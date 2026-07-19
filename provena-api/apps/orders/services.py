import logging
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.catalogue.models import ProductVariant
from apps.inventory import services as inventory_services
from apps.suppliers.models import FulfilmentMode

from .models import (
    RETURN_WINDOW_DAYS,
    DiscountCode,
    DiscountRedemption,
    Order,
    OrderItem,
    OrderReturn,
    OrderStatus,
    ReturnItem,
    ReturnStatus,
    SubOrder,
    _generate_order_reference,
)
from .pricing import compute_order_pricing

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


def _push_order_status(reference: str, status: str) -> None:
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        from .consumers import _order_group

        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            _order_group(reference),
            {"type": "order.status", "status": status},
        )
    except Exception:
        logger.exception("Failed to push order status via WebSocket")


def _consume_cart_reservation(buyer, variant: ProductVariant, quantity: int) -> bool:
    """
    If the buyer holds a non-expired cart reservation for `variant` covering at least
    `quantity` units, delete it and return True (stock is already reserved).
    Returns False if no valid reservation exists.

    Must be called inside a transaction. The CartItem row is locked with
    SELECT FOR UPDATE so that concurrent checkouts for the same cart item
    serialise here: the second caller blocks until the first commits, then
    sees DoesNotExist and falls through to reserve_stock() instead.
    """
    from apps.marketplace.models import CartItem, CartReservation

    try:
        cart_item = CartItem.objects.select_for_update().get(
            cart__buyer=buyer,
            variant=variant,
        )
    except CartItem.DoesNotExist:
        return False

    # Re-read reservation through the locked CartItem so expiry is checked
    # after the lock is held, not before.
    try:
        res = CartReservation.objects.get(
            cart_item=cart_item,
            expires_at__gt=timezone.now(),
        )
    except CartReservation.DoesNotExist:
        return False

    if res.quantity < quantity:
        # Partial reservation — release the cart portion and re-reserve the full amount.
        inventory_services.release_reservation(
            variant, res.quantity, reference=f"CART:{cart_item.id}"
        )
        cart_item.delete()
        return False

    if res.quantity > quantity:
        # More reserved than needed — release the surplus, keep the order amount reserved.
        surplus = res.quantity - quantity
        inventory_services.release_reservation(variant, surplus, reference=f"CART:{cart_item.id}")

    cart_item.delete()
    return True


def _resolve_discount(buyer, code_str: str, order_goods: Decimal) -> DiscountCode:
    """Validate a discount code for this buyer/order, raising ValueError on any failure.

    The code row is locked FOR UPDATE so concurrent checkouts of the same code serialise
    here: usage-limit counts are read under the lock, so the cap cannot be over-redeemed.
    """
    try:
        code = DiscountCode.objects.select_for_update().get(code=code_str.strip().upper())
    except DiscountCode.DoesNotExist:
        raise ValueError("Discount code not found.") from None

    if not code.is_live(timezone.now()):
        raise ValueError("This discount code is not currently valid.")
    if order_goods < code.minimum_spend:
        raise ValueError(f"Spend at least £{code.minimum_spend} to use this code.")
    if code.max_uses is not None and code.redemptions.count() >= code.max_uses:
        raise ValueError("This discount code has reached its usage limit.")
    if (
        code.max_uses_per_buyer is not None
        and code.redemptions.filter(buyer=buyer).count() >= code.max_uses_per_buyer
    ):
        raise ValueError("You have already used this discount code.")
    return code


