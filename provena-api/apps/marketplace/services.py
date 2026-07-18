import contextlib
import uuid
from datetime import datetime, timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.catalogue.models import ProductVariant
from apps.inventory import services as inventory_services
from apps.orders.models import OrderStatus

from .models import RESERVATION_MINUTES, Cart, CartItem, CartReservation, Review, WishlistItem

CART_COOKIE = "provena_cart"


def _reservation_expiry() -> datetime:
    return timezone.now() + timedelta(minutes=RESERVATION_MINUTES)


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------


def get_or_create_cart(*, user=None, session_key: str | None = None) -> Cart:
    if user is not None:
        cart, _ = Cart.objects.get_or_create(buyer=user)
        return cart
    if session_key:
        cart, _ = Cart.objects.get_or_create(session_key=session_key)
        return cart
    raise ValueError("Either user or session_key is required.")


def new_session_key() -> str:
    return str(uuid.uuid4())


def _item_filter(user=None, session_key: str | None = None) -> dict:
    if user is not None:
        return {"cart__buyer": user}
    return {"cart__session_key": session_key}


@transaction.atomic
def add_to_cart(
    *, user=None, session_key: str | None = None, variant_id, quantity: int
) -> CartItem:
    if quantity <= 0:
        raise ValueError("Quantity must be at least 1.")
    variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)
    cart = get_or_create_cart(user=user, session_key=session_key)
    item, created = CartItem.objects.get_or_create(
        cart=cart, variant=variant, defaults={"quantity": quantity}
    )
    if not created:
        item = CartItem.objects.select_for_update().get(pk=item.pk)
        item.quantity += quantity
        item.save(update_fields=["quantity", "updated_at"])

    inventory_services.reserve_stock(variant, quantity, reference=f"CART:{item.id}")
    CartReservation.objects.update_or_create(
        cart_item=item,
        defaults={
            "variant": variant,
            "quantity": item.quantity,
            "expires_at": _reservation_expiry(),
        },
    )
    return item


@transaction.atomic
def update_cart_item(
    *, user=None, session_key: str | None = None, item_id, quantity: int
) -> CartItem:
    if quantity <= 0:
        raise ValueError("Quantity must be at least 1.")
    item = get_object_or_404(
        CartItem.objects.select_for_update(), id=item_id, **_item_filter(user, session_key)
    )
    old_qty = item.quantity
    delta = quantity - old_qty
    if delta > 0:
        inventory_services.reserve_stock(item.variant, delta, reference=f"CART:{item.id}")
    elif delta < 0:
        inventory_services.release_reservation(item.variant, -delta, reference=f"CART:{item.id}")
    item.quantity = quantity
    item.save(update_fields=["quantity", "updated_at"])
    CartReservation.objects.update_or_create(
        cart_item=item,
        defaults={
            "variant": item.variant,
            "quantity": quantity,
            "expires_at": _reservation_expiry(),
        },
    )
    return item


@transaction.atomic
def remove_from_cart(*, user=None, session_key: str | None = None, item_id) -> None:
    item = get_object_or_404(
        CartItem.objects.select_for_update(), id=item_id, **_item_filter(user, session_key)
    )
    with contextlib.suppress(CartReservation.DoesNotExist):
        res = item.reservation
        inventory_services.release_reservation(
            item.variant, res.quantity, reference=f"CART:{item.id}"
        )
    item.delete()


@transaction.atomic
def clear_cart(*, user=None, session_key: str | None = None) -> None:
    # Materialise the locked set so we delete exactly these IDs, not any CartItems
    # inserted by a concurrent add_to_cart() after the lock was taken.
    # of=("self",) restricts the lock to marketplace_cartitem rows only; without it
    # PostgreSQL rejects FOR UPDATE because select_related("reservation") produces a
    # LEFT OUTER JOIN on the nullable reverse-OneToOne and PG forbids locking on that.
    items = list(
        CartItem.objects.select_for_update(of=("self",))
        .filter(**_item_filter(user, session_key))
        .select_related("reservation", "variant")
    )
    locked_ids = []
    for item in items:
        locked_ids.append(item.id)
        with contextlib.suppress(CartReservation.DoesNotExist):
            res = item.reservation
            inventory_services.release_reservation(
                item.variant, res.quantity, reference=f"CART:{item.id}"
            )
    if locked_ids:
        CartItem.objects.filter(id__in=locked_ids).delete()


@transaction.atomic
def merge_guest_cart(session_key: str, user) -> None:
    """Move items from a guest cart into the authenticated user's cart.

    Stock reservations are preserved: for items in both carts the quantities are summed
    and the guest CartReservation is deleted without releasing stock (the units stay
    reserved under the user's CartReservation). For guest-only items the CartItem row is
    moved to the user cart so its CartReservation follows automatically.
    """
    try:
        guest_cart = Cart.objects.select_for_update().get(session_key=session_key)
    except Cart.DoesNotExist:
        return

    user_cart = get_or_create_cart(user=user)

    for item in list(guest_cart.items.select_for_update(of=("self",)).select_related("variant")):
        try:
            existing = CartItem.objects.select_for_update().get(
                cart=user_cart, variant=item.variant
            )
            existing.quantity += item.quantity
            existing.save(update_fields=["quantity", "updated_at"])
            CartReservation.objects.update_or_create(
                cart_item=existing,
                defaults={
                    "variant": item.variant,
                    "quantity": existing.quantity,
                    "expires_at": _reservation_expiry(),
                },
            )
            item.delete()
        except CartItem.DoesNotExist:
            item.cart = user_cart
            item.save(update_fields=["cart"])
            with contextlib.suppress(CartReservation.DoesNotExist):
                res = item.reservation
                res.expires_at = _reservation_expiry()
                res.save(update_fields=["expires_at"])

    guest_cart.delete()


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------


def add_to_wishlist(user, variant_id) -> WishlistItem:
    variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)
    item, _ = WishlistItem.objects.get_or_create(buyer=user, variant=variant)
    return item


def remove_from_wishlist(user, item_id) -> None:
    get_object_or_404(WishlistItem, id=item_id, buyer=user).delete()


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------


@transaction.atomic
def create_review(user, variant_id, rating: int, title: str, body: str) -> Review:
    variant = get_object_or_404(ProductVariant, id=variant_id)
    if Review.objects.filter(reviewer=user, variant=variant).exists():
        raise ValueError("You have already submitted a review for this product.")

    from apps.orders.models import OrderItem

    has_delivered_order = OrderItem.objects.filter(
        variant=variant,
        sub_order__order__buyer=user,
        sub_order__status=OrderStatus.DELIVERED,
    ).exists()

    if not has_delivered_order:
        raise ValueError("You can only review products you have purchased and received.")

    return Review.objects.create(
        variant=variant,
        reviewer=user,
        rating=rating,
        title=title,
        body=body,
        is_verified_purchase=True,
        is_approved=False,
    )


def approve_review(review: Review) -> Review:
    review.is_approved = True
    review.save(update_fields=["is_approved", "updated_at"])
    return review
