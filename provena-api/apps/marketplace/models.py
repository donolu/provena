import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

RESERVATION_MINUTES = 30


class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Cart({self.buyer.email})"

    @property
    def total(self) -> Decimal:
        return sum((item.subtotal for item in self.items.all()), Decimal("0.00"))

    @property
    def item_count(self) -> int:
        return self.items.count()


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        "catalogue.ProductVariant",
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField()
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("cart", "variant")]
        ordering = ["added_at"]

    def __str__(self) -> str:
        return f"{self.variant.sku} x{self.quantity}"

    @property
    def subtotal(self) -> Decimal:
        return self.variant.price * self.quantity


class CartReservation(models.Model):
    """Tracks a stock reservation held against a cart item. Expires after RESERVATION_MINUTES."""

    cart_item = models.OneToOneField(
        CartItem,
        on_delete=models.CASCADE,
        related_name="reservation",
    )
    variant = models.ForeignKey(
        "catalogue.ProductVariant",
        on_delete=models.CASCADE,
        related_name="cart_reservations",
    )
    quantity = models.PositiveIntegerField()
    reserved_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["expires_at"]

    def __str__(self) -> str:
        return f"Reservation {self.variant.sku} x{self.quantity} (expires {self.expires_at:%H:%M})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at


class WishlistItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="wishlist")
    variant = models.ForeignKey(
        "catalogue.ProductVariant",
        on_delete=models.CASCADE,
        related_name="wishlisted_by",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("buyer", "variant")]
        ordering = ["-added_at"]

    def __str__(self) -> str:
        return f"{self.buyer.email} / {self.variant.sku}"


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.ForeignKey(
        "catalogue.ProductVariant",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    reviewer = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("reviewer", "variant")]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.rating}/5 on {self.variant.sku}"
