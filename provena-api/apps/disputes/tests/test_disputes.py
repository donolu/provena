"""Tests for the dispute resolution feature (Issue #36)."""

from datetime import timedelta

from apps.disputes import services
from apps.disputes.models import (
    Dispute,
    DisputeEvent,
    DisputeEventType,
    DisputeStatus,
    DisputeType,
)

BASE = "/api/v1/disputes/"


# ---------------------------------------------------------------------------
# Service layer
# ---------------------------------------------------------------------------


class TestOpenDisputeService:
    def test_creates_dispute_and_event(self, buyer, supplier, dispatched_sub_order):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Package arrived broken.",
            resolution_requested="FULL_REFUND",
        )
        assert dispute.status == DisputeStatus.OPEN
        assert dispute.payout_held is True
        assert Dispute.objects.filter(pk=dispute.pk).exists()
        event = DisputeEvent.objects.get(dispute=dispute)
        assert event.event_type == DisputeEventType.OPENED

    def test_deadline_uses_category_window(self, buyer, supplier, dispatched_sub_order, category):
        category.dispute_window_days = 5
        category.save(update_fields=["dispute_window_days"])
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Wrong item.",
            resolution_requested="REPLACEMENT",
        )
        expected = dispatched_sub_order.order.created_at + timedelta(days=5)
        diff = abs((dispute.response_deadline - expected).total_seconds())
        assert diff < 2

    def test_fixed_window_for_not_received(self, buyer, supplier, dispatched_sub_order):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.NOT_RECEIVED,
            description="Never arrived.",
            resolution_requested="FULL_REFUND",
        )
        expected = dispatched_sub_order.order.created_at + timedelta(days=14)
        diff = abs((dispute.response_deadline - expected).total_seconds())
        assert diff < 2


class TestRespondDisputeService:
    def test_status_changes_to_respondent_replied(self, buyer, supplier, dispatched_sub_order):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Broken.",
            resolution_requested="FULL_REFUND",
        )
        services.respond_to_dispute(dispute, supplier.user, "Goods were fine when dispatched.")
        dispute.refresh_from_db()
        assert dispute.status == DisputeStatus.RESPONDENT_REPLIED
        events = list(DisputeEvent.objects.filter(dispute=dispute).order_by("created_at"))
        assert events[-1].event_type == DisputeEventType.RESPONDED


class TestResolveDisputeService:
    def test_resolve_releases_hold_for_rejected_outcome(
        self, buyer, supplier, admin_user, dispatched_sub_order
    ):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Broken.",
            resolution_requested="FULL_REFUND",
        )
        dispute.status = DisputeStatus.ESCALATED
        dispute.save(update_fields=["status"])
        services.resolve_dispute(
            dispute, admin_user, "REJECTED", None, "Supplier evidence accepted."
        )
        dispute.refresh_from_db()
        assert dispute.payout_held is False
        assert dispute.outcome == "REJECTED"

    def test_resolve_keeps_hold_for_refund_outcome(
        self, buyer, supplier, admin_user, dispatched_sub_order
    ):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Broken.",
            resolution_requested="FULL_REFUND",
        )
        dispute.status = DisputeStatus.ESCALATED
        dispute.save(update_fields=["status"])
        services.resolve_dispute(dispute, admin_user, "FULL_REFUND", None, "Refund approved.")
        dispute.refresh_from_db()
        assert dispute.payout_held is True


class TestTriggerRefundService:
    def test_creates_refund_record(self, buyer, supplier, admin_user, dispatched_sub_order):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Broken.",
            resolution_requested="FULL_REFUND",
        )
        dispute.status = DisputeStatus.RESOLVED
        dispute.outcome = "FULL_REFUND"
        dispute.save(update_fields=["status", "outcome"])
        refund = services.trigger_refund(dispute, admin_user, "re_stripe123", 399)
        assert refund.stripe_refund_id == "re_stripe123"
        assert refund.amount_pence == 399


# ---------------------------------------------------------------------------
# API views
# ---------------------------------------------------------------------------


