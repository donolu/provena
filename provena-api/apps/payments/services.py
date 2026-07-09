import logging
from decimal import Decimal

import stripe
from django.conf import settings
from django.db import transaction

from apps.orders.models import Order, OrderStatus

from .models import Payment, PaymentStatus, Payout, PayoutStatus

logger = logging.getLogger(__name__)


def _to_pence(amount: Decimal) -> int:
    return int(amount * 100)


def create_payment_intent(order: Order) -> Payment:
    if order.status != OrderStatus.PENDING:
        raise ValueError(f"Cannot create payment for order in status {order.status}.")
    if hasattr(order, "payment"):
        return order.payment

    # Stripe is called outside any DB transaction so a network error never causes a rollback
    # of already-committed data. The idempotency key makes retries safe: Stripe returns the
    # same PaymentIntent on duplicate requests for the same order reference.
    stripe.api_key = settings.STRIPE_SECRET_KEY
    intent = stripe.PaymentIntent.create(
        amount=_to_pence(order.total_amount),
        currency="gbp",
        metadata={"order_reference": order.reference},
        idempotency_key=f"order-{order.reference}",
    )
    return Payment.objects.create(
        order=order,
        stripe_payment_intent_id=intent["id"],
        stripe_client_secret=intent["client_secret"],
        amount=order.total_amount,
        currency="gbp",
        status=PaymentStatus.PROCESSING,
    )


@transaction.atomic
def handle_payment_succeeded(stripe_payment_intent_id: str) -> Payment:
    payment = Payment.objects.select_for_update().get(
        stripe_payment_intent_id=stripe_payment_intent_id
    )
    if payment.status == PaymentStatus.SUCCEEDED:
        return payment
    payment.status = PaymentStatus.SUCCEEDED
    payment.save(update_fields=["status", "updated_at"])
    _create_payouts(payment)
    transaction.on_commit(lambda: _send_order_emails(payment.order))
    return payment


def _send_order_emails(order) -> None:
    from apps.notifications.email_service import (
        send_order_confirmation_buyer,
        send_order_notification_supplier,
    )

    send_order_confirmation_buyer(order)
    for sub_order in order.sub_orders.select_related("supplier__user").all():
        send_order_notification_supplier(sub_order)


@transaction.atomic
def handle_payment_failed(stripe_payment_intent_id: str) -> Payment:
    payment = Payment.objects.select_for_update().get(
        stripe_payment_intent_id=stripe_payment_intent_id
    )
    if payment.status == PaymentStatus.FAILED:
        return payment
    payment.status = PaymentStatus.FAILED
    payment.save(update_fields=["status", "updated_at"])
    return payment


@transaction.atomic
def handle_refund(
    stripe_payment_intent_id: str,
    amount_refunded_pence: int | None = None,
    charge_amount_pence: int | None = None,
) -> Payment:
    payment = Payment.objects.select_for_update().get(
        stripe_payment_intent_id=stripe_payment_intent_id
    )
    if amount_refunded_pence is not None and charge_amount_pence is not None:
        payment.refunded_amount = Decimal(amount_refunded_pence) / 100
        is_full = amount_refunded_pence >= charge_amount_pence
    else:
        payment.refunded_amount = payment.amount
        is_full = True

    payment.status = PaymentStatus.REFUNDED if is_full else PaymentStatus.PARTIALLY_REFUNDED
    payment.save(update_fields=["status", "refunded_amount", "updated_at"])

    if is_full:
        Payout.objects.filter(
            sub_order__order=payment.order,
            status__in=[PayoutStatus.PENDING, PayoutStatus.PROCESSING],
        ).update(status=PayoutStatus.FAILED)
    return payment


