import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def release_expired_cart_reservations() -> int:
    """Release stock held by expired cart reservations and remove the stale cart items."""
    from apps.inventory import services as inventory_services

    from .models import CartItem, CartReservation

    # Snapshot IDs only — quantity is re-read under the lock to avoid using stale data
    # if the reservation was renewed between this snapshot and the per-item lock.
    expired_ids = list(
        CartReservation.objects.filter(expires_at__lt=timezone.now()).values_list(
            "cart_item_id", flat=True
        )
    )
    released = 0
    for cart_item_id in expired_ids:
        try:
            with transaction.atomic():
                # Lock the CartItem to serialise with concurrent checkouts and cart updates.
                cart_item = CartItem.objects.select_for_update().get(pk=cart_item_id)
                # Re-fetch the reservation under the lock; if it was renewed (expires_at
                # pushed forward) or already consumed, DoesNotExist skips this item.
                try:
                    res = CartReservation.objects.get(
                        cart_item=cart_item,
                        expires_at__lt=timezone.now(),
                    )
                except CartReservation.DoesNotExist:
                    continue  # renewed or already released — nothing to do
                inventory_services.release_reservation(
                    cart_item.variant,
                    res.quantity,
                    reference=f"CART_EXPIRED:{cart_item_id}",
                )
                cart_item.delete()
                released += 1
        except CartItem.DoesNotExist:
            pass  # checkout already consumed this cart item
        except Exception:
            logger.exception("Failed to release expired cart reservation %s", cart_item_id)

    if released:
        logger.info("Released %d expired cart reservation(s).", released)
    return released