class TestOpenDisputeView:
    def test_buyer_can_open_dispute(self, buyer_client, dispatched_sub_order):
        res = buyer_client.post(
            BASE,
            {
                "sub_order_id": str(dispatched_sub_order.id),
                "dispute_type": "DAMAGED",
                "description": "The packaging was completely crushed on arrival.",
                "resolution_requested": "FULL_REFUND",
            },
            format="json",
        )
        assert res.status_code == 201
        assert res.json()["status"] == "OPEN"

    def test_supplier_can_open_counter_dispute(self, supplier_client, dispatched_sub_order):
        res = supplier_client.post(
            BASE,
            {
                "sub_order_id": str(dispatched_sub_order.id),
                "dispute_type": "FALSE_CLAIM",
                "description": "We have photographic evidence goods were delivered in perfect condition.",
                "resolution_requested": "NO_ACTION",
            },
            format="json",
        )
        assert res.status_code == 201

    def test_buyer_cannot_open_supplier_only_type(self, buyer_client, dispatched_sub_order):
        res = buyer_client.post(
            BASE,
            {
                "sub_order_id": str(dispatched_sub_order.id),
                "dispute_type": "FALSE_CLAIM",
                "description": "I want to raise a false claim dispute.",
                "resolution_requested": "NO_ACTION",
            },
            format="json",
        )
        assert res.status_code == 403

    def test_description_too_short_rejected(self, buyer_client, dispatched_sub_order):
        res = buyer_client.post(
            BASE,
            {
                "sub_order_id": str(dispatched_sub_order.id),
                "dispute_type": "DAMAGED",
                "description": "Short",
                "resolution_requested": "FULL_REFUND",
            },
            format="json",
        )
        assert res.status_code == 400

    def test_non_party_cannot_open(self, admin_client, dispatched_sub_order):
        res = admin_client.post(
            BASE,
            {
                "sub_order_id": str(dispatched_sub_order.id),
                "dispute_type": "DAMAGED",
                "description": "Admin trying to open a dispute on someone else's sub-order.",
                "resolution_requested": "FULL_REFUND",
            },
            format="json",
        )
        assert res.status_code == 403

    def test_unauthenticated_returns_401(self, client, dispatched_sub_order):
        res = client.post(
            BASE,
            {
                "sub_order_id": str(dispatched_sub_order.id),
                "dispute_type": "DAMAGED",
                "description": "Trying without auth.",
                "resolution_requested": "FULL_REFUND",
            },
            content_type="application/json",
        )
        assert res.status_code == 401


class TestDisputeListView:
    def test_buyer_sees_own_disputes(self, buyer_client, buyer, supplier, dispatched_sub_order):
        services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Item broken.",
            resolution_requested="FULL_REFUND",
        )
        res = buyer_client.get(BASE)
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_unrelated_user_sees_empty_list(self, admin_client):
        res = admin_client.get(BASE)
        assert res.status_code == 200
        assert res.json() == []


class TestDisputeDetailView:
    def test_party_can_view_detail(self, buyer_client, buyer, supplier, dispatched_sub_order):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Item arrived broken.",
            resolution_requested="FULL_REFUND",
        )
        res = buyer_client.get(f"{BASE}{dispute.id}/")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "OPEN"
        assert len(data["events"]) == 1

    def test_non_party_cannot_view(self, admin_client, buyer, supplier, dispatched_sub_order):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Item arrived broken.",
            resolution_requested="FULL_REFUND",
        )
        res = admin_client.get(f"{BASE}{dispute.id}/")
        assert res.status_code == 403


class TestRespondView:
    def test_respondent_can_reply(self, supplier_client, buyer, supplier, dispatched_sub_order):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Item arrived broken.",
            resolution_requested="FULL_REFUND",
        )
        res = supplier_client.post(
            f"{BASE}{dispute.id}/respond/",
            {
                "body": "We packed the item carefully and have photographic evidence of its condition."
            },
            format="json",
        )
        assert res.status_code == 200
        assert res.json()["status"] == "RESPONDENT_REPLIED"

    def test_opener_cannot_use_respond_endpoint(
        self, buyer_client, buyer, supplier, dispatched_sub_order
    ):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Item arrived broken.",
            resolution_requested="FULL_REFUND",
        )
        res = buyer_client.post(
            f"{BASE}{dispute.id}/respond/",
            {"body": "I am trying to respond to my own dispute which should not be allowed."},
            format="json",
        )
        assert res.status_code == 403


