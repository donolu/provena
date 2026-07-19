import random
import string
import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.catalogue.models import ReturnPolicy, VatRate
from apps.suppliers.models import FulfilmentMode


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    CONFIRMED = "CONFIRMED", "Confirmed"
    DISPATCHED = "DISPATCHED", "Dispatched"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"


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
    goods_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    shipping_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    # Snapshot of the applied discount code and who funded it (drives the payout split).
    discount_code = models.CharField(max_length=40, blank=True)
    discount_funded_by = models.CharField(max_length=10, blank=True)
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
    goods_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    shipping_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    # Snapshot of who delivers this sub-order (drives shipping attribution in payouts, ADR-013).
    fulfilment_mode = models.CharField(
        max_length=20,
        choices=FulfilmentMode.choices,
        default=FulfilmentMode.SUPPLIER_SHIP,
    )
    tracking_number = models.CharField(max_length=200, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
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
    vat_rate = models.CharField(max_length=10, choices=VatRate.choices, default=VatRate.STANDARD)
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    # Return policy snapshotted at checkout from the product's effective policy (ADR-014), so a
    # later re-classification of the product/category never changes a placed order's rights.
    # Existing rows backfill to RETURNABLE (they were placed under the flat 14-day regime).
    return_policy = models.CharField(
        max_length=16, choices=ReturnPolicy.choices, default=ReturnPolicy.RETURNABLE
    )

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.sku} x {self.quantity}"

    @property
    def is_returnable(self) -> bool:
        """Whether this item is eligible for a change-of-mind return (ADR-014).
        A non-returnable item that arrives defective is handled via a dispute."""
        return self.return_policy == ReturnPolicy.RETURNABLE

    @property
    def total_price(self) -> Decimal:
        return self.unit_price * self.quantity

    @property
    def returned_quantity(self) -> int:
        """Units already returned across this item's non-rejected returns."""
        from django.db.models import Sum

        agg = self.return_items.exclude(order_return__status=ReturnStatus.REJECTED).aggregate(
            total=Sum("quantity")
        )
        return agg["total"] or 0

    @property
    def returnable_quantity(self) -> int:
        return self.quantity - self.returned_quantity


class ReturnStatus(models.TextChoices):
    REQUESTED = "REQUESTED", "Requested"
    APPROVED = "APPROVED", "Approved"
    REFUNDING = "REFUNDING", "Refunding"
    REJECTED = "REJECTED", "Rejected"
    REFUNDED = "REFUNDED", "Refunded"


RETURN_WINDOW_DAYS = 14


class OrderReturn(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sub_order = models.ForeignKey(SubOrder, on_delete=models.CASCADE, related_name="returns")
    raised_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="return_requests",
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=12, choices=ReturnStatus.choices, default=ReturnStatus.REQUESTED
    )
    supplier_notes = models.TextField(blank=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Return on {self.sub_order} ({self.status})"


class ReturnItem(models.Model):
    """A specific item + quantity within a return. A return with no items is a full sub-order return."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_return = models.ForeignKey(OrderReturn, on_delete=models.CASCADE, related_name="items")
    order_item = models.ForeignKey(OrderItem, on_delete=models.PROTECT, related_name="return_items")
    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.order_item.sku} x{self.quantity} (return {self.order_return_id})"


class DiscountType(models.TextChoices):
    PERCENTAGE = "PERCENTAGE", "Percentage"
    FIXED = "FIXED", "Fixed amount"


class DiscountFunding(models.TextChoices):
    PLATFORM = "PLATFORM", "Platform"
    SUPPLIER = "SUPPLIER", "Supplier"


class DiscountCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=40, unique=True)
    discount_type = models.CharField(max_length=10, choices=DiscountType.choices)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    funded_by = models.CharField(
        max_length=10, choices=DiscountFunding.choices, default=DiscountFunding.PLATFORM
    )
    minimum_spend = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    max_uses_per_buyer = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.code

    def save(self, *args, **kwargs) -> None:
        self.code = self.code.upper()
        super().save(*args, **kwargs)

    def is_live(self, now) -> bool:
        if not self.is_active:
            return False
        if self.valid_from is not None and now < self.valid_from:
            return False
        if self.valid_until is not None and now > self.valid_until:
            return False
        return True

    def compute_discount(self, goods_subtotal: Decimal) -> Decimal:
        """The discount for a pre-discount goods value, capped at that value."""
        if self.discount_type == DiscountType.PERCENTAGE:
            raw = goods_subtotal * self.value / Decimal("100")
        else:
            raw = self.value
        capped = min(raw, goods_subtotal)
        return capped.quantize(Decimal("0.01"))


class DiscountRedemption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.ForeignKey(DiscountCode, on_delete=models.PROTECT, related_name="redemptions")
    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="discount_redemptions"
    )
    # One redemption per order makes application idempotent under retries.
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="discount_redemption"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.code} on {self.order.reference} (£{self.amount})"