def preview_discount(buyer, code_str: str) -> dict:
    """Advisory check of a discount code against the buyer's current cart.

    Returns ``{"valid": True, "code", "discount_amount", "new_total"}`` or
    ``{"valid": False, "reason"}``. ``new_total`` is the full previewed order total
    (goods - discount + shipping, VAT-inclusive) from the same ``compute_order_pricing``
    pass used at checkout, so the buyer sees the figure they will actually be charged
    rather than a raw goods discount. The preview reserves nothing — ``place_order``
    re-validates authoritatively, so a code can still lapse between preview and checkout.

    Shipping here follows each supplier's standing policy; for platform-brokered delivery
    (ADR-013) the exact live courier fee is only resolved at checkout, since it needs the
    delivery address, so the preview falls back to the supplier's configured fee.
    """
    from apps.marketplace.services import get_or_create_cart

    cart = get_or_create_cart(user=buyer)
    supplier_groups: dict = {}
    for cart_item in cart.items.select_related("variant__product__supplier"):
        variant = cart_item.variant
        sid = variant.product.supplier_id
        supplier_groups.setdefault(sid, {"supplier": variant.product.supplier, "items": []})
        supplier_groups[sid]["items"].append(
            {
                "variant": variant,
                "quantity": cart_item.quantity,
                "line_total": variant.price * cart_item.quantity,
            }
        )

    goods = sum(
        (i["line_total"] for g in supplier_groups.values() for i in g["items"]),
        Decimal("0.00"),
    )
    if goods <= 0:
        return {"valid": False, "reason": "Your cart is empty."}
    try:
        with transaction.atomic():
            code = _resolve_discount(buyer, code_str, goods)
    except ValueError as exc:
        return {"valid": False, "reason": str(exc)}

    # Pure computation (no writes), so run it outside the lock held by _resolve_discount.
    pricing = compute_order_pricing(supplier_groups, discount_code=code)
    return {
        "valid": True,
        "code": code.code,
        "discount_amount": str(pricing.discount_amount),
        "new_total": str(pricing.total_amount),
    }


@transaction.atomic
def place_order(
    buyer,
    items: list[dict],
    shipping: dict,
    discount_code: str = "",
) -> Order:
    """
    items: [{"variant": ProductVariant, "quantity": int}, ...]
    shipping: {"name", "line1", "line2", "city", "postcode", "country", "notes"}
    discount_code: optional order-level voucher code.
    Reserves stock atomically; rolls back entirely on any failure.
    """
    if not items:
        raise ValueError("Order must have at least one item.")

    reference = _generate_order_reference()
    supplier_groups: dict = {}

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
        sid = variant.product.supplier_id
        supplier_groups.setdefault(sid, {"supplier": variant.product.supplier, "items": []})
        supplier_groups[sid]["items"].append(
            {"variant": variant, "quantity": quantity, "line_total": line_total}
        )

    discount: DiscountCode | None = None
    if discount_code:
        order_goods = sum(
            (i["line_total"] for g in supplier_groups.values() for i in g["items"]),
            Decimal("0.00"),
        )
        discount = _resolve_discount(buyer, discount_code, order_goods)

    # Platform-brokered delivery (ADR-013): quote the courier for each PLATFORM_DELIVERY supplier.
    # An unserviceable address blocks checkout for that supplier rather than charging a wrong fee.
    courier_quotes: dict = {}
    for sid, group in supplier_groups.items():
        if getattr(group["supplier"], "fulfilment_mode", "") == FulfilmentMode.PLATFORM_DELIVERY:
            from apps.delivery import services as delivery_services
            from apps.delivery.providers import NotServiceable

            try:
                courier_quotes[sid] = delivery_services.quote_for_supplier(
                    group["supplier"], dropoff=shipping, items=group["items"]
                )
            except NotServiceable as exc:
                raise ValueError(str(exc)) from exc

    # One deterministic pricing pass; results are snapshotted onto the order (ADR-012).
    pricing = compute_order_pricing(
        supplier_groups, discount_code=discount, courier_quotes=courier_quotes
    )

    order = Order.objects.create(
        buyer=buyer,
        reference=reference,
        goods_subtotal=pricing.goods_subtotal,
        discount_amount=pricing.discount_amount,
        shipping_amount=pricing.shipping_amount,
        vat_amount=pricing.vat_amount,
        total_amount=pricing.total_amount,
        discount_code=discount.code if discount else "",
        discount_funded_by=discount.funded_by if discount else "",
        shipping_name=shipping["name"],
        shipping_line1=shipping["line1"],
        shipping_line2=shipping.get("line2", ""),
        shipping_city=shipping["city"],
        shipping_postcode=shipping["postcode"],
        shipping_country=shipping["country"],
        notes=shipping.get("notes", ""),
    )

    if discount is not None:
        DiscountRedemption.objects.create(
            code=discount, buyer=buyer, order=order, amount=pricing.discount_amount
        )

    for sub_pricing in pricing.sub_orders:
        sub = SubOrder.objects.create(
            order=order,
            supplier=sub_pricing.supplier,
            goods_subtotal=sub_pricing.goods_subtotal,
            discount_amount=sub_pricing.discount_amount,
            shipping_amount=sub_pricing.shipping_amount,
            vat_amount=sub_pricing.vat_amount,
            subtotal=sub_pricing.total,
            fulfilment_mode=sub_pricing.fulfilment_mode,
        )
        quote = courier_quotes.get(sub_pricing.supplier.pk)
        if quote is not None:
            from apps.delivery import services as delivery_services

            delivery_services.record_quote(sub, quote)
        for line in sub_pricing.lines:
            v = line.variant
            OrderItem.objects.create(
                sub_order=sub,
                variant=v,
                product_name=v.product.name,
                variant_name=v.name,
                sku=v.sku,
                quantity=line.quantity,
                unit_price=line.unit_price,
                vat_rate=line.vat_rate,
                vat_amount=line.vat_amount,
                return_policy=v.product.effective_return_policy,
            )

    return order