class TestEscalateView:
    def test_buyer_can_escalate(self, buyer_client, buyer, supplier, dispatched_sub_order):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Item arrived broken.",
            resolution_requested="FULL_REFUND",
        )
        res = buyer_client.post(
            f"{BASE}{dispute.id}/escalate/",
            {"body": "No satisfactory response received."},
            format="json",
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ESCALATED"


class TestResolveView:
    def test_admin_can_resolve(
        self, admin_client, buyer, supplier, admin_user, dispatched_sub_order
    ):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Item arrived broken.",
            resolution_requested="FULL_REFUND",
        )
        dispute.status = DisputeStatus.ESCALATED
        dispute.save(update_fields=["status"])
        res = admin_client.post(
            f"{BASE}{dispute.id}/resolve/",
            {"outcome": "FULL_REFUND", "outcome_notes": "Evidence reviewed, refund approved."},
            format="json",
        )
        assert res.status_code == 200
        assert res.json()["outcome"] == "FULL_REFUND"

    def test_non_admin_cannot_resolve(self, buyer_client, buyer, supplier, dispatched_sub_order):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Item arrived broken.",
            resolution_requested="FULL_REFUND",
        )
        dispute.status = DisputeStatus.ESCALATED
        dispute.save(update_fields=["status"])
        res = buyer_client.post(
            f"{BASE}{dispute.id}/resolve/",
            {"outcome": "FULL_REFUND", "outcome_notes": "Self-resolving."},
            format="json",
        )
        assert res.status_code == 403

    def test_partial_refund_requires_amount(
        self, admin_client, buyer, supplier, dispatched_sub_order
    ):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Partially damaged goods.",
            resolution_requested="PARTIAL_REFUND",
        )
        dispute.status = DisputeStatus.ESCALATED
        dispute.save(update_fields=["status"])
        res = admin_client.post(
            f"{BASE}{dispute.id}/resolve/",
            {"outcome": "PARTIAL_REFUND"},
            format="json",
        )
        assert res.status_code == 400

    def test_cannot_resolve_open_dispute(self, admin_client, buyer, supplier, dispatched_sub_order):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Item arrived broken.",
            resolution_requested="FULL_REFUND",
        )
        res = admin_client.post(
            f"{BASE}{dispute.id}/resolve/",
            {"outcome": "FULL_REFUND", "outcome_notes": "Skipping escalation."},
            format="json",
        )
        assert res.status_code == 409


class TestCloseView:
    def test_opener_can_close(self, buyer_client, buyer, supplier, dispatched_sub_order):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Issue resolved informally.",
            resolution_requested="FULL_REFUND",
        )
        res = buyer_client.post(
            f"{BASE}{dispute.id}/close/",
            {"body": "Supplier sent a replacement, withdrawing."},
            format="json",
        )
        assert res.status_code == 200
        assert res.json()["status"] == "CLOSED"
        dispute.refresh_from_db()
        assert dispute.payout_held is False

    def test_respondent_cannot_close(self, supplier_client, buyer, supplier, dispatched_sub_order):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Item broken.",
            resolution_requested="FULL_REFUND",
        )
        res = supplier_client.post(
            f"{BASE}{dispute.id}/close/",
            {},
            format="json",
        )
        assert res.status_code == 403


class TestAdminListView:
    def test_admin_sees_all_disputes(self, admin_client, buyer, supplier, dispatched_sub_order):
        services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Broken item.",
            resolution_requested="FULL_REFUND",
        )
        res = admin_client.get(f"{BASE}admin/")
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_non_admin_cannot_access(self, buyer_client):
        res = buyer_client.get(f"{BASE}admin/")
        assert res.status_code == 403

    def test_filter_by_status(self, admin_client, buyer, supplier, dispatched_sub_order):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Broken item.",
            resolution_requested="FULL_REFUND",
        )
        dispute.status = DisputeStatus.ESCALATED
        dispute.save(update_fields=["status"])
        res = admin_client.get(f"{BASE}admin/?status=OPEN")
        assert res.json() == []
        res2 = admin_client.get(f"{BASE}admin/?status=ESCALATED")
        assert len(res2.json()) == 1


class TestAdminRefundView:
    def test_admin_can_trigger_refund(self, admin_client, buyer, supplier, dispatched_sub_order):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Broken item.",
            resolution_requested="FULL_REFUND",
        )
        dispute.status = DisputeStatus.RESOLVED
        dispute.outcome = "FULL_REFUND"
        dispute.save(update_fields=["status", "outcome"])
        res = admin_client.post(
            f"{BASE}admin/{dispute.id}/refund/",
            {"stripe_refund_id": "re_test123", "amount_pence": 399},
            format="json",
        )
        assert res.status_code == 201
        assert res.json()["stripe_refund_id"] == "re_test123"

    def test_cannot_refund_non_refund_outcome(
        self, admin_client, buyer, supplier, dispatched_sub_order
    ):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Broken item.",
            resolution_requested="FULL_REFUND",
        )
        dispute.status = DisputeStatus.RESOLVED
        dispute.outcome = "REJECTED"
        dispute.save(update_fields=["status", "outcome"])
        res = admin_client.post(
            f"{BASE}admin/{dispute.id}/refund/",
            {"stripe_refund_id": "re_test456", "amount_pence": 399},
            format="json",
        )
        assert res.status_code == 409
