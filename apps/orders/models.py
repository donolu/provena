import random
import string
import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    CONFIRMED = "CONFIRMED", "Confirmed"
    DISPATCHED = "DISPATCHED", "Dispatched"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"


class DisputeStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    RESOLVED = "RESOLVED", "Resolved"
    REJECTED = "REJECTED", "Rejected"


def _generate_order_reference() -> str:
    date_part = timezone.now().strftime("%Y%m%d")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))  # noqa: S311  # nosec B311
    return f"ORD-{date_part}-{suffix}"


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="orders")
    reference = models.CharField(max_length=24, unique=True)
    status = models.CharField(
        max_length=12, choices=OrderStatus.choices, default=OrderStatus.PENDING
    )
    shipping_name = models.CharField(max_length=200)
    shipping_line1 = models.CharField(max_length=200)
    shipping_line2 = models.CharField(max_length=200, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_postcode = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.reference


class SubOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="sub_orders")
    supplier = models.ForeignKey(
        "suppliers.Supplier", on_delete=models.PROTECT, related_name="sub_orders"
    )
    status = models.CharField(
        max_length=12, choices=OrderStatus.choices, default=OrderStatus.PENDING
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tracking_number = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.order.reference} / {self.supplier.business_name}"


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sub_order = models.ForeignKey(SubOrder, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        "catalogue.ProductVariant",
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    product_name = models.CharField(max_length=200)
    variant_name = models.CharField(max_length=120)
    sku = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.sku} x {self.quantity}"

    @property
    def total_price(self) -> Decimal:
        return self.unit_price * self.quantity


class OrderDispute(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sub_order = models.ForeignKey(SubOrder, on_delete=models.CASCADE, related_name="disputes")
    raised_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="raised_disputes",
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=10, choices=DisputeStatus.choices, default=DisputeStatus.OPEN
    )
    resolution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Dispute on {self.sub_order} ({self.status})"