@transaction.atomic
def confirm_sub_order(sub_order: SubOrder) -> SubOrder:
    if sub_order.status != OrderStatus.PENDING:
        raise ValueError(f"Cannot confirm a sub-order with status {sub_order.status}.")
    sub_order.status = OrderStatus.CONFIRMED
    sub_order.save(update_fields=["status", "updated_at"])
    _sync_order_status(sub_order.order)
    ref, s = sub_order.order.reference, sub_order.order.status
    transaction.on_commit(lambda: _push_order_status(ref, s))
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
    ref, s = sub_order.order.reference, sub_order.order.status
    transaction.on_commit(lambda: _push_order_status(ref, s))
    transaction.on_commit(lambda: _safe_send_shipping_update(sub_order))
    # Platform-brokered delivery: the supplier has marked the parcel ready, so book the courier
    # now (ADR-013 §#5). After commit so a provider call never holds the dispatch transaction open.
    if sub_order.fulfilment_mode == FulfilmentMode.PLATFORM_DELIVERY:
        transaction.on_commit(lambda: _safe_book_courier(sub_order))
    return sub_order


def _safe_book_courier(sub_order: SubOrder) -> None:
    try:
        from apps.delivery import services as delivery_services

        delivery_services.book_delivery(sub_order)
    except Exception:
        logger.exception("Failed to book courier for sub_order %s", sub_order.id)


@transaction.atomic
def deliver_sub_order(sub_order: SubOrder) -> SubOrder:
    if sub_order.status != OrderStatus.DISPATCHED:
        raise ValueError(f"Cannot deliver a sub-order with status {sub_order.status}.")
    sub_order.status = OrderStatus.DELIVERED
    sub_order.delivered_at = timezone.now()
    sub_order.save(update_fields=["status", "delivered_at", "updated_at"])
    _sync_order_status(sub_order.order)
    _trigger_sub_order_payout(sub_order)
    ref, s = sub_order.order.reference, sub_order.order.status
    transaction.on_commit(lambda: _push_order_status(ref, s))
    transaction.on_commit(lambda: _safe_send_delivery_confirmation(sub_order))
    return sub_order


def _safe_send_shipping_update(sub_order: SubOrder) -> None:
    try:
        from apps.notifications.email_service import send_shipping_update

        send_shipping_update(sub_order)
    except Exception:
        logger.exception("Failed to send shipping update email for sub_order %s", sub_order.id)


