from datetime import datetime, timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.catalogue.models import ProductVariant
from apps.inventory import services as inventory_services
from apps.orders.models import OrderStatus

from .models import RESERVATION_MINUTES, Cart, CartItem, CartReservation, Review, WishlistItem


def _reservation_expiry() -> datetime:
    return timezone.now() + timedelta(minutes=RESERVATION_MINUTES)


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------


def get_or_create_cart(user) -> Cart:
    cart, _ = Cart.objects.get_or_create(buyer=user)
    return cart


@transaction.atomic
def add_to_cart(user, variant_id, quantity: int) -> CartItem:
    if quantity <= 0:
        raise ValueError("Quantity must be at least 1.")
    variant = get_object_or_404(ProductVariant, id=variant_id, is_active=True)
    cart = get_or_create_cart(user)
    item, created = CartItem.objects.get_or_create(
        cart=cart, variant=variant, defaults={"quantity": quantity}
    )
    if not created:
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
def update_cart_item(user, item_id, quantity: int) -> CartItem:
    if quantity <= 0:
        raise ValueError("Quantity must be at least 1.")
    item = get_object_or_404(CartItem, id=item_id, cart__buyer=user)
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
def remove_from_cart(user, item_id) -> None:
    item = get_object_or_404(CartItem, id=item_id, cart__buyer=user)
    try:
        res = item.reservation
        inventory_services.release_reservation(
            item.variant, res.quantity, reference=f"CART:{item.id}"
        )
    except CartReservation.DoesNotExist:
        pass
    item.delete()


@transaction.atomic
def clear_cart(user) -> None:
    items = CartItem.objects.filter(cart__buyer=user).select_related("reservation", "variant")
    for item in items:
        try:
            res = item.reservation
            inventory_services.release_reservation(
                item.variant, res.quantity, reference=f"CART:{item.id}"
            )
        except CartReservation.DoesNotExist:
            pass
    CartItem.objects.filter(cart__buyer=user).delete()


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

    is_verified = OrderItem.objects.filter(
        variant=variant,
        sub_order__order__buyer=user,
        sub_order__status=OrderStatus.DELIVERED,
    ).exists()

    return Review.objects.create(
        variant=variant,
        reviewer=user,
        rating=rating,
        title=title,
        body=body,
        is_verified_purchase=is_verified,
        is_approved=False,
    )


def approve_review(review: Review) -> Review:
    review.is_approved = True
    review.save(update_fields=["is_approved", "updated_at"])
    return review
