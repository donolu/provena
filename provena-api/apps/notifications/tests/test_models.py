from apps.notifications.models import Notification, NotificationType


class TestNotificationModel:
    def test_str(self, buyer):
        n = Notification.objects.create(
            recipient=buyer,
            notification_type=NotificationType.GENERAL,
            title="Hello",
            body="World",
        )
        assert "GENERAL" in str(n)
        assert "Hello" in str(n)
        assert "buyer@example.com" in str(n)

    def test_default_is_read_false(self, buyer):
        n = Notification.objects.create(recipient=buyer, title="T", body="B")
        assert n.is_read is False

    def test_data_defaults_to_empty_dict(self, buyer):
        n = Notification.objects.create(recipient=buyer, title="T", body="B")
        assert n.data == {}

    def test_ordering_newest_first(self, buyer):
        n1 = Notification.objects.create(recipient=buyer, title="First", body="B")
        n2 = Notification.objects.create(recipient=buyer, title="Second", body="B")
        ids = list(Notification.objects.filter(recipient=buyer).values_list("id", flat=True))
        assert ids[0] == n2.id
        assert ids[1] == n1.id
