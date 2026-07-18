import uuid

from django.db import models
from django.utils import timezone

from .providers.base import DeliveryStatus


class CourierDelivery(models.Model):
    """A platform-brokered delivery for one sub-order, and the reconciliation ledger row for it
    (buyer fee charged vs courier cost paid). One per sub-order (ADR-013)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sub_order = models.OneToOneField(
        "orders.SubOrder", on_delete=models.CASCADE, related_name="courier_delivery"
    )
    provider = models.CharField(max_length=40)
    provider_quote_id = models.CharField(max_length=100)
    provider_delivery_id = models.CharField(max_length=100, blank=True)
    fee_charged = models.DecimalField(max_digits=8, decimal_places=2)
    courier_cost = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=3, default="GBP")
    status = models.CharField(
        max_length=12, choices=DeliveryStatus.CHOICES, default=DeliveryStatus.QUOTED
    )
    tracking_url = models.URLField(blank=True)
    quote_expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"CourierDelivery {self.sub_order_id} ({self.status})"

    @property
    def is_quote_expired(self) -> bool:
        return timezone.now() > self.quote_expires_at
