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
