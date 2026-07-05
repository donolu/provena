import uuid

from django.db import models
from django.utils import timezone


class DisputeType(models.TextChoices):
    # Buyer-initiated
    NOT_RECEIVED = "NOT_RECEIVED", "Item not received"
    DAMAGED = "DAMAGED", "Item damaged or spoiled"
    WRONG_ITEM = "WRONG_ITEM", "Wrong item received"
    PARTIAL_DELIVERY = "PARTIAL_DELIVERY", "Partial delivery"
    # Supplier-initiated
    FALSE_CLAIM = "FALSE_CLAIM", "False claim"
    DELIVERY_REFUSED = "DELIVERY_REFUSED", "Delivery refused by buyer"
    FRAUDULENT_CANCELLATION = "FRAUDULENT_CANCELLATION", "Fraudulent cancellation"


class ResolutionRequested(models.TextChoices):
    FULL_REFUND = "FULL_REFUND", "Full refund"
    PARTIAL_REFUND = "PARTIAL_REFUND", "Partial refund"
    REPLACEMENT = "REPLACEMENT", "Replacement"
    NO_ACTION = "NO_ACTION", "No action"


class DisputeStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    RESPONDENT_REPLIED = "RESPONDENT_REPLIED", "Respondent replied"
    ESCALATED = "ESCALATED", "Escalated to admin"
    RESOLVED = "RESOLVED", "Resolved"
    CLOSED = "CLOSED", "Closed"


class DisputeOutcome(models.TextChoices):
    FULL_REFUND = "FULL_REFUND", "Full refund"
    PARTIAL_REFUND = "PARTIAL_REFUND", "Partial refund"
    REPLACEMENT = "REPLACEMENT", "Replacement"
    REJECTED = "REJECTED", "Rejected (in favour of respondent)"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"


class DisputeEventType(models.TextChoices):
    OPENED = "OPENED", "Opened"
    RESPONDED = "RESPONDED", "Responded"
    ESCALATED = "ESCALATED", "Escalated"
    RESOLVED = "RESOLVED", "Resolved"
    CLOSED = "CLOSED", "Closed"
    ADMIN_NOTE = "ADMIN_NOTE", "Admin note"


# Types that always use a fixed 14-day window regardless of category setting.
FIXED_WINDOW_TYPES = frozenset(
    [
        DisputeType.NOT_RECEIVED,
        DisputeType.DELIVERY_REFUSED,
        DisputeType.FRAUDULENT_CANCELLATION,
    ]
)
FIXED_WINDOW_DAYS = 14


class Dispute(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sub_order = models.ForeignKey(
        "orders.SubOrder", on_delete=models.PROTECT, related_name="disputes"
    )
    opened_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="disputes_opened"
    )
    respondent = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="disputes_received"
    )
    dispute_type = models.CharField(max_length=30, choices=DisputeType.choices)
    description = models.TextField()
    resolution_requested = models.CharField(max_length=20, choices=ResolutionRequested.choices)
    status = models.CharField(
        max_length=20, choices=DisputeStatus.choices, default=DisputeStatus.OPEN
    )
    outcome = models.CharField(max_length=20, choices=DisputeOutcome.choices, blank=True)
    outcome_amount_pence = models.PositiveIntegerField(null=True, blank=True)
    outcome_notes = models.TextField(blank=True)
    response_deadline = models.DateTimeField()
    payout_held = models.BooleanField(default=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at"]

    def __str__(self) -> str:
        return f"Dispute {self.id} on {self.sub_order}"

    @property
    def is_overdue(self) -> bool:
        return self.status == DisputeStatus.OPEN and timezone.now() > self.response_deadline


class DisputeEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name="events")
    author = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="dispute_events"
    )
    event_type = models.CharField(max_length=20, choices=DisputeEventType.choices)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.event_type} on {self.dispute_id} by {self.author_id}"


class DisputeRefundStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"


class DisputeRefund(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(Dispute, on_delete=models.PROTECT, related_name="refunds")
    sub_order = models.ForeignKey(
        "orders.SubOrder", on_delete=models.PROTECT, related_name="dispute_refunds"
    )
    stripe_refund_id = models.CharField(max_length=100, unique=True)
    amount_pence = models.PositiveIntegerField()
    status = models.CharField(
        max_length=12, choices=DisputeRefundStatus.choices, default=DisputeRefundStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Refund {self.stripe_refund_id} ({self.amount_pence}p)"
