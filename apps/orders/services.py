import logging
from decimal import Decimal

from django.db import transaction

from apps.catalogue.models import ProductVariant
from apps.inventory import services as inventory_services

from .models import (
    DisputeStatus,
    Order,
    OrderDispute,
    OrderItem,
    OrderStatus,
    SubOrder,
    _generate_order_reference,
)

logger = logging.getLogger(__name__)


def _sync_order_status(order: Order) -> None:
    sub_statuses = list(order.sub_orders.values_list("status", flat=True))
    non_cancelled = [s for s in sub_statuses if s != OrderStatus.CANCELLED]

    if not non_cancelled:
        new_status = OrderStatus.CANCELLED
    elif all(s == OrderStatus.DELIVERED for s in non_cancelled):
        new_status = OrderStatus.DELIVERED
    elif all(s in (OrderStatus.DISPATCHED, OrderStatus.DELIVERED) for s in non_cancelled):
        new_status = OrderStatus.DISPATCHED
    elif all(
        s in (OrderStatus.CONFIRMED, OrderStatus.DISPATCHED, OrderStatus.DELIVERED)
        for s in non_cancelled
    ):
        new_status = OrderStatus.CONFIRMED
    else:
        return
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])


def _consume_cart_reservation(buyer, variant: ProductVariant, quantity: int) -> bool:
    """
    If the buyer holds a non-expired cart reservation for `variant` covering at least
    `quantity` units, delete it and return True (stock is already reserved).
    Returns False if no valid reservation exists.
    """
    from django.utils import timezone

    from apps.marketplace.models import CartReservation

    try:
        res = CartReservation.objects.select_related("cart_item").get(
            cart_item__cart__buyer=buyer,
            variant=variant,
            expires_at__gt=timezone.now(),
        )
    except CartReservation.DoesNotExist:
        return False

    if res.quantity < quantity:
        # Partial reservation — release the cart portion and re-reserve the full amount.
        inventory_services.release_reservation(
            variant, res.quantity, reference=f"CART:{res.cart_item_id}"
        )
        res.cart_item.delete()
        return False

    if res.quantity > quantity:
        # More reserved than needed — release the surplus, keep the order amount reserved.
        surplus = res.quantity - quantity
        inventory_services.release_reservation(
            variant, surplus, reference=f"CART:{res.cart_item_id}"
        )

    res.cart_item.delete()
    return True


@transaction.atomic
def place_order(
    buyer,
    items: list[dict],
    shipping: dict,
) -> Order:
    """
    items: [{"variant": ProductVariant, "quantity": int}, ...]
    shipping: {"name", "line1", "line2", "city", "postcode", "country", "notes"}
    Reserves stock atomically; rolls back entirely on any failure.
    """
    if not items:
        raise ValueError("Order must have at least one item.")

    reference = _generate_order_reference()
    supplier_groups: dict = {}
    total_amount = Decimal("0.00")

    for item in items:
        variant: ProductVariant = item["variant"]
        quantity: int = item["quantity"]
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive for SKU {variant.sku}.")
        if not variant.is_active:
            raise ValueError(f"SKU {variant.sku} is not available.")

        # If the buyer has a live cart reservation for this variant the stock is already
        # held in quantity_reserved — don't reserve again, just clear the cart record.
        cart_reserved = _consume_cart_reservation(buyer, variant, quantity)
        if not cart_reserved:
            inventory_services.reserve_stock(variant, quantity, reference=reference)

        line_total = variant.price * quantity
        total_amount += line_total
        sid = variant.product.supplier_id
        supplier_groups.setdefault(sid, {"supplier": variant.product.supplier, "items": []})
        supplier_groups[sid]["items"].append(
            {"variant": variant, "quantity": quantity, "line_total": line_total}
        )

    order = Order.objects.create(
        buyer=buyer,
        reference=reference,
        total_amount=total_amount,
        shipping_name=shipping["name"],
        shipping_line1=shipping["line1"],
        shipping_line2=shipping.get("line2", ""),
        shipping_city=shipping["city"],
        shipping_postcode=shipping["postcode"],
        shipping_country=shipping["country"],
        notes=shipping.get("notes", ""),
    )

    for group in supplier_groups.values():
        subtotal = sum(i["line_total"] for i in group["items"])
        sub = SubOrder.objects.create(
            order=order,
            supplier=group["supplier"],
            subtotal=subtotal,
        )
        for item in group["items"]:
            v = item["variant"]
            OrderItem.objects.create(
                sub_order=sub,
                variant=v,
                product_name=v.product.name,
                variant_name=v.name,
                sku=v.sku,
                quantity=item["quantity"],
                unit_price=v.price,
            )

    return order


