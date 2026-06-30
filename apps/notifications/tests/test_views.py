from rest_framework.test import APIClient

from apps.notifications.models import Notification


class TestNotificationListView:
    def test_list_own_notifications(self, buyer_client, buyer):
        Notification.objects.create(recipient=buyer, title="T1", body="B1")
        Notification.objects.create(recipient=buyer, title="T2", body="B2")
        response = buyer_client.get("/api/v1/notifications/")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_filter_unread(self, buyer_client, buyer):
        Notification.objects.create(recipient=buyer, title="Read", body="B", is_read=True)
        Notification.objects.create(recipient=buyer, title="Unread", body="B", is_read=False)
        response = buyer_client.get("/api/v1/notifications/?unread=true")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["title"] == "Unread"

    def test_does_not_show_other_users_notifications(self, buyer_client, staff_user):
        Notification.objects.create(recipient=staff_user, title="T", body="B")
        response = buyer_client.get("/api/v1/notifications/")
        assert response.json() == []

    def test_unauthenticated(self):
        response = APIClient().get("/api/v1/notifications/")
        assert response.status_code == 401


class TestNotificationMarkReadView:
    def test_marks_read(self, buyer_client, buyer):
        n = Notification.objects.create(recipient=buyer, title="T", body="B")
        response = buyer_client.post(f"/api/v1/notifications/{n.id}/read/")
        assert response.status_code == 200
        assert response.json()["is_read"] is True

    def test_other_user_gets_404(self, staff_client, buyer):
        n = Notification.objects.create(recipient=buyer, title="T", body="B")
        response = staff_client.post(f"/api/v1/notifications/{n.id}/read/")
        assert response.status_code == 404


class TestNotificationMarkAllReadView:
    def test_marks_all_read(self, buyer_client, buyer):
        Notification.objects.create(recipient=buyer, title="A", body="B")
        Notification.objects.create(recipient=buyer, title="C", body="D")
        response = buyer_client.post("/api/v1/notifications/read-all/")
        assert response.status_code == 200
        assert response.json()["marked_read"] == 2
        assert Notification.objects.filter(recipient=buyer, is_read=False).count() == 0

    def test_unauthenticated(self):
        response = APIClient().post("/api/v1/notifications/read-all/")
        assert response.status_code == 401


class TestNotificationDeleteView:
    def test_deletes_own(self, buyer_client, buyer):
        n = Notification.objects.create(recipient=buyer, title="T", body="B")
        response = buyer_client.delete(f"/api/v1/notifications/{n.id}/")
        assert response.status_code == 204
        assert Notification.objects.filter(id=n.id).count() == 0

    def test_other_user_gets_404(self, staff_client, buyer):
        n = Notification.objects.create(recipient=buyer, title="T", body="B")
        response = staff_client.delete(f"/api/v1/notifications/{n.id}/")
        assert response.status_code == 404
