import logging
from datetime import timedelta
from decimal import Decimal

import stripe
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order, OrderStatus

from .models import (
    Payment,
    PaymentRefundRequest,
    PaymentRefundRequestStatus,
    PaymentStatus,
    Payout,
    PayoutStatus,
)

logger = logging.getLogger(__name__)

_PAYOUT_PROCESSING_TIMEOUT = timedelta(minutes=10)


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
    old_refunded = payment.refunded_amount
    if amount_refunded_pence is not None and charge_amount_pence is not None:
        payment.refunded_amount = Decimal(amount_refunded_pence) / 100
        is_full = amount_refunded_pence >= charge_amount_pence
    else:
        payment.refunded_amount = payment.amount
        is_full = True

    # Drain pending_refund_amount by the confirmed delta so the available-to-refund
    # balance stays accurate between initiate_refund() and the next webhook fire.
    confirmed_delta = payment.refunded_amount - old_refunded
    payment.pending_refund_amount = max(
        Decimal("0"), payment.pending_refund_amount - confirmed_delta
    )
    payment.status = PaymentStatus.REFUNDED if is_full else PaymentStatus.PARTIALLY_REFUNDED
    payment.save(update_fields=["status", "refunded_amount", "pending_refund_amount", "updated_at"])

    if is_full:
        Payout.objects.filter(
            sub_order__order=payment.order,
            status__in=[PayoutStatus.PENDING, PayoutStatus.PROCESSING],
        ).update(status=PayoutStatus.FAILED)
    return payment


