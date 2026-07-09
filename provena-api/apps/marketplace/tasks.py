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

    expired = list(
        CartReservation.objects.filter(expires_at__lt=timezone.now()).values_list(
            "cart_item_id", "quantity"
        )
    )
    released = 0
    for cart_item_id, quantity in expired:
        try:
            with transaction.atomic():
                # Lock the CartItem row to serialise with concurrent checkouts.
                # If checkout already consumed this reservation, DoesNotExist is caught below.
                cart_item = CartItem.objects.select_for_update().get(pk=cart_item_id)
                inventory_services.release_reservation(
                    cart_item.variant,
                    quantity,
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
