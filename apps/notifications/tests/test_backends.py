from unittest.mock import patch

from apps.notifications.backends import (
    EmailBackend,
    InAppBackend,
    SlackBackend,
    TelegramBackend,
    WhatsAppBackend,
)
from apps.notifications.models import Notification


class TestInAppBackend:
    def test_creates_notification(self, buyer):
        InAppBackend().send(buyer, "Title", "Body", {"notification_type": "GENERAL"})
        assert Notification.objects.filter(recipient=buyer, title="Title").exists()

    def test_uses_notification_type_from_data(self, buyer):
        InAppBackend().send(buyer, "T", "B", {"notification_type": "LOW_STOCK"})
        n = Notification.objects.get(recipient=buyer)
        assert n.notification_type == "LOW_STOCK"


class TestEmailBackend:
    def test_sends_email(self, buyer):
        with patch("apps.notifications.backends.send_mail") as mock_send:
            EmailBackend().send(buyer, "Subject", "Message body", {})
            mock_send.assert_called_once()
            _, kwargs = mock_send.call_args
            recipients = kwargs.get("recipient_list") or mock_send.call_args[0][3]
            assert buyer.email in recipients

    def test_smtp_failure_is_caught(self, buyer):
        with patch("apps.notifications.backends.send_mail", side_effect=OSError("SMTP error")):
            EmailBackend().send(buyer, "Subject", "Msg", {})  # must not raise


class TestStubBackends:
    def test_slack_does_not_raise(self, buyer):
        SlackBackend().send(buyer, "T", "B", {})

    def test_telegram_does_not_raise(self, buyer):
        TelegramBackend().send(buyer, "T", "B", {})

    def test_whatsapp_does_not_raise(self, buyer):
        WhatsAppBackend().send(buyer, "T", "B", {})
