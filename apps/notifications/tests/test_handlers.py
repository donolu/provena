from unittest.mock import MagicMock, patch

from apps.notifications.handlers import handle_low_stock_alert
from apps.notifications.models import NotificationType


class TestHandleLowStockAlert:
    def _make_variant(self, sku="CARR-1KG"):
        v = MagicMock()
        v.id = "00000000-0000-0000-0000-000000000001"
        v.sku = sku
        v.name = "Carrots 1kg"
        return v

    def _make_stock_level(self, threshold=5):
        sl = MagicMock()
        sl.low_stock_threshold = threshold
        return sl

    def test_notifies_staff_user(self, staff_user):
        with patch("apps.notifications.services.notify") as mock_notify:
            handle_low_stock_alert(
                sender=None,
                variant=self._make_variant(),
                stock_level=self._make_stock_level(),
                quantity_available=2,
            )
            assert mock_notify.call_count == 1
            call_kwargs = mock_notify.call_args.kwargs
            assert call_kwargs["recipient"] == staff_user
            assert "CARR-1KG" in call_kwargs["title"]
            assert call_kwargs["notification_type"] == NotificationType.LOW_STOCK

    def test_does_not_notify_non_staff(self, buyer, staff_user):
        with patch("apps.notifications.services.notify") as mock_notify:
            handle_low_stock_alert(
                sender=None,
                variant=self._make_variant(),
                stock_level=self._make_stock_level(),
                quantity_available=1,
            )
            recipients = [c.kwargs["recipient"] for c in mock_notify.call_args_list]
            assert staff_user in recipients
            assert buyer not in recipients

    def test_no_staff_means_no_calls(self, buyer):
        with patch("apps.notifications.services.notify") as mock_notify:
            handle_low_stock_alert(
                sender=None,
                variant=self._make_variant(),
                stock_level=self._make_stock_level(),
                quantity_available=0,
            )
            mock_notify.assert_not_called()

    def test_notify_failure_does_not_propagate(self, staff_user):
        with patch("apps.notifications.services.notify", side_effect=RuntimeError("fail")):
            handle_low_stock_alert(
                sender=None,
                variant=self._make_variant(),
                stock_level=self._make_stock_level(),
                quantity_available=1,
            )  # must not raise