def _safe_send_delivery_confirmation(sub_order: SubOrder) -> None:
    try:
        from apps.notifications.email_service import send_delivery_confirmation

        send_delivery_confirmation(sub_order)
    except Exception:
        logger.exception(
            "Failed to send delivery confirmation email for sub_order %s", sub_order.id
        )


def _trigger_sub_order_payout(sub_order: SubOrder) -> None:
    """Queue a payout transfer for the sub-order's Payout record if one exists."""
    from apps.payments.models import Payout, PayoutStatus
    from apps.payments.tasks import trigger_payout

    try:
        payout = Payout.objects.get(sub_order=sub_order, status=PayoutStatus.PENDING)
        payout_id = str(payout.id)
        transaction.on_commit(lambda: trigger_payout.delay(payout_id))
        logger.info("Queued payout task for sub_order %s, payout %s", sub_order.id, payout.id)
    except Payout.DoesNotExist:
        logger.warning("No pending payout found for sub_order %s", sub_order.id)
    except Exception:
        logger.exception("Failed to queue payout task for sub_order %s", sub_order.id)


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
    ref, s = sub_order.order.reference, sub_order.order.status
    transaction.on_commit(lambda: _push_order_status(ref, s))
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
def request_return(sub_order: SubOrder, raised_by, reason: str, items=None) -> OrderReturn:
    """Request a return. ``items`` is an optional list of ``{"order_item": OrderItem,
    "quantity": int}``; omit it (or pass an empty list) for a full sub-order return."""
    if sub_order.status != OrderStatus.DELIVERED:
        raise ValueError("Returns can only be requested for delivered sub-orders.")
    if not sub_order.delivered_at or timezone.now() > sub_order.delivered_at + timedelta(
        days=RETURN_WINDOW_DAYS
    ):
        raise ValueError(f"Returns must be requested within {RETURN_WINDOW_DAYS} days of delivery.")

    lines = items or []
    # Validate everything before creating any row, so a rejected request leaves no orphan
    # OrderReturn. Return eligibility is the snapshotted policy (ADR-014): a non-returnable
    # item (e.g. perishable) has no change-of-mind return and must go via a dispute instead.
    if not lines:
        non_returnable = sorted({i.sku for i in sub_order.items.all() if not i.is_returnable})
        if non_returnable:
            raise ValueError(
                f"This order contains non-returnable items ({', '.join(non_returnable)}), "
                "such as perishable goods. Return the eligible items individually, or raise a "
                "dispute if they arrived damaged or spoiled."
            )
    for line in lines:
        order_item = line["order_item"]
        quantity = int(line["quantity"])
        if order_item.sub_order_id != sub_order.id:
            raise ValueError("Return item does not belong to this sub-order.")
        if not order_item.is_returnable:
            raise ValueError(
                f"{order_item.sku} is non-returnable (e.g. a perishable item) and can only be "
                "refunded if it arrives damaged or spoiled; please raise a dispute for it."
            )
        if quantity <= 0:
            raise ValueError("Return quantity must be positive.")
        if quantity > order_item.returnable_quantity:
            raise ValueError(
                f"Cannot return {quantity} of {order_item.sku}; "
                f"only {order_item.returnable_quantity} remain returnable."
            )

    ret = OrderReturn.objects.create(sub_order=sub_order, raised_by=raised_by, reason=reason)
    for line in lines:
        ReturnItem.objects.create(
            order_return=ret, order_item=line["order_item"], quantity=int(line["quantity"])
        )
    return ret


@transaction.atomic
def approve_return(return_obj: OrderReturn, notes: str = "") -> OrderReturn:
    if return_obj.status != ReturnStatus.REQUESTED:
        raise ValueError("Can only approve a requested return.")
    return_obj.status = ReturnStatus.APPROVED
    return_obj.supplier_notes = notes
    return_obj.save(update_fields=["status", "supplier_notes", "updated_at"])
    return return_obj


