import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.module_loading import import_string

from .models import Notification, NotificationType

logger = logging.getLogger(__name__)

_DEFAULT_BACKENDS = [
    "apps.notifications.backends.InAppBackend",
    "apps.notifications.backends.EmailBackend",
]


def notify(
    recipient,
    title: str,
    body: str,
    notification_type: str = NotificationType.GENERAL,
    data: dict | None = None,
) -> None:
    payload = dict(data or {})
    payload.setdefault("notification_type", notification_type)
    backend_paths = getattr(settings, "NOTIFICATION_BACKENDS", _DEFAULT_BACKENDS)
    for path in backend_paths:
        backend = import_string(path)()
        try:
            backend.send(recipient=recipient, title=title, body=body, data=payload)
        except Exception:
            logger.exception("Notification backend %s failed", path)


def mark_as_read(user, notification_id) -> Notification:
    notification = get_object_or_404(Notification, pk=notification_id, recipient=user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return notification


def mark_all_as_read(user) -> int:
    return Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)


def delete_notification(user, notification_id) -> None:
    notification = get_object_or_404(Notification, pk=notification_id, recipient=user)
    notification.delete()
