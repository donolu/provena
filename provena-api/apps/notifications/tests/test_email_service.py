"""Tests for email_service.py covering send_welcome, send_password_reset,
send_delivery_confirmation, the tracking-number path of send_shipping_update,
and the _send error/success paths."""

from unittest.mock import MagicMock, patch

from apps.notifications.email_service import (
    _send,
    send_delivery_confirmation,
    send_password_reset,
    send_shipping_update,
    send_welcome,
)
from apps.notifications.models import NotificationPreference

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _mock_user(email="user@example.com", first_name=""):
    u = MagicMock()
    u.email = email
    u.first_name = first_name
    return u


def _mock_sub_order(buyer, tracking_number=None):
    supplier = MagicMock()
    supplier.user = MagicMock()
    supplier.user.email = "supplier@example.com"
    supplier.business_name = "Test Farm"

    order = MagicMock()
    order.buyer = buyer
    order.reference = "ORD-TEST"
    order.shipping_name = "A B"
    order.shipping_line1 = "1 Street"
    order.shipping_line2 = ""
    order.shipping_city = "London"
    order.shipping_postcode = "SW1A 1AA"

    sub = MagicMock()
    sub.order = order
    sub.supplier = supplier
    sub.tracking_number = tracking_number
    sub.items.select_related.return_value.all.return_value = []
    return sub


# ---------------------------------------------------------------------------
# send_welcome
# ---------------------------------------------------------------------------


class TestSendWelcome:
    def test_sends_email(self):
        user = _mock_user(email="new@example.com", first_name="Alice")
        with patch("apps.notifications.email_service._send") as mock_send:
            send_welcome(user)
        mock_send.assert_called_once()
        assert "Welcome" in mock_send.call_args.kwargs["subject"]

    def test_uses_first_name_in_body(self):
        user = _mock_user(email="alice@example.com", first_name="Alice")
        with patch("apps.notifications.email_service._send") as mock_send:
            send_welcome(user)
        assert "Alice" in mock_send.call_args.kwargs["plain"]

    def test_falls_back_to_email_prefix_when_no_first_name(self):
        user = _mock_user(email="bob.smith@example.com", first_name="")
        with patch("apps.notifications.email_service._send") as mock_send:
            send_welcome(user)
        mock_send.assert_called_once()
        assert "bob.smith" in mock_send.call_args.kwargs["plain"]

    def test_catalogue_link_in_body(self):
        user = _mock_user()
        with patch("apps.notifications.email_service._send") as mock_send:
            send_welcome(user)
        assert "/catalogue" in mock_send.call_args.kwargs["plain"]


# ---------------------------------------------------------------------------
# send_password_reset
# ---------------------------------------------------------------------------


class TestSendPasswordReset:
    RESET_URL = "https://example.com/reset/abc123"

    def test_sends_email(self):
        user = _mock_user(first_name="Charlie")
        with patch("apps.notifications.email_service._send") as mock_send:
            send_password_reset(user, self.RESET_URL)
        mock_send.assert_called_once()
        assert "Reset" in mock_send.call_args.kwargs["subject"]

    def test_reset_url_in_plain(self):
        user = _mock_user()
        with patch("apps.notifications.email_service._send") as mock_send:
            send_password_reset(user, self.RESET_URL)
        assert self.RESET_URL in mock_send.call_args.kwargs["plain"]

    def test_reset_url_in_html(self):
        user = _mock_user()
        with patch("apps.notifications.email_service._send") as mock_send:
            send_password_reset(user, self.RESET_URL)
        assert self.RESET_URL in mock_send.call_args.kwargs["html"]

    def test_falls_back_to_there_when_no_first_name(self):
        user = _mock_user(first_name="")
        with patch("apps.notifications.email_service._send") as mock_send:
            send_password_reset(user, self.RESET_URL)
        assert "there" in mock_send.call_args.kwargs["html"]


