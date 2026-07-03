"""Tests for ORD-07: dispute raising with 7-day window, admin mediation."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.orders import services
from apps.orders.models import DisputeStatus, OrderDispute

# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestRaiseDisputeService:
    def test_can_raise_on_dispatched(self, buyer, dispatched_sub_order):
        dispute = services.raise_dispute(dispatched_sub_order, buyer, "Item damaged")
        assert dispute.status == DisputeStatus.OPEN
        assert dispute.reason == "Item damaged"
        assert dispute.raised_by == buyer

    def test_can_raise_on_delivered_within_7_days(self, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        dispute = services.raise_dispute(sub, buyer, "Wrong item")
        assert dispute.status == DisputeStatus.OPEN

    def test_cannot_raise_on_delivered_after_7_days(self, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        sub.delivered_at = timezone.now() - timedelta(days=8)
        sub.save(update_fields=["delivered_at"])
        with pytest.raises(ValueError, match="7 days"):
            services.raise_dispute(sub, buyer, "Too late")

    def test_cannot_raise_on_pending(self, buyer, sub_order):
        with pytest.raises(ValueError, match="dispatched or delivered"):
            services.raise_dispute(sub_order, buyer, "Reason")

    def test_cannot_raise_on_confirmed(self, buyer, sub_order):
        services.confirm_sub_order(sub_order)
        sub_order.refresh_from_db()
        with pytest.raises(ValueError, match="dispatched or delivered"):
            services.raise_dispute(sub_order, buyer, "Reason")

    def test_raise_creates_db_record(self, buyer, dispatched_sub_order):
        services.raise_dispute(dispatched_sub_order, buyer, "Broken seal")
        assert OrderDispute.objects.filter(sub_order=dispatched_sub_order).count() == 1


class TestResolveDisputeService:
    def test_resolve_open_dispute(self, buyer, dispatched_sub_order):
        dispute = services.raise_dispute(dispatched_sub_order, buyer, "Issue")
        resolved = services.resolve_dispute(dispute, "Refund processed")
        assert resolved.status == DisputeStatus.RESOLVED
        assert resolved.resolution == "Refund processed"

    def test_cannot_resolve_already_resolved(self, buyer, dispatched_sub_order):
        dispute = services.raise_dispute(dispatched_sub_order, buyer, "Issue")
        services.resolve_dispute(dispute, "Done")
        with pytest.raises(ValueError, match="open"):
            services.resolve_dispute(dispute, "Again")

    def test_cannot_resolve_rejected_dispute(self, buyer, dispatched_sub_order):
        dispute = services.raise_dispute(dispatched_sub_order, buyer, "Issue")
        services.reject_dispute(dispute, "Not valid")
        with pytest.raises(ValueError, match="open"):
            services.resolve_dispute(dispute, "Too late")


class TestRejectDisputeService:
    def test_reject_open_dispute(self, buyer, dispatched_sub_order):
        dispute = services.raise_dispute(dispatched_sub_order, buyer, "Issue")
        rejected = services.reject_dispute(dispute, "No evidence provided")
        assert rejected.status == DisputeStatus.REJECTED
        assert rejected.resolution == "No evidence provided"

    def test_cannot_reject_already_closed(self, buyer, dispatched_sub_order):
        dispute = services.raise_dispute(dispatched_sub_order, buyer, "Issue")
        services.resolve_dispute(dispute, "Resolved")
        with pytest.raises(ValueError, match="open"):
            services.reject_dispute(dispute, "Cannot")


# ---------------------------------------------------------------------------
# View tests — buyer
# ---------------------------------------------------------------------------


class TestRaiseDisputeView:
    def test_buyer_can_raise_on_dispatched(self, buyer_client, placed_order, dispatched_sub_order):
        response = buyer_client.post(
            f"/api/v1/orders/{placed_order.reference}/sub-orders/{dispatched_sub_order.id}/dispute/",
            {"reason": "Package arrived damaged."},
            format="json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "OPEN"
        assert data["reason"] == "Package arrived damaged."

    def test_buyer_can_raise_on_delivered(self, buyer_client, placed_order, dispatched_sub_order):
        services.deliver_sub_order(dispatched_sub_order)
        dispatched_sub_order.refresh_from_db()
        response = buyer_client.post(
            f"/api/v1/orders/{placed_order.reference}/sub-orders/{dispatched_sub_order.id}/dispute/",
            {"reason": "Wrong item."},
            format="json",
        )
        assert response.status_code == 201

    def test_cannot_raise_after_7_days(self, buyer_client, placed_order, dispatched_sub_order):
        services.deliver_sub_order(dispatched_sub_order)
        dispatched_sub_order.delivered_at = timezone.now() - timedelta(days=8)
        dispatched_sub_order.save(update_fields=["delivered_at"])
        response = buyer_client.post(
            f"/api/v1/orders/{placed_order.reference}/sub-orders/{dispatched_sub_order.id}/dispute/",
            {"reason": "Late claim."},
            format="json",
        )
        assert response.status_code == 400
        assert "7 days" in response.json()["detail"]

    def test_cannot_raise_on_pending_sub_order(self, buyer_client, placed_order, sub_order):
        response = buyer_client.post(
            f"/api/v1/orders/{placed_order.reference}/sub-orders/{sub_order.id}/dispute/",
            {"reason": "Reason"},
            format="json",
        )
        assert response.status_code == 400

    def test_other_buyer_cannot_raise(
        self, api_client, admin_user, placed_order, dispatched_sub_order
    ):
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            f"/api/v1/orders/{placed_order.reference}/sub-orders/{dispatched_sub_order.id}/dispute/",
            {"reason": "Not my order"},
            format="json",
        )
        assert response.status_code == 404

    def test_unauthenticated_cannot_raise(self, client, placed_order, dispatched_sub_order):
        response = client.post(
            f"/api/v1/orders/{placed_order.reference}/sub-orders/{dispatched_sub_order.id}/dispute/",
            {"reason": "Anon"},
            format="json",
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# View tests — admin
# ---------------------------------------------------------------------------


class TestAdminDisputeListView:
    def test_admin_can_list_disputes(self, admin_client, buyer, dispatched_sub_order):
        services.raise_dispute(dispatched_sub_order, buyer, "Broken")
        response = admin_client.get("/api/v1/orders/admin/disputes/")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_filter_by_open(self, admin_client, buyer, dispatched_sub_order):
        dispute = services.raise_dispute(dispatched_sub_order, buyer, "Broken")
        services.resolve_dispute(dispute, "Fixed")
        response = admin_client.get("/api/v1/orders/admin/disputes/?status=OPEN")
        assert response.json() == []
        response2 = admin_client.get("/api/v1/orders/admin/disputes/?status=RESOLVED")
        assert len(response2.json()) == 1

    def test_buyer_cannot_list(self, buyer_client):
        response = buyer_client.get("/api/v1/orders/admin/disputes/")
        assert response.status_code == 403

    def test_unauthenticated_cannot_list(self, client):
        response = client.get("/api/v1/orders/admin/disputes/")
        assert response.status_code == 401


class TestAdminResolveDisputeView:
    def test_admin_can_resolve(self, admin_client, buyer, dispatched_sub_order):
        dispute = services.raise_dispute(dispatched_sub_order, buyer, "Issue")
        response = admin_client.post(
            f"/api/v1/orders/admin/disputes/{dispute.id}/resolve/",
            {"resolution": "Refund issued"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "RESOLVED"
        assert response.json()["resolution"] == "Refund issued"

    def test_cannot_resolve_non_open(self, admin_client, buyer, dispatched_sub_order):
        dispute = services.raise_dispute(dispatched_sub_order, buyer, "Issue")
        services.reject_dispute(dispute, "Invalid")
        response = admin_client.post(
            f"/api/v1/orders/admin/disputes/{dispute.id}/resolve/",
            {"resolution": "Attempt"},
            format="json",
        )
        assert response.status_code == 400

    def test_buyer_cannot_resolve(self, buyer_client, buyer, dispatched_sub_order):
        dispute = services.raise_dispute(dispatched_sub_order, buyer, "Issue")
        response = buyer_client.post(
            f"/api/v1/orders/admin/disputes/{dispute.id}/resolve/",
            {"resolution": "Self-resolve"},
            format="json",
        )
        assert response.status_code == 403


class TestAdminRejectDisputeView:
    def test_admin_can_reject(self, admin_client, buyer, dispatched_sub_order):
        dispute = services.raise_dispute(dispatched_sub_order, buyer, "Weak claim")
        response = admin_client.post(
            f"/api/v1/orders/admin/disputes/{dispute.id}/reject/",
            {"resolution": "Insufficient evidence"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "REJECTED"

    def test_cannot_reject_non_open(self, admin_client, buyer, dispatched_sub_order):
        dispute = services.raise_dispute(dispatched_sub_order, buyer, "Issue")
        services.resolve_dispute(dispute, "Done")
        response = admin_client.post(
            f"/api/v1/orders/admin/disputes/{dispute.id}/reject/",
            {"resolution": "Late"},
            format="json",
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Disputes appear nested in order detail
# ---------------------------------------------------------------------------


class TestDisputesInOrderDetail:
    def test_disputes_nested_in_sub_order(
        self, buyer_client, placed_order, dispatched_sub_order, buyer
    ):
        services.raise_dispute(dispatched_sub_order, buyer, "Test dispute")
        response = buyer_client.get(f"/api/v1/orders/{placed_order.reference}/")
        assert response.status_code == 200
        sub = response.json()["sub_orders"][0]
        assert len(sub["disputes"]) == 1
        assert sub["disputes"][0]["reason"] == "Test dispute"
        assert sub["disputes"][0]["status"] == "OPEN"

    def test_delivered_at_in_sub_order(self, buyer_client, placed_order, dispatched_sub_order):
        services.deliver_sub_order(dispatched_sub_order)
        response = buyer_client.get(f"/api/v1/orders/{placed_order.reference}/")
        sub = response.json()["sub_orders"][0]
        assert sub["delivered_at"] is not None