def initiate_refund(payment: Payment, amount: Decimal | None = None) -> Payment:
    """Issue a refund via Stripe. amount=None means full refund."""
    # Each (payment, amount-in-pence) pair maps to one PaymentRefundRequest row keyed
    # by the Stripe idempotency key. Retries of the same amount find the existing row
    # and reuse its reservation rather than inflating pending_refund_amount again.
    this_call_reserved = False

    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status not in (PaymentStatus.SUCCEEDED, PaymentStatus.PARTIALLY_REFUNDED):
            raise ValueError(f"Cannot refund a payment with status {payment.status}.")

        outstanding_amount = payment.amount - payment.refunded_amount
        refund_amount: Decimal = amount if amount is not None else outstanding_amount
        if refund_amount <= 0:
            raise ValueError("Refund amount must be greater than zero.")
        amount_pence = _to_pence(refund_amount)
        stripe_idempotency_key = f"refund-{payment.id}-{amount_pence}"

        request, created = PaymentRefundRequest.objects.get_or_create(
            stripe_idempotency_key=stripe_idempotency_key,
            defaults={"payment": payment, "amount": refund_amount},
        )

        if request.status == PaymentRefundRequestStatus.COMPLETED:
            return payment

        needs_reservation = created or request.status == PaymentRefundRequestStatus.FAILED
        if needs_reservation:
            max_refundable = (
                payment.amount - payment.refunded_amount - payment.pending_refund_amount
            )
            if refund_amount > max_refundable:
                if created:
                    request.delete()
                raise ValueError(
                    f"Refund amount £{refund_amount} exceeds refundable balance £{max_refundable}."
                )
            if not created:
                # Reset a previously-failed attempt so it can be retried.
                request.status = PaymentRefundRequestStatus.PENDING
                request.save(update_fields=["status", "updated_at"])
            payment.pending_refund_amount += refund_amount
            payment.save(update_fields=["pending_refund_amount", "updated_at"])
            this_call_reserved = True
        # else: existing PENDING (in-flight retry) — skip reservation, proceed to Stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    intent = stripe.PaymentIntent.retrieve(payment.stripe_payment_intent_id)
    charge_id = getattr(intent, "latest_charge", None)
    if not charge_id:
        if this_call_reserved:
            with transaction.atomic():
                request.status = PaymentRefundRequestStatus.FAILED
                request.save(update_fields=["status", "updated_at"])
                pmt = Payment.objects.select_for_update().get(pk=payment.pk)
                pmt.pending_refund_amount = max(
                    Decimal("0"), pmt.pending_refund_amount - refund_amount
                )
                pmt.save(update_fields=["pending_refund_amount", "updated_at"])
        raise ValueError("No charge found on this PaymentIntent.")

    try:
        refund = stripe.Refund.create(
            charge=charge_id,
            amount=amount_pence,
            idempotency_key=stripe_idempotency_key,
        )
    except stripe.StripeError as exc:
        if this_call_reserved:
            with transaction.atomic():
                request.status = PaymentRefundRequestStatus.FAILED
                request.save(update_fields=["status", "updated_at"])
                pmt = Payment.objects.select_for_update().get(pk=payment.pk)
                pmt.pending_refund_amount = max(
                    Decimal("0"), pmt.pending_refund_amount - refund_amount
                )
                pmt.save(update_fields=["pending_refund_amount", "updated_at"])
        raise ValueError(f"Stripe refund failed: {exc}") from exc

    with transaction.atomic():
        request.stripe_refund_id = refund.id
        request.status = PaymentRefundRequestStatus.COMPLETED
        request.save(update_fields=["stripe_refund_id", "status", "updated_at"])

    logger.info("Stripe refund initiated for payment %s (amount=%s)", payment.id, refund_amount)
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
    # Lock the Payout row and transition atomically.
    # PENDING → PROCESSING: mark as in-flight with a timestamp.
    # PROCESSING (stale, >10 min): reset timestamp and fall through so Transfer.create
    #   is retried — the idempotency key returns the existing Stripe transfer.
    # PROCESSING (recent, <10 min): another worker is active; raise to avoid racing it.
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(pk=payout.pk)
        if payout.status == PayoutStatus.PENDING:
            payout.status = PayoutStatus.PROCESSING
            payout.processing_started_at = timezone.now()
            payout.save(update_fields=["status", "processing_started_at", "updated_at"])
        elif payout.status == PayoutStatus.PROCESSING:
            if (
                payout.processing_started_at is not None
                and timezone.now() - payout.processing_started_at < _PAYOUT_PROCESSING_TIMEOUT
            ):
                raise ValueError(
                    "Payout is already being processed by another worker. "
                    f"Retry after {_PAYOUT_PROCESSING_TIMEOUT.seconds // 60} minutes if stalled."
                )
            # Stale or no timestamp: reset and fall through.
            payout.processing_started_at = timezone.now()
            payout.save(update_fields=["processing_started_at", "updated_at"])
        else:
            raise ValueError(f"Cannot process a payout with status {payout.status}.")

    supplier = payout.supplier
    if not supplier.stripe_account_id or not supplier.stripe_onboarding_complete:
        # Supplier not yet onboarded; roll back to PENDING so the payout can be retried.
        with transaction.atomic():
            payout.status = PayoutStatus.PENDING
            payout.save(update_fields=["status", "updated_at"])
        raise ValueError(
            f"Supplier '{supplier.business_name}' has not completed Stripe Connect onboarding."
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY

    payment = payout.sub_order.order.payment
    intent = stripe.PaymentIntent.retrieve(payment.stripe_payment_intent_id)
    charge_id = getattr(intent, "latest_charge", None)

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
            "idempotency_key": f"payout-{payout.id}",
        }
        if charge_id:
            transfer_kwargs["source_transaction"] = charge_id

        transfer = stripe.Transfer.create(**transfer_kwargs)
        with transaction.atomic():
            payout.stripe_transfer_id = transfer.id
            payout.status = PayoutStatus.PAID
            payout.save(update_fields=["status", "stripe_transfer_id", "updated_at"])
        logger.info("Stripe transfer %s created for payout %s", transfer.id, payout.id)
    except stripe.StripeError as exc:
        # Re-read under lock: if the first worker already wrote PAID (e.g. our call was a
        # stale-PROCESSING retry and Stripe idempotently returned the transfer), do not
        # overwrite that success with FAILED.
        with transaction.atomic():
            locked = Payout.objects.select_for_update().get(pk=payout.pk)
            if locked.status != PayoutStatus.PAID:
                locked.status = PayoutStatus.FAILED
                locked.save(update_fields=["status", "updated_at"])
        logger.exception("Stripe transfer failed for payout %s", payout.id)
        raise ValueError(f"Stripe transfer failed: {exc}") from exc

    try:
        from apps.notifications.email_service import send_payout_received

        send_payout_received(payout)
    except Exception:
        logger.exception("Failed to send payout email for payout %s", payout.id)

    return payout