# ---------------------------------------------------------------------------
# send_shipping_update — tracking number branch
# ---------------------------------------------------------------------------


class TestSendShippingUpdateWithTracking:
    def test_tracking_number_in_plain(self, buyer):
        NotificationPreference.objects.create(user=buyer, email_order_dispatched=True)
        sub = _mock_sub_order(buyer, tracking_number="TRK-9999")
        with patch("apps.notifications.email_service._send") as mock_send:
            send_shipping_update(sub)
        mock_send.assert_called_once()
        assert "TRK-9999" in mock_send.call_args.kwargs["plain"]

    def test_tracking_number_in_html(self, buyer):
        NotificationPreference.objects.create(user=buyer, email_order_dispatched=True)
        sub = _mock_sub_order(buyer, tracking_number="TRK-9999")
        with patch("apps.notifications.email_service._send") as mock_send:
            send_shipping_update(sub)
        assert "TRK-9999" in mock_send.call_args.kwargs["html"]

    def test_no_tracking_block_when_absent(self, buyer):
        NotificationPreference.objects.create(user=buyer, email_order_dispatched=True)
        sub = _mock_sub_order(buyer, tracking_number=None)
        with patch("apps.notifications.email_service._send") as mock_send:
            send_shipping_update(sub)
        mock_send.assert_called_once()
        assert "Tracking" not in mock_send.call_args.kwargs["plain"]


# ---------------------------------------------------------------------------
# send_delivery_confirmation
# ---------------------------------------------------------------------------


class TestSendDeliveryConfirmation:
    def test_sends_when_opted_in(self, buyer):
        NotificationPreference.objects.create(user=buyer, email_order_dispatched=True)
        sub = _mock_sub_order(buyer)
        with patch("apps.notifications.email_service._send") as mock_send:
            send_delivery_confirmation(sub)
        mock_send.assert_called_once()

    def test_skips_when_opted_out(self, buyer):
        NotificationPreference.objects.create(user=buyer, email_order_dispatched=False)
        sub = _mock_sub_order(buyer)
        with patch("apps.notifications.email_service._send") as mock_send:
            send_delivery_confirmation(sub)
        mock_send.assert_not_called()

    def test_order_reference_in_subject(self, buyer):
        NotificationPreference.objects.create(user=buyer, email_order_dispatched=True)
        sub = _mock_sub_order(buyer)
        sub.order.reference = "ORD-DELIVER-001"
        with patch("apps.notifications.email_service._send") as mock_send:
            send_delivery_confirmation(sub)
        assert "ORD-DELIVER-001" in mock_send.call_args.kwargs["subject"]

    def test_sends_when_no_pref_row_exists(self, buyer):
        sub = _mock_sub_order(buyer)
        with patch("apps.notifications.email_service._send") as mock_send:
            send_delivery_confirmation(sub)
        mock_send.assert_called_once()


# ---------------------------------------------------------------------------
# _send — internal transport layer
# ---------------------------------------------------------------------------


class TestSendInternal:
    def test_sends_successfully(self):
        with patch("apps.notifications.email_service.EmailMultiAlternatives") as MockMsg:
            _send(subject="Hello", plain="plain", html="<p>html</p>", to=["a@b.com"])
        MockMsg.return_value.send.assert_called_once()

    def test_attaches_html_alternative(self):
        with patch("apps.notifications.email_service.EmailMultiAlternatives") as MockMsg:
            _send(subject="Hello", plain="plain", html="<p>html</p>", to=["a@b.com"])
        MockMsg.return_value.attach_alternative.assert_called_once_with("<p>html</p>", "text/html")

    def test_swallows_smtp_exception(self):
        with patch("apps.notifications.email_service.EmailMultiAlternatives") as MockMsg:
            MockMsg.return_value.send.side_effect = Exception("SMTP error")
            _send(subject="Hello", plain="plain", html="<p>html</p>", to=["a@b.com"])