@transaction.atomic
def reject_return(return_obj: OrderReturn, notes: str = "") -> OrderReturn:
    if return_obj.status != ReturnStatus.REQUESTED:
        raise ValueError("Can only reject a requested return.")
    return_obj.status = ReturnStatus.REJECTED
    return_obj.supplier_notes = notes
    return_obj.save(update_fields=["status", "supplier_notes", "updated_at"])
    return return_obj


def _return_refund_amount(return_obj: OrderReturn) -> Decimal:
    """Refund due for a return.

    No items, or items covering the whole sub-order in one request, means the full sub-order total
    (goods - discount + shipping). A genuine partial return refunds only the returned units'
    discounted, VAT-inclusive value (goods, no shipping - the buyer still received a delivery),
    the discount allocated pro rata by returned goods value.
    """
    sub = return_obj.sub_order
    return_items = list(return_obj.items.select_related("order_item"))
    if not return_items:
        return sub.subtotal

    returned_gross = sum(
        (ri.order_item.unit_price * ri.quantity for ri in return_items), Decimal("0.00")
    )
    if returned_gross >= sub.goods_subtotal:  # every unit returned in one request
        return sub.subtotal

    discount_share = Decimal("0.00")
    if sub.discount_amount > 0 and sub.goods_subtotal > 0:
        discount_share = (sub.discount_amount * returned_gross / sub.goods_subtotal).quantize(
            Decimal("0.01")
        )
    return (returned_gross - discount_share).quantize(Decimal("0.01"))


def process_return_refund(return_obj: OrderReturn, refund_amount=None) -> OrderReturn:
    from apps.payments import services as payment_services

    # Phase 1: atomically claim the return by advancing it from APPROVED to
    # REFUNDING and locking in the refund amount. A concurrent caller blocks on
    # the row lock and, after this transaction commits, sees REFUNDING (retry
    # path) or REFUNDED (already done) rather than APPROVED.
    with transaction.atomic():
        locked = OrderReturn.objects.select_for_update().get(pk=return_obj.pk)

        if locked.status == ReturnStatus.REFUNDED:
            return locked

        if locked.status not in (ReturnStatus.APPROVED, ReturnStatus.REFUNDING):
            raise ValueError("Can only refund an approved return.")

        payment = getattr(locked.sub_order.order, "payment", None)
        if payment is None:
            raise ValueError("No payment found for this order.")

        if locked.status == ReturnStatus.APPROVED:
            # Default to the returned units' value (full sub-order total when the whole sub-order
            # is returned, incl shipping; goods-only for a partial return). See _return_refund_amount.
            amount = (
                Decimal(str(refund_amount))
                if refund_amount is not None
                else _return_refund_amount(locked)
            )
            locked.refund_amount = amount
            locked.status = ReturnStatus.REFUNDING
            locked.save(update_fields=["status", "refund_amount", "updated_at"])
            claimed_this_call = True
        else:
            # REFUNDING retry: a previous attempt claimed the return and set the
            # amount. Ignore the caller's refund_amount to prevent a second Stripe
            # charge for a different value.
            assert locked.refund_amount is not None, (
                "REFUNDING return must have a stored refund_amount"
            )
            amount = locked.refund_amount
            claimed_this_call = False

    # Phase 2: call Stripe outside any DB transaction so the connection is not
    # held open during the network round-trip. Only the caller that performed
    # the APPROVED→REFUNDING transition resets the claim on failure; a retry
    # that merely observed REFUNDING must not release a claim it does not own.
    try:
        payment_services.initiate_refund(payment, amount=amount)
    except Exception:
        if claimed_this_call:
            with transaction.atomic():
                OrderReturn.objects.filter(pk=locked.pk, status=ReturnStatus.REFUNDING).update(
                    status=ReturnStatus.APPROVED
                )
        raise

    # Phase 2b: reverse the fulfilling supplier's transfer for the refunded share so the
    # platform does not absorb money already paid out. Idempotent; a failure here leaves the
    # return REFUNDING and re-runs on retry (the buyer refund above is idempotent too).
    sub_total = locked.sub_order.subtotal
    ratio = (amount / sub_total) if sub_total > 0 else Decimal("0")
    payment_services.reverse_payout_for_sub_order(locked.sub_order, ratio)

    # Phase 3: return inventory and mark REFUNDED. Re-read under lock in case a
    # concurrent retry also reached Stripe; bail early if already REFUNDED.
    with transaction.atomic():
        final = OrderReturn.objects.select_for_update().get(pk=locked.pk)
        if final.status == ReturnStatus.REFUNDED:
            return final

        return_items = list(final.items.select_related("order_item__variant"))
        if return_items:
            # Partial (or explicit-item) return: restock only the returned units.
            for ri in return_items:
                inventory_services.return_stock(
                    ri.order_item.variant,
                    ri.quantity,
                    notes=f"Return {final.id}",
                )
        else:
            # Full sub-order return: restock every item.
            for item in final.sub_order.items.select_related("variant"):
                inventory_services.return_stock(
                    item.variant,
                    item.quantity,
                    notes=f"Return {final.id}",
                )
        final.status = ReturnStatus.REFUNDED
        final.save(update_fields=["status", "updated_at"])
    return final


