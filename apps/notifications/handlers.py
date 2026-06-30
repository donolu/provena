import logging

logger = logging.getLogger(__name__)


def handle_low_stock_alert(sender, variant, stock_level, quantity_available, **kwargs):
    from django.contrib.auth import get_user_model

    from . import services
    from .models import NotificationType

    User = get_user_model()
    title = f"Low stock: {variant.sku}"
    body = (
        f"{variant.name} (SKU: {variant.sku}) has {quantity_available} units remaining, "
        f"at or below the reorder threshold of {stock_level.low_stock_threshold}."
    )
    data = {
        "notification_type": NotificationType.LOW_STOCK,
        "variant_id": str(variant.id),
        "variant_sku": variant.sku,
        "quantity_available": quantity_available,
        "low_stock_threshold": stock_level.low_stock_threshold,
    }
    for user in User.objects.filter(is_staff=True, is_active=True):
        try:
            services.notify(
                recipient=user,
                title=title,
                body=body,
                notification_type=NotificationType.LOW_STOCK,
                data=data,
            )
        except Exception:
            logger.exception("Failed to notify staff user %s for low stock alert", user.email)
