import hashlib
import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import DataExportRequest, DataExportStatus
from apps.accounts.tasks import _collect_user_data, generate_data_export, purge_expired_exports

EXPORT_URL = "/api/v1/auth/me/export/"
DOWNLOAD_URL = "/api/v1/auth/me/export/download/"
ADMIN_EXPORTS_URL = "/api/v1/auth/admin/exports/"


# ---------------------------------------------------------------------------
# Request endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDataExportRequestView:
    def test_unauthenticated_rejected(self, api_client):
        res = api_client.post(EXPORT_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_queues_export_and_returns_202(self, buyer_client, buyer):
        with patch("apps.accounts.views.generate_data_export.delay") as mock_delay:
            res = buyer_client.post(EXPORT_URL)
        assert res.status_code == status.HTTP_202_ACCEPTED
        assert DataExportRequest.objects.filter(user=buyer).count() == 1
        mock_delay.assert_called_once()

    def test_rate_limit_blocks_second_request(self, buyer_client, buyer):
        with patch("apps.accounts.views.generate_data_export.delay"):
            buyer_client.post(EXPORT_URL)
            res = buyer_client.post(EXPORT_URL)
        assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_rate_limit_allows_after_30_days(self, buyer_client, buyer):
        old_export = DataExportRequest.objects.create(user=buyer)
        old_export.requested_at = timezone.now() - timedelta(days=31)
        old_export.save(update_fields=["requested_at"])

        with patch("apps.accounts.views.generate_data_export.delay") as mock_delay:
            res = buyer_client.post(EXPORT_URL)
        assert res.status_code == status.HTTP_202_ACCEPTED
        mock_delay.assert_called_once()


# ---------------------------------------------------------------------------
# Download endpoint
# ---------------------------------------------------------------------------


def _make_completed_export(user, expired=False):
    token_raw = "test-token-abc123"
    token_hash = hashlib.sha256(token_raw.encode()).hexdigest()
    expires_at = (
        timezone.now() - timedelta(hours=1) if expired else timezone.now() + timedelta(hours=24)
    )
    export = DataExportRequest.objects.create(
        user=user,
        status=DataExportStatus.COMPLETED,
        token_hash=token_hash,
        payload={"profile": {"email": user.email}, "orders": []},
        expires_at=expires_at,
        completed_at=timezone.now(),
    )
    return export, token_raw


@pytest.mark.django_db
class TestDataExportDownloadView:
    def test_valid_token_returns_json_file(self, api_client, buyer):
        _export, token = _make_completed_export(buyer)
        res = api_client.get(DOWNLOAD_URL, {"token": token})
        assert res.status_code == status.HTTP_200_OK
        assert res["Content-Disposition"] == 'attachment; filename="provena-data-export.json"'
        assert res["Content-Type"] == "application/json"

    def test_token_and_payload_cleared_after_download(self, api_client, buyer):
        export, token = _make_completed_export(buyer)
        api_client.get(DOWNLOAD_URL, {"token": token})
        export.refresh_from_db()
        assert export.token_hash == ""
        assert export.payload is None

    def test_second_download_with_same_token_fails(self, api_client, buyer):
        _export, token = _make_completed_export(buyer)
        api_client.get(DOWNLOAD_URL, {"token": token})
        res = api_client.get(DOWNLOAD_URL, {"token": token})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_expired_token_rejected(self, api_client, buyer):
        _, token = _make_completed_export(buyer, expired=True)
        res = api_client.get(DOWNLOAD_URL, {"token": token})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_token_rejected(self, api_client):
        res = api_client.get(DOWNLOAD_URL)
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_wrong_token_rejected(self, api_client, buyer):
        _make_completed_export(buyer)
        res = api_client.get(DOWNLOAD_URL, {"token": "wrong-token"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_payload_returned_is_correct(self, api_client, buyer):
        _export, token = _make_completed_export(buyer)
        res = api_client.get(DOWNLOAD_URL, {"token": token})
        data = json.loads(res.content)
        assert data["profile"]["email"] == buyer.email


# ---------------------------------------------------------------------------
# Admin list endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAdminDataExportListView:
    def test_admin_can_list_exports(self, admin_client, buyer):
        DataExportRequest.objects.create(user=buyer)
        res = admin_client.get(ADMIN_EXPORTS_URL)
        assert res.status_code == status.HTTP_200_OK
        assert res.data["count"] == 1
        assert res.data["results"][0]["user_email"] == buyer.email

    def test_buyer_cannot_access(self, buyer_client):
        res = buyer_client.get(ADMIN_EXPORTS_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_rejected(self, api_client):
        res = api_client.get(ADMIN_EXPORTS_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGenerateDataExportTask:
    def test_task_completes_and_sends_email(self, buyer):
        export = DataExportRequest.objects.create(user=buyer)
        with patch("apps.accounts.tasks.send_data_export_ready_email") as mock_email:
            generate_data_export(str(export.id))

        export.refresh_from_db()
        assert export.status == DataExportStatus.COMPLETED
        assert export.token_hash != ""
        assert export.payload is not None
        assert export.expires_at is not None
        assert export.completed_at is not None
        mock_email.assert_called_once()

    def test_task_marks_failed_on_error(self, buyer):
        export = DataExportRequest.objects.create(user=buyer)
        with patch("apps.accounts.tasks._collect_user_data", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError):
                generate_data_export(str(export.id))

        export.refresh_from_db()
        assert export.status == DataExportStatus.FAILED

    def test_task_noop_for_missing_export(self):
        generate_data_export("00000000-0000-0000-0000-000000000000")

    def test_collect_user_data_returns_expected_keys(self, buyer):
        payload = _collect_user_data(buyer)
        assert set(payload.keys()) == {
            "export_generated_at",
            "profile",
            "addresses",
            "orders",
            "wishlist",
            "reviews",
            "notifications",
            "notification_preferences",
            "disputes",
        }
        assert payload["profile"]["email"] == buyer.email

    def test_collect_user_data_buyer_has_no_supplier_key(self, buyer):
        payload = _collect_user_data(buyer)
        assert "supplier" not in payload


# ---------------------------------------------------------------------------
# Purge task
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPurgeExpiredExports:
    def test_clears_payload_and_token_for_expired_exports(self, buyer):
        expired = DataExportRequest.objects.create(
            user=buyer,
            status=DataExportStatus.COMPLETED,
            token_hash="abc",
            payload={"profile": {}},
            expires_at=timezone.now() - timedelta(hours=1),
            completed_at=timezone.now() - timedelta(hours=2),
        )
        purge_expired_exports()
        expired.refresh_from_db()
        assert expired.payload is None
        assert expired.token_hash == ""

    def test_does_not_touch_valid_exports(self, buyer):
        valid = DataExportRequest.objects.create(
            user=buyer,
            status=DataExportStatus.COMPLETED,
            token_hash="abc",
            payload={"profile": {}},
            expires_at=timezone.now() + timedelta(hours=23),
            completed_at=timezone.now(),
        )
        purge_expired_exports()
        valid.refresh_from_db()
        assert valid.payload is not None
