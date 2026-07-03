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


@transaction.atomic
def create_payment_intent(order: Order) -> Payment:
    if order.status != OrderStatus.PENDING:
        raise ValueError(f"Cannot create payment for order in status {order.status}.")
    if hasattr(order, "payment"):
        return order.payment

    stripe.api_key = settings.STRIPE_SECRET_KEY
    intent = stripe.PaymentIntent.create(
        amount=_to_pence(order.total_amount),
        currency="gbp",
        metadata={"order_reference": order.reference},
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
    _send_order_emails(payment.order)
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
def handle_refund(stripe_payment_intent_id: str) -> Payment:
    payment = Payment.objects.select_for_update().get(
        stripe_payment_intent_id=stripe_payment_intent_id
    )
    payment.status = PaymentStatus.REFUNDED
    payment.save(update_fields=["status", "updated_at"])
    Payout.objects.filter(
        sub_order__order=payment.order,
        status__in=[PayoutStatus.PENDING, PayoutStatus.PROCESSING],
    ).update(status=PayoutStatus.FAILED)
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
    payout.status = PayoutStatus.PROCESSING
    payout.save(update_fields=["status", "updated_at"])
    logger.info("Payout %s marked as PROCESSING", payout.id)
    try:
        from apps.notifications.email_service import send_payout_received

        send_payout_received(payout)
    except Exception:
        logger.exception("Failed to send payout email for payout %s", payout.id)
    return payout
