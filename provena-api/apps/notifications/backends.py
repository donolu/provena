import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class NotificationBackend:
    def send(self, recipient, title: str, body: str, data: dict) -> None:
        raise NotImplementedError


class InAppBackend(NotificationBackend):
    def send(self, recipient, title: str, body: str, data: dict) -> None:
        from .models import Notification

        notification_type = data.get("notification_type", "GENERAL")
        Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data,
        )


class EmailBackend(NotificationBackend):
    def send(self, recipient, title: str, body: str, data: dict) -> None:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@provena.io")
        try:
            send_mail(
                subject=title,
                message=body,
                from_email=from_email,
                recipient_list=[recipient.email],
                fail_silently=False,
            )
        except Exception:
            logger.exception("EmailBackend failed for recipient %s", recipient.email)


class SlackBackend(NotificationBackend):
    def send(self, recipient, title: str, body: str, data: dict) -> None:
        logger.info("SlackBackend: %s | %s (to %s)", title, body, recipient.email)


class TelegramBackend(NotificationBackend):
    def send(self, recipient, title: str, body: str, data: dict) -> None:
        logger.info("TelegramBackend: %s | %s (to %s)", title, body, recipient.email)


class WhatsAppBackend(NotificationBackend):
    def send(self, recipient, title: str, body: str, data: dict) -> None:
        logger.info("WhatsAppBackend: %s | %s (to %s)", title, body, recipient.email)
