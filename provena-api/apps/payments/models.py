import uuid

from django.db import models


class PaymentRefundRequestStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"
    PARTIALLY_REFUNDED = "PARTIAL_REFUND", "Partially refunded"
    REFUNDED = "REFUNDED", "Refunded"
    CANCELLED = "CANCELLED", "Cancelled"


class PayoutStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    PAID = "PAID", "Paid"
    FAILED = "FAILED", "Failed"
    REVERSED = "REVERSED", "Reversed"


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField("orders.Order", on_delete=models.PROTECT, related_name="payment")
    stripe_payment_intent_id = models.CharField(max_length=200, unique=True)
    stripe_client_secret = models.CharField(max_length=500, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="gbp")
    status = models.CharField(
        max_length=14, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    refunded_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending_refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.order.reference} / {self.status}"


class Payout(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sub_order = models.OneToOneField(
        "orders.SubOrder", on_delete=models.PROTECT, related_name="payout"
    )
    supplier = models.ForeignKey(
        "suppliers.Supplier", on_delete=models.PROTECT, related_name="payouts"
    )
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=12, decimal_places=2)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=12, choices=PayoutStatus.choices, default=PayoutStatus.PENDING
    )
    stripe_transfer_id = models.CharField(max_length=200, blank=True)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Payout {self.sub_order} / {self.status}"


class PaymentRefundRequest(models.Model):
    """Tracks each distinct refund attempt so retries reuse the same reservation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="refund_requests")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    stripe_idempotency_key = models.CharField(max_length=200, unique=True)
    stripe_refund_id = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=20,
        choices=PaymentRefundRequestStatus.choices,
        default=PaymentRefundRequestStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"RefundRequest {self.payment_id} / {self.amount} / {self.status}"
