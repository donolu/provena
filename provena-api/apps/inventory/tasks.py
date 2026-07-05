import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def check_low_stock_levels():
    """Periodic task: emit low_stock_alert for every StockLevel currently below threshold."""
    from .models import StockLevel
    from .signals import low_stock_alert

    triggered = 0
    for level in StockLevel.objects.select_related("variant").iterator():
        if level.is_low_stock:
            low_stock_alert.send(
                sender=StockLevel,
                variant=level.variant,
                stock_level=level,
                quantity_available=level.quantity_available,
            )
            triggered += 1

    logger.info("low_stock check: %d variants below threshold", triggered)
    return triggered


@shared_task
def check_lot_expiry(days_ahead: int = 3):
    """Daily task: create in-app notifications for lots expiring within `days_ahead` days."""
    from datetime import timedelta

    from django.utils.timezone import localdate

    from apps.notifications.models import Notification, NotificationType

    from .models import StockLot

    today = localdate()
    cutoff = today + timedelta(days=days_ahead)

    lots = (
        StockLot.objects.filter(
            expires_at__isnull=False,
            expires_at__lte=cutoff,
            expires_at__gte=today,
            quantity_remaining__gt=0,
        )
        .select_related("variant__product__supplier__user")
        .order_by("expires_at")
    )

    notified = 0
    for lot in lots:
        supplier = lot.variant.product.supplier
        if not supplier or not supplier.user_id:
            continue

        if lot.expires_at is None:  # should not happen given isnull=False filter
            continue
        days_left = (lot.expires_at - today).days
        label = lot.lot_number or str(lot.id)[:8]
        title = f"Lot {label} expires in {days_left} day{'s' if days_left != 1 else ''}"
        body = (
            f"{lot.variant.product.name} — {lot.variant.name}: "
            f"{lot.quantity_remaining} unit{'s' if lot.quantity_remaining != 1 else ''} "
            f"remaining, expiry {lot.expires_at.isoformat()}."
        )

        Notification.objects.get_or_create(
            recipient_id=supplier.user_id,
            notification_type=NotificationType.GENERAL,
            title=title,
            defaults={
                "body": body,
                "data": {"lot_id": str(lot.id), "variant_id": str(lot.variant_id)},
            },
        )
        notified += 1

    logger.info("lot_expiry check: %d expiry notification(s) created", notified)
    return notified
