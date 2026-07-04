import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def release_expired_cart_reservations() -> int:
    """Release stock held by expired cart reservations and remove the stale cart items."""
    from apps.inventory import services as inventory_services

    from .models import CartReservation

    expired = list(
        CartReservation.objects.filter(expires_at__lt=timezone.now()).select_related(
            "cart_item__variant"
        )
    )
    released = 0
    for res in expired:
        try:
            with transaction.atomic():
                inventory_services.release_reservation(
                    res.cart_item.variant,
                    res.quantity,
                    reference=f"CART_EXPIRED:{res.cart_item_id}",
                )
                res.cart_item.delete()
                released += 1
        except Exception:
            logger.exception("Failed to release expired cart reservation %s", res.id)

    if released:
        logger.info("Released %d expired cart reservation(s).", released)
    return released