def _create_admin_return(
    sub_order: SubOrder, raised_by, reason: str, item_lines: list
) -> OrderReturn:
    """Create an already-approved return for an admin item refund (validates quantities)."""
    ret = OrderReturn.objects.create(
        sub_order=sub_order,
        raised_by=raised_by,
        reason=reason,
        status=ReturnStatus.APPROVED,
    )
    for line in item_lines:
        order_item: OrderItem = line["order_item"]
        quantity = int(line["quantity"])
        if quantity <= 0:
            raise ValueError("Refund quantity must be positive.")
        # returnable_quantity counts units already covered by non-rejected returns (including
        # rows created earlier in this same request), so the same units cannot be refunded twice.
        if quantity > order_item.returnable_quantity:
            raise ValueError(
                f"Cannot refund {quantity} of {order_item.sku}; "
                f"only {order_item.returnable_quantity} remain refundable."
            )
        ReturnItem.objects.create(order_return=ret, order_item=order_item, quantity=quantity)
    return ret


def admin_refund_order_items(
    order: Order, item_selections: list, *, raised_by, reason: str = "Admin item refund"
) -> list[OrderReturn]:
    """Admin-initiated per-item refund attributed to the supplier that sold each item.

    ``item_selections`` is a list of ``{"order_item": OrderItem, "quantity": int}``. Items are
    grouped by sub-order (one supplier each); an approved return is created per sub-order and
    driven through ``process_return_refund``, so the buyer is refunded the selected units'
    discounted, VAT-inclusive value and each supplier's payout is reversed proportionally
    (ADR-012). Unlike a buyer return this is not gated on delivery status or the return window,
    and it restocks the refunded units.

    Returns the processed ``OrderReturn`` objects, one per affected supplier.
    """
    if not item_selections:
        raise ValueError("Select at least one item to refund.")

    groups: dict = {}
    for line in item_selections:
        order_item: OrderItem = line["order_item"]
        if order_item.sub_order.order_id != order.id:
            raise ValueError("Refund item does not belong to this order.")
        group = groups.setdefault(
            order_item.sub_order_id, {"sub_order": order_item.sub_order, "lines": []}
        )
        group["lines"].append(line)

    # Create every return up front (and validate quantities) so a bad selection fails before any
    # money moves. Each return is then processed through the refund + payout-reversal path.
    with transaction.atomic():
        returns = [
            _create_admin_return(g["sub_order"], raised_by, reason, g["lines"])
            for g in groups.values()
        ]

    return [process_return_refund(ret) for ret in returns]
