"""Tests for the dispute resolution feature (Issues #36, #37, #38, #39, #40)."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

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
# Service layer — core (#36)
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
        # REJECTED outcome doesn't trigger Stripe; no payment fixture needed.
        services.resolve_dispute(
            dispute, admin_user, "REJECTED", None, "Supplier evidence accepted."
        )
        dispute.refresh_from_db()
        assert dispute.payout_held is False
        assert dispute.outcome == "REJECTED"

    def test_resolve_keeps_hold_for_refund_outcome(
        self, buyer, supplier, admin_user, dispatched_sub_order, payment
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

        fake_refund = MagicMock()
        fake_refund.id = "re_auto123"
        with patch("apps.disputes.services.stripe") as mock_stripe:
            mock_stripe.Refund.create.return_value = fake_refund
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
# Service layer — auto-escalate (#39)
# ---------------------------------------------------------------------------


class TestAutoEscalateService:
    def test_escalates_overdue_open_disputes(
        self, buyer, supplier, dispatched_sub_order, admin_user
    ):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Broken.",
            resolution_requested="FULL_REFUND",
        )
        # Force the deadline into the past.
        from django.utils import timezone

        dispute.response_deadline = timezone.now() - timedelta(hours=1)
        dispute.save(update_fields=["response_deadline"])

        count = services.auto_escalate_overdue_disputes()

        assert count == 1
        dispute.refresh_from_db()
        assert dispute.status == DisputeStatus.ESCALATED
        events = list(DisputeEvent.objects.filter(dispute=dispute).order_by("created_at"))
        assert events[-1].event_type == DisputeEventType.AUTO_ESCALATED

    def test_already_escalated_not_affected(self, buyer, supplier, dispatched_sub_order):
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
        # Even with an overdue deadline, ESCALATED disputes are skipped.
        from django.utils import timezone

        dispute.response_deadline = timezone.now() - timedelta(hours=1)
        dispute.save(update_fields=["response_deadline"])

        count = services.auto_escalate_overdue_disputes()
        assert count == 0

    def test_not_yet_overdue_not_affected(self, buyer, supplier, dispatched_sub_order):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Broken.",
            resolution_requested="FULL_REFUND",
        )
        from django.utils import timezone

        assert dispute.response_deadline > timezone.now()
        count = services.auto_escalate_overdue_disputes()
        assert count == 0


# ---------------------------------------------------------------------------
# Service layer — auto-refund on resolve (#40)
# ---------------------------------------------------------------------------


class TestAutoRefundOnResolve:
    def test_full_refund_calls_stripe_and_creates_record(
        self, buyer, supplier, admin_user, dispatched_sub_order, payment
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

        fake_refund = MagicMock()
        fake_refund.id = "re_autotest456"
        with patch("apps.disputes.services.stripe") as mock_stripe:
            mock_stripe.Refund.create.return_value = fake_refund
            services.resolve_dispute(dispute, admin_user, "FULL_REFUND", None, "Approved.")
            mock_stripe.Refund.create.assert_called_once()
            _, kwargs = mock_stripe.Refund.create.call_args
            assert kwargs["payment_intent"] == payment.stripe_payment_intent_id

        from apps.disputes.models import DisputeRefund

        refund = DisputeRefund.objects.get(dispute=dispute)
        assert refund.stripe_refund_id == "re_autotest456"
        assert refund.sub_order == dispatched_sub_order

    def test_partial_refund_uses_outcome_amount(
        self, buyer, supplier, admin_user, dispatched_sub_order, payment
    ):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Partially damaged.",
            resolution_requested="PARTIAL_REFUND",
        )
        dispute.status = DisputeStatus.ESCALATED
        dispute.save(update_fields=["status"])

        fake_refund = MagicMock()
        fake_refund.id = "re_partial789"
        with patch("apps.disputes.services.stripe") as mock_stripe:
            mock_stripe.Refund.create.return_value = fake_refund
            services.resolve_dispute(dispute, admin_user, "PARTIAL_REFUND", 200, "Half refund.")
            _, kwargs = mock_stripe.Refund.create.call_args
            assert kwargs["amount"] == 200

    def test_rejected_outcome_does_not_call_stripe(
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

        with patch("apps.disputes.services.stripe") as mock_stripe:
            services.resolve_dispute(dispute, admin_user, "REJECTED", None, "Rejected.")
            mock_stripe.Refund.create.assert_not_called()


# ---------------------------------------------------------------------------
# API views — core (#36)
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
        assert "messages" in data
        assert "attachments" in data

    def test_non_party_cannot_view(self, api_client, db, buyer, supplier, dispatched_sub_order):
        dispute = services.open_dispute(
            sub_order=dispatched_sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Item arrived broken.",
            resolution_requested="FULL_REFUND",
        )
        from apps.accounts.models import Role, User

        stranger = User.objects.create_user(
            email="stranger@example.com", password="Securepass123!", role=Role.BUYER
        )
        api_client.force_authenticate(user=stranger)
        res = api_client.get(f"{BASE}{dispute.id}/")
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
    def test_admin_can_resolve_rejected(
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
            {"outcome": "REJECTED", "outcome_notes": "Evidence reviewed, claim rejected."},
            format="json",
        )
        assert res.status_code == 200
        assert res.json()["outcome"] == "REJECTED"

    def test_admin_can_resolve_with_auto_refund(
        self, admin_client, buyer, supplier, admin_user, dispatched_sub_order, payment
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

        fake_refund = MagicMock()
        fake_refund.id = "re_viewtest"
        with patch("apps.disputes.services.stripe") as mock_stripe:
            mock_stripe.Refund.create.return_value = fake_refund
            res = admin_client.post(
                f"{BASE}{dispute.id}/resolve/",
                {"outcome": "FULL_REFUND", "outcome_notes": "Evidence reviewed, refund approved."},
                format="json",
            )
        assert res.status_code == 200
        assert res.json()["outcome"] == "FULL_REFUND"
        assert len(res.json()["refunds"]) == 1

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

    def test_stripe_error_returns_502(
        self, admin_client, buyer, supplier, dispatched_sub_order, payment
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

        with patch("apps.disputes.services.stripe") as mock_stripe:
            mock_stripe.Refund.create.side_effect = Exception("Stripe unreachable")
            res = admin_client.post(
                f"{BASE}{dispute.id}/resolve/",
                {"outcome": "FULL_REFUND", "outcome_notes": "Approved."},
                format="json",
            )
        assert res.status_code == 502
        dispute.refresh_from_db()
        assert dispute.status == DisputeStatus.ESCALATED  # rolled back


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


# ---------------------------------------------------------------------------
# API views — message thread (#38)
# ---------------------------------------------------------------------------


class TestMessageThreadView:
    def _open(self, buyer, supplier, sub_order):
        return services.open_dispute(
            sub_order=sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Item arrived broken.",
            resolution_requested="FULL_REFUND",
        )

    def test_party_can_post_message(self, buyer_client, buyer, supplier, dispatched_sub_order):
        dispute = self._open(buyer, supplier, dispatched_sub_order)
        res = buyer_client.post(
            f"{BASE}{dispute.id}/messages/",
            {"body": "I have additional evidence to share."},
            format="json",
        )
        assert res.status_code == 201
        assert res.json()["body"] == "I have additional evidence to share."

    def test_respondent_can_post_message(
        self, supplier_client, buyer, supplier, dispatched_sub_order
    ):
        dispute = self._open(buyer, supplier, dispatched_sub_order)
        res = supplier_client.post(
            f"{BASE}{dispute.id}/messages/",
            {"body": "Here is our response with evidence attached."},
            format="json",
        )
        assert res.status_code == 201

    def test_admin_can_post_on_resolved_dispute(
        self, admin_client, buyer, supplier, dispatched_sub_order
    ):
        dispute = self._open(buyer, supplier, dispatched_sub_order)
        dispute.status = DisputeStatus.RESOLVED
        dispute.save(update_fields=["status"])
        res = admin_client.post(
            f"{BASE}{dispute.id}/messages/",
            {"body": "Closing note from admin."},
            format="json",
        )
        assert res.status_code == 201

    def test_party_cannot_post_on_resolved_dispute(
        self, buyer_client, buyer, supplier, dispatched_sub_order
    ):
        dispute = self._open(buyer, supplier, dispatched_sub_order)
        dispute.status = DisputeStatus.RESOLVED
        dispute.save(update_fields=["status"])
        res = buyer_client.post(
            f"{BASE}{dispute.id}/messages/",
            {"body": "Trying to message on a resolved dispute."},
            format="json",
        )
        assert res.status_code == 409

    def test_get_lists_messages(self, buyer_client, buyer, supplier, dispatched_sub_order):
        dispute = self._open(buyer, supplier, dispatched_sub_order)
        services.post_message(dispute, buyer, "First message.")
        services.post_message(dispute, supplier.user, "Reply message.")
        res = buyer_client.get(f"{BASE}{dispute.id}/messages/")
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_non_party_cannot_post(self, api_client, db, buyer, supplier, dispatched_sub_order):
        dispute = self._open(buyer, supplier, dispatched_sub_order)
        from apps.accounts.models import Role, User

        stranger = User.objects.create_user(
            email="stranger2@example.com", password="Securepass123!", role=Role.BUYER
        )
        api_client.force_authenticate(user=stranger)
        res = api_client.post(
            f"{BASE}{dispute.id}/messages/",
            {"body": "Intruder message."},
            format="json",
        )
        assert res.status_code == 403

    def test_message_appears_in_dispute_detail(
        self, buyer_client, buyer, supplier, dispatched_sub_order
    ):
        dispute = self._open(buyer, supplier, dispatched_sub_order)
        services.post_message(dispute, buyer, "Detail test message.")
        res = buyer_client.get(f"{BASE}{dispute.id}/")
        assert res.status_code == 200
        assert len(res.json()["messages"]) == 1

    def test_empty_body_rejected(self, buyer_client, buyer, supplier, dispatched_sub_order):
        dispute = self._open(buyer, supplier, dispatched_sub_order)
        res = buyer_client.post(
            f"{BASE}{dispute.id}/messages/",
            {"body": ""},
            format="json",
        )
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# API views — file evidence uploads (#37)
# ---------------------------------------------------------------------------


class TestAttachmentUploadView:
    def _open(self, buyer, supplier, sub_order):
        return services.open_dispute(
            sub_order=sub_order,
            opened_by=buyer,
            respondent=supplier.user,
            dispute_type=DisputeType.DAMAGED,
            description="Item arrived broken.",
            resolution_requested="FULL_REFUND",
        )

    @patch("apps.disputes.services.boto3")
    def test_party_can_request_upload_url(
        self, mock_boto3, buyer_client, buyer, supplier, dispatched_sub_order
    ):
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/upload"

        dispute = self._open(buyer, supplier, dispatched_sub_order)
        res = buyer_client.post(
            f"{BASE}{dispute.id}/attachments/",
            {
                "filename": "damage_photo.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 204800,
            },
            format="json",
        )
        assert res.status_code == 201
        data = res.json()
        assert "upload_url" in data
        assert data["upload_url"] == "https://s3.example.com/upload"
        assert data["attachment"]["filename"] == "damage_photo.jpg"

    @patch("apps.disputes.services.boto3")
    def test_creates_dispute_event_on_upload(
        self, mock_boto3, buyer_client, buyer, supplier, dispatched_sub_order
    ):
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/upload"

        dispute = self._open(buyer, supplier, dispatched_sub_order)
        buyer_client.post(
            f"{BASE}{dispute.id}/attachments/",
            {"filename": "receipt.pdf", "content_type": "application/pdf", "size_bytes": 51200},
            format="json",
        )
        events = DisputeEvent.objects.filter(
            dispute=dispute, event_type=DisputeEventType.ATTACHMENT
        )
        assert events.count() == 1
        assert events.first().body == "receipt.pdf"

    def test_disallowed_content_type_rejected(
        self, buyer_client, buyer, supplier, dispatched_sub_order
    ):
        dispute = self._open(buyer, supplier, dispatched_sub_order)
        res = buyer_client.post(
            f"{BASE}{dispute.id}/attachments/",
            {
                "filename": "malware.exe",
                "content_type": "application/octet-stream",
                "size_bytes": 100,
            },
            format="json",
        )
        assert res.status_code == 400

    def test_oversized_file_rejected(self, buyer_client, buyer, supplier, dispatched_sub_order):
        dispute = self._open(buyer, supplier, dispatched_sub_order)
        res = buyer_client.post(
            f"{BASE}{dispute.id}/attachments/",
            {
                "filename": "huge.jpg",
                "content_type": "image/jpeg",
                "size_bytes": 11 * 1024 * 1024,
            },
            format="json",
        )
        assert res.status_code == 400

    def test_cannot_upload_to_resolved_dispute(
        self, buyer_client, buyer, supplier, dispatched_sub_order
    ):
        dispute = self._open(buyer, supplier, dispatched_sub_order)
        dispute.status = DisputeStatus.RESOLVED
        dispute.save(update_fields=["status"])
        res = buyer_client.post(
            f"{BASE}{dispute.id}/attachments/",
            {"filename": "late.jpg", "content_type": "image/jpeg", "size_bytes": 1000},
            format="json",
        )
        assert res.status_code == 409

    def test_non_party_cannot_upload(self, api_client, db, buyer, supplier, dispatched_sub_order):
        dispute = self._open(buyer, supplier, dispatched_sub_order)
        from apps.accounts.models import Role, User

        stranger = User.objects.create_user(
            email="stranger3@example.com", password="Securepass123!", role=Role.BUYER
        )
        api_client.force_authenticate(user=stranger)
        res = api_client.post(
            f"{BASE}{dispute.id}/attachments/",
            {"filename": "intruder.jpg", "content_type": "image/jpeg", "size_bytes": 1000},
            format="json",
        )
        assert res.status_code == 403
