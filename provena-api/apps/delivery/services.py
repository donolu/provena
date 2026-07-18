"""Courier delivery orchestration (ADR-013 live-courier slice).

Bridges the order flow to a `CourierProvider`: quote at checkout, book at dispatch, and react to
status webhooks (delivered -> mark delivered/pay out; failed -> refund the buyer's delivery fee and
absorb the courier cost). Pass-through at cost, so `fee_charged == courier_cost`.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum

from .models import CourierDelivery
from .providers import DeliveryStatus, get_provider
from .providers.base import Quote

logger = logging.getLogger(__name__)


def _supplier_pickup(supplier) -> dict:
    address = getattr(supplier, "address", None)
    if address is None:
        return {"name": supplier.business_name}
    return {
        "name": supplier.business_name,
        "line1": address.line1,
        "city": address.city,
        "postcode": address.postcode,
        "country": address.country,
    }


def quote_for_supplier(supplier, *, dropoff: dict, items: list[dict]) -> Quote:
    """Quote platform-brokered delivery for a supplier's items to ``dropoff``.

    ``items`` is ``[{"quantity": int}, ...]``. Raises ``NotServiceable`` (from the provider) if the
    address cannot be served — the caller turns that into a checkout error.
    """
    return get_provider().get_quote(pickup=_supplier_pickup(supplier), dropoff=dropoff, items=items)


def record_quote(sub_order, quote: Quote) -> CourierDelivery:
    """Snapshot a checkout quote onto a CourierDelivery row (status QUOTED)."""
    return CourierDelivery.objects.create(
        sub_order=sub_order,
        provider=quote.provider,
        provider_quote_id=quote.quote_id,
        fee_charged=quote.fee,
        courier_cost=quote.courier_cost,
        currency=quote.currency,
        status=DeliveryStatus.QUOTED,
        quote_expires_at=quote.expires_at,
    )


def order_has_expired_quote(order) -> bool:
    """True if any platform-delivery quote on the order has lapsed (checked before charging)."""
    return any(
        cd.is_quote_expired and cd.status == DeliveryStatus.QUOTED
        for cd in CourierDelivery.objects.filter(sub_order__order=order)
    )


def book_delivery(sub_order) -> CourierDelivery | None:
    """Book the courier for a sub-order that has a quote (idempotent). Called at dispatch."""
    with transaction.atomic():
        try:
            cd = CourierDelivery.objects.select_for_update().get(sub_order=sub_order)
        except CourierDelivery.DoesNotExist:
            return None
        if cd.status != DeliveryStatus.QUOTED:
            return cd  # already booked / terminal — idempotent

        order = sub_order.order
        dropoff = {
            "name": order.shipping_name,
            "line1": order.shipping_line1,
            "city": order.shipping_city,
            "postcode": order.shipping_postcode,
            "country": order.shipping_country,
        }
        delivery = get_provider().create_delivery(
            quote_id=cd.provider_quote_id,
            pickup=_supplier_pickup(sub_order.supplier),
            dropoff=dropoff,
            reference=order.reference,
        )
        cd.provider_delivery_id = delivery.delivery_id
        cd.tracking_url = delivery.tracking_url
        cd.status = DeliveryStatus.BOOKED
        cd.save(update_fields=["provider_delivery_id", "tracking_url", "status", "updated_at"])
        logger.info("Booked courier %s for sub_order %s", delivery.delivery_id, sub_order.id)
        return cd


def handle_status_event(payload: dict) -> None:
    """Apply a courier status webhook: delivered -> deliver the sub-order (pays out); failed/
    cancelled -> refund the buyer's delivery fee and absorb the courier cost."""
    from apps.orders import services as order_services
    from apps.payments import services as payment_services

    delivery_id, status = get_provider().parse_status_event(payload)
    if not delivery_id:
        return
    try:
        cd = CourierDelivery.objects.select_related("sub_order__order__payment").get(
            provider_delivery_id=delivery_id
        )
    except CourierDelivery.DoesNotExist:
        logger.warning("Courier event for unknown delivery %s", delivery_id)
        return

    if cd.status in (DeliveryStatus.DELIVERED, *DeliveryStatus.FAILURE):
        return  # terminal — idempotent

    if status == DeliveryStatus.DELIVERED:
        cd.status = DeliveryStatus.DELIVERED
        cd.save(update_fields=["status", "updated_at"])
        # Delivery complete -> mark the sub-order delivered, which triggers the supplier payout.
        if cd.sub_order.status == "DISPATCHED":
            order_services.deliver_sub_order(cd.sub_order)
        return

    if status in DeliveryStatus.FAILURE:
        cd.status = status
        cd.save(update_fields=["status", "updated_at"])
        payment = getattr(cd.sub_order.order, "payment", None)
        if payment is not None and cd.fee_charged > 0:
            # Refund the buyer's delivery fee; the platform absorbs the courier cost (ADR-013 §#6).
            payment_services.initiate_refund(
                payment,
                amount=cd.fee_charged,
                idempotency_key=f"courier-fail-{cd.id}",
            )
        logger.info("Courier delivery %s %s; refunded delivery fee", delivery_id, status)
        return

    # Non-terminal progress (e.g. en route).
    cd.status = status
    cd.save(update_fields=["status", "updated_at"])


def reconciliation_summary() -> dict:
    """Platform delivery ledger: buyer fees collected vs courier cost, and absorbed failures."""
    agg = CourierDelivery.objects.aggregate(
        fee_charged_total=Sum("fee_charged"),
        courier_cost_total=Sum("courier_cost"),
        delivered=Count("id", filter=Q(status=DeliveryStatus.DELIVERED)),
        failed=Count("id", filter=Q(status__in=DeliveryStatus.FAILURE)),
        absorbed_cost=Sum("courier_cost", filter=Q(status__in=DeliveryStatus.FAILURE)),
    )

    def money(value) -> str:
        # SQLite returns Decimal sums with float artefacts; quantise to pence.
        return str(Decimal(str(value or "0")).quantize(Decimal("0.01")))

    return {
        "fee_charged_total": money(agg["fee_charged_total"]),
        "courier_cost_total": money(agg["courier_cost_total"]),
        "delivered_count": agg["delivered"] or 0,
        "failed_count": agg["failed"] or 0,
        "platform_absorbed_cost": money(agg["absorbed_cost"]),
    }