def initiate_refund(payment: Payment, amount: Decimal | None = None) -> Payment:
    """Issue a refund via Stripe. amount=None means full refund."""
    if payment.status not in (PaymentStatus.SUCCEEDED, PaymentStatus.PARTIALLY_REFUNDED):
        raise ValueError(f"Cannot refund a payment with status {payment.status}.")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    intent = stripe.PaymentIntent.retrieve(payment.stripe_payment_intent_id)
    charge_id = getattr(intent, "latest_charge", None)
    if not charge_id:
        raise ValueError("No charge found on this PaymentIntent.")

    kwargs: dict = {"charge": charge_id}
    if amount is not None:
        max_refundable = payment.amount - payment.refunded_amount
        if amount > max_refundable:
            raise ValueError(
                f"Refund amount £{amount} exceeds refundable balance £{max_refundable}."
            )
        kwargs["amount"] = _to_pence(amount)

    stripe.Refund.create(**kwargs)
    logger.info("Stripe refund initiated for payment %s (amount=%s)", payment.id, amount or "full")
    return payment


@transaction.atomic
def handle_payment_cancelled(stripe_payment_intent_id: str) -> Payment:
    payment = Payment.objects.select_for_update().get(
        stripe_payment_intent_id=stripe_payment_intent_id
    )
    payment.status = PaymentStatus.CANCELLED
    payment.save(update_fields=["status", "updated_at"])
    return payment


def _create_payouts(payment: Payment) -> None:
    fee_pct = Decimal(str(getattr(settings, "PLATFORM_FEE_PERCENT", "10")))
    for sub_order in payment.order.sub_orders.select_related("supplier").all():
        gross = sub_order.subtotal
        fee = (gross * fee_pct / Decimal("100")).quantize(Decimal("0.01"))
        net = gross - fee
        _payout, created = Payout.objects.get_or_create(
            sub_order=sub_order,
            defaults={
                "supplier": sub_order.supplier,
                "gross_amount": gross,
                "platform_fee": fee,
                "net_amount": net,
                "status": PayoutStatus.PENDING,
            },
        )
        if created:
            logger.info(
                "Payout created for sub_order %s: gross=%s fee=%s net=%s",
                sub_order.id,
                gross,
                fee,
                net,
            )


def process_payout(payout: Payout) -> Payout:
    if payout.status != PayoutStatus.PENDING:
        raise ValueError(f"Cannot process a payout with status {payout.status}.")

    supplier = payout.supplier
    if not supplier.stripe_account_id or not supplier.stripe_onboarding_complete:
        raise ValueError(
            f"Supplier '{supplier.business_name}' has not completed Stripe Connect onboarding."
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY

    payment = payout.sub_order.order.payment
    intent = stripe.PaymentIntent.retrieve(payment.stripe_payment_intent_id)
    charge_id = getattr(intent, "latest_charge", None)

    payout.status = PayoutStatus.PROCESSING
    payout.save(update_fields=["status", "updated_at"])

    try:
        transfer_kwargs: dict = {
            "amount": _to_pence(payout.net_amount),
            "currency": payment.currency,
            "destination": supplier.stripe_account_id,
            "metadata": {
                "payout_id": str(payout.id),
                "sub_order_id": str(payout.sub_order.id),
                "order_reference": payment.order.reference,
            },
        }
        if charge_id:
            transfer_kwargs["source_transaction"] = charge_id

        transfer = stripe.Transfer.create(**transfer_kwargs)
        payout.stripe_transfer_id = transfer.id
        payout.status = PayoutStatus.PAID
        payout.save(update_fields=["status", "stripe_transfer_id", "updated_at"])
        logger.info("Stripe transfer %s created for payout %s", transfer.id, payout.id)
    except stripe.StripeError as exc:
        payout.status = PayoutStatus.FAILED
        payout.save(update_fields=["status", "updated_at"])
        logger.exception("Stripe transfer failed for payout %s", payout.id)
        raise ValueError(f"Stripe transfer failed: {exc}") from exc

    try:
        from apps.notifications.email_service import send_payout_received

        send_payout_received(payout)
    except Exception:
        logger.exception("Failed to send payout email for payout %s", payout.id)

    return payout
