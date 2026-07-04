from unittest.mock import MagicMock, patch

import pytest
from django.http import Http404

from apps.notifications import services
from apps.notifications.models import Notification, NotificationType


class TestNotify:
    def test_dispatches_to_backends(self, buyer):
        with patch("apps.notifications.services.import_string") as mock_import:
            backend = MagicMock()
            mock_import.return_value = MagicMock(return_value=backend)
            services.notify(buyer, "Title", "Body", NotificationType.GENERAL)
            assert backend.send.call_count >= 1

    def test_notification_type_added_to_payload(self, buyer):
        captured = {}
        with patch("apps.notifications.services.import_string") as mock_import:

            def capture(**kwargs):
                captured.update(kwargs)

            backend = MagicMock()
            backend.send.side_effect = capture
            mock_import.return_value = MagicMock(return_value=backend)
            services.notify(buyer, "T", "B", NotificationType.LOW_STOCK)
            assert captured["data"]["notification_type"] == NotificationType.LOW_STOCK

    def test_backend_exception_is_caught(self, buyer):
        with patch("apps.notifications.services.import_string") as mock_import:
            backend = MagicMock()
            backend.send.side_effect = RuntimeError("fail")
            mock_import.return_value = MagicMock(return_value=backend)
            services.notify(buyer, "T", "B")  # must not raise


class TestMarkAsRead:
    def test_marks_notification_read(self, buyer):
        n = Notification.objects.create(recipient=buyer, title="T", body="B")
        result = services.mark_as_read(buyer, n.id)
        assert result.is_read is True
        n.refresh_from_db()
        assert n.is_read is True

    def test_idempotent_if_already_read(self, buyer):
        n = Notification.objects.create(recipient=buyer, title="T", body="B", is_read=True)
        result = services.mark_as_read(buyer, n.id)
        assert result.is_read is True

    def test_raises_404_for_other_user(self, buyer, staff_user):
        n = Notification.objects.create(recipient=buyer, title="T", body="B")
        with pytest.raises(Http404):
            services.mark_as_read(staff_user, n.id)


class TestMarkAllAsRead:
    def test_marks_all_unread(self, buyer):
        Notification.objects.create(recipient=buyer, title="A", body="B")
        Notification.objects.create(recipient=buyer, title="C", body="D")
        count = services.mark_all_as_read(buyer)
        assert count == 2
        assert Notification.objects.filter(recipient=buyer, is_read=False).count() == 0

    def test_skips_already_read(self, buyer):
        Notification.objects.create(recipient=buyer, title="A", body="B", is_read=True)
        Notification.objects.create(recipient=buyer, title="C", body="D")
        count = services.mark_all_as_read(buyer)
        assert count == 1

    def test_does_not_touch_other_user(self, buyer, staff_user):
        Notification.objects.create(recipient=staff_user, title="T", body="B")
        services.mark_all_as_read(buyer)
        assert Notification.objects.filter(recipient=staff_user, is_read=False).count() == 1


class TestDeleteNotification:
    def test_deletes_own_notification(self, buyer):
        n = Notification.objects.create(recipient=buyer, title="T", body="B")
        services.delete_notification(buyer, n.id)
        assert Notification.objects.filter(id=n.id).count() == 0

    def test_raises_404_for_other_user(self, buyer, staff_user):
        n = Notification.objects.create(recipient=buyer, title="T", body="B")
        with pytest.raises(Http404):
            services.delete_notification(staff_user, n.id)
