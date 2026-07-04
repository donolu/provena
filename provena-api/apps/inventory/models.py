import uuid

from django.db import models


class MovementType(models.TextChoices):
    INBOUND = "INBOUND", "Inbound Receipt"
    OUTBOUND = "OUTBOUND", "Outbound Dispatch"
    ADJUSTMENT = "ADJUSTMENT", "Manual Adjustment"
    RETURN = "RETURN", "Customer Return"
    RESERVED = "RESERVED", "Order Reserved"
    UNRESERVED = "UNRESERVED", "Reservation Released"


class StockLevel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.OneToOneField(
        "catalogue.ProductVariant",
        on_delete=models.CASCADE,
        related_name="stock",
    )
    quantity_available = models.PositiveIntegerField(default=0)
    quantity_reserved = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.variant.sku}: {self.quantity_available} available"

    @property
    def quantity_on_hand(self) -> int:
        return self.quantity_available + self.quantity_reserved

    @property
    def is_low_stock(self) -> bool:
        return self.low_stock_threshold > 0 and self.quantity_available <= self.low_stock_threshold


class StockLot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.ForeignKey(
        "catalogue.ProductVariant",
        on_delete=models.CASCADE,
        related_name="lots",
    )
    lot_number = models.CharField(max_length=100, blank=True)
    quantity_received = models.PositiveIntegerField()
    quantity_remaining = models.PositiveIntegerField()
    received_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["expires_at", "received_at"]

    def __str__(self) -> str:
        label = self.lot_number or str(self.id)
        return f"Lot {label} — {self.variant.sku}"


class StockMovement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.ForeignKey(
        "catalogue.ProductVariant",
        on_delete=models.CASCADE,
        related_name="movements",
    )
    movement_type = models.CharField(max_length=12, choices=MovementType.choices)
    quantity = models.IntegerField()
    quantity_after = models.PositiveIntegerField()
    reference = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stock_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        sign = "+" if self.quantity >= 0 else ""
        return f"{self.variant.sku} {sign}{self.quantity} ({self.movement_type})"