@transaction.atomic
def confirm_sub_order(sub_order: SubOrder) -> SubOrder:
    if sub_order.status != OrderStatus.PENDING:
        raise ValueError(f"Cannot confirm a sub-order with status {sub_order.status}.")
    sub_order.status = OrderStatus.CONFIRMED
    sub_order.save(update_fields=["status", "updated_at"])
    _sync_order_status(sub_order.order)
    return sub_order


@transaction.atomic
def dispatch_sub_order(sub_order: SubOrder, tracking_number: str = "") -> SubOrder:
    if sub_order.status not in (OrderStatus.PENDING, OrderStatus.CONFIRMED):
        raise ValueError(f"Cannot dispatch a sub-order with status {sub_order.status}.")
    for item in sub_order.items.select_related("variant"):
        inventory_services.dispatch_stock(
            item.variant, item.quantity, reference=sub_order.order.reference
        )
    sub_order.status = OrderStatus.DISPATCHED
    sub_order.tracking_number = tracking_number
    sub_order.save(update_fields=["status", "tracking_number", "updated_at"])
    _sync_order_status(sub_order.order)
    try:
        from apps.notifications.email_service import send_shipping_update

        send_shipping_update(sub_order)
    except Exception:
        logger.exception("Failed to send shipping update email for sub_order %s", sub_order.id)
    return sub_order


@transaction.atomic
def deliver_sub_order(sub_order: SubOrder) -> SubOrder:
    if sub_order.status != OrderStatus.DISPATCHED:
        raise ValueError(f"Cannot deliver a sub-order with status {sub_order.status}.")
    sub_order.status = OrderStatus.DELIVERED
    sub_order.save(update_fields=["status", "updated_at"])
    _sync_order_status(sub_order.order)
    return sub_order


@transaction.atomic
def cancel_sub_order(sub_order: SubOrder) -> SubOrder:
    if sub_order.status == OrderStatus.DELIVERED:
        raise ValueError("Cannot cancel a delivered sub-order.")
    if sub_order.status == OrderStatus.CANCELLED:
        return sub_order
    if sub_order.status in (OrderStatus.PENDING, OrderStatus.CONFIRMED):
        for item in sub_order.items.select_related("variant"):
            inventory_services.release_reservation(
                item.variant, item.quantity, reference=sub_order.order.reference
            )
    sub_order.status = OrderStatus.CANCELLED
    sub_order.save(update_fields=["status", "updated_at"])
    _sync_order_status(sub_order.order)
    return sub_order


@transaction.atomic
def cancel_order(order: Order) -> Order:
    if order.status == OrderStatus.DELIVERED:
        raise ValueError("Cannot cancel a delivered order.")
    for sub in order.sub_orders.exclude(status=OrderStatus.CANCELLED):
        cancel_sub_order(sub)
    order.refresh_from_db()
    return order


@transaction.atomic
def raise_dispute(sub_order: SubOrder, raised_by, reason: str) -> OrderDispute:
    if sub_order.status not in (OrderStatus.DISPATCHED, OrderStatus.DELIVERED):
        raise ValueError("Disputes can only be raised for dispatched or delivered sub-orders.")
    return OrderDispute.objects.create(
        sub_order=sub_order,
        raised_by=raised_by,
        reason=reason,
    )


@transaction.atomic
def resolve_dispute(dispute: OrderDispute, resolution: str) -> OrderDispute:
    if dispute.status != DisputeStatus.OPEN:
        raise ValueError("Can only resolve an open dispute.")
    dispute.status = DisputeStatus.RESOLVED
    dispute.resolution = resolution
    dispute.save(update_fields=["status", "resolution", "updated_at"])
    return dispute


@transaction.atomic
def reject_dispute(dispute: OrderDispute, resolution: str) -> OrderDispute:
    if dispute.status != DisputeStatus.OPEN:
        raise ValueError("Can only reject an open dispute.")
    dispute.status = DisputeStatus.REJECTED
    dispute.resolution = resolution
    dispute.save(update_fields=["status", "resolution", "updated_at"])
    return dispute
