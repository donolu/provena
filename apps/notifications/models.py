import uuid

from django.db import models


class NotificationType(models.TextChoices):
    LOW_STOCK = "LOW_STOCK", "Low Stock Alert"
    ORDER_PLACED = "ORDER_PLACED", "Order Placed"
    ORDER_DISPATCHED = "ORDER_DISPATCHED", "Order Dispatched"
    ORDER_DELIVERED = "ORDER_DELIVERED", "Order Delivered"
    PAYMENT_SUCCEEDED = "PAYMENT_SUCCEEDED", "Payment Succeeded"
    GENERAL = "GENERAL", "General"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL,
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.notification_type}] {self.title} -> {self.recipient.email}"
