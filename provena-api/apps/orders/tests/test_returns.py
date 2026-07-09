"""Tests for ORD-08: returns flow — buyer requests, supplier approves/rejects, admin refunds."""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.orders import services
from apps.orders.models import OrderReturn, ReturnStatus

# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestRequestReturnService:
    def test_can_request_on_delivered_within_window(self, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Changed my mind")
        assert ret.status == ReturnStatus.REQUESTED
        assert ret.reason == "Changed my mind"
        assert ret.raised_by == buyer

    def test_cannot_request_on_pending(self, buyer, sub_order):
        with pytest.raises(ValueError, match="delivered"):
            services.request_return(sub_order, buyer, "Reason")

    def test_cannot_request_on_dispatched(self, buyer, dispatched_sub_order):
        with pytest.raises(ValueError, match="delivered"):
            services.request_return(dispatched_sub_order, buyer, "Reason")

    def test_cannot_request_after_14_days(self, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        sub.delivered_at = timezone.now() - timedelta(days=15)
        sub.save(update_fields=["delivered_at"])
        with pytest.raises(ValueError, match="14 days"):
            services.request_return(sub, buyer, "Too late")

    def test_creates_db_record(self, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        services.request_return(sub, buyer, "Reason")
        assert OrderReturn.objects.filter(sub_order=sub).count() == 1


class TestApproveReturnService:
    def test_approve_requested(self, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Reason")
        approved = services.approve_return(ret, notes="OK")
        assert approved.status == ReturnStatus.APPROVED
        assert approved.supplier_notes == "OK"

    def test_cannot_approve_rejected(self, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Reason")
        services.reject_return(ret)
        with pytest.raises(ValueError, match="requested"):
            services.approve_return(ret)

    def test_cannot_approve_already_approved(self, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Reason")
        services.approve_return(ret)
        with pytest.raises(ValueError, match="requested"):
            services.approve_return(ret)


class TestRejectReturnService:
    def test_reject_requested(self, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Reason")
        rejected = services.reject_return(ret, notes="Policy does not cover this.")
        assert rejected.status == ReturnStatus.REJECTED
        assert rejected.supplier_notes == "Policy does not cover this."

    def test_cannot_reject_approved(self, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Reason")
        services.approve_return(ret)
        with pytest.raises(ValueError, match="requested"):
            services.reject_return(ret)


class TestProcessReturnRefund:
    def test_cannot_refund_requested(self, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Reason")
        with pytest.raises(ValueError, match="approved"):
            services.process_return_refund(ret)

    def test_cannot_refund_rejected(self, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Reason")
        services.reject_return(ret)
        with pytest.raises(ValueError, match="approved"):
            services.process_return_refund(ret)

    def _stripe_mocks(self):
        intent = MagicMock()
        intent.latest_charge = "ch_test"
        pi_patch = patch("stripe.PaymentIntent.retrieve", return_value=intent)
        refund_patch = patch("stripe.Refund.create", return_value=MagicMock(id="re_test"))
        return pi_patch, refund_patch

    def test_refund_approved_return(self, buyer, placed_order, dispatched_sub_order):
        from apps.payments.models import Payment, PaymentStatus

        payment = Payment.objects.create(
            order=placed_order,
            stripe_payment_intent_id="pi_test_ord08",
            amount=Decimal("7.98"),
            status=PaymentStatus.SUCCEEDED,
        )
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Faulty item")
        services.approve_return(ret)

        pi_patch, refund_patch = self._stripe_mocks()
        with pi_patch, refund_patch as mock_refund:
            result = services.process_return_refund(ret)

        assert result.status == ReturnStatus.REFUNDED
        assert result.refund_amount == payment.amount
        mock_refund.assert_called_once()

    def test_partial_refund(self, buyer, placed_order, dispatched_sub_order):
        from apps.payments.models import Payment, PaymentStatus

        Payment.objects.create(
            order=placed_order,
            stripe_payment_intent_id="pi_test_partial",
            amount=Decimal("7.98"),
            status=PaymentStatus.SUCCEEDED,
        )
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "One item faulty")
        services.approve_return(ret)

        pi_patch, refund_patch = self._stripe_mocks()
        with pi_patch, refund_patch:
            result = services.process_return_refund(ret, refund_amount=Decimal("3.99"))

        assert result.refund_amount == Decimal("3.99")

    def test_refunding_retry_uses_claimed_amount(self, buyer, placed_order, dispatched_sub_order):
        """A REFUNDING retry ignores the caller's new amount; uses the already-claimed value."""
        from apps.payments.models import Payment, PaymentStatus

        Payment.objects.create(
            order=placed_order,
            stripe_payment_intent_id="pi_test_retry",
            amount=Decimal("7.98"),
            status=PaymentStatus.SUCCEEDED,
        )
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Faulty item")
        services.approve_return(ret)

        # Simulate a first attempt that claimed £3.99 and set REFUNDING, then crashed
        # before Stripe was called (e.g. the process was killed mid-flight).
        ret.status = ReturnStatus.REFUNDING
        ret.refund_amount = Decimal("3.99")
        ret.save(update_fields=["status", "refund_amount", "updated_at"])

        with patch("apps.payments.services.initiate_refund") as mock_initiate:
            result = services.process_return_refund(ret, refund_amount=Decimal("1.00"))

        assert result.status == ReturnStatus.REFUNDED
        # initiate_refund must have been called with the stored £3.99, not the caller's £1.00.
        mock_initiate.assert_called_once()
        assert mock_initiate.call_args[1]["amount"] == Decimal("3.99")

    def test_refunding_retry_does_not_release_claim_on_failure(
        self, buyer, placed_order, dispatched_sub_order
    ):
        """A retry that observes REFUNDING must not reset status to APPROVED on transient error."""
        from apps.payments.models import Payment, PaymentStatus

        Payment.objects.create(
            order=placed_order,
            stripe_payment_intent_id="pi_test_retry_fail",
            amount=Decimal("7.98"),
            status=PaymentStatus.SUCCEEDED,
        )
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Faulty item")
        services.approve_return(ret)

        # Row is already mid-flight: REFUNDING was set by a different worker.
        ret.status = ReturnStatus.REFUNDING
        ret.refund_amount = Decimal("3.99")
        ret.save(update_fields=["status", "refund_amount", "updated_at"])

        with patch("apps.payments.services.initiate_refund", side_effect=RuntimeError("transient")):
            with pytest.raises(RuntimeError):
                services.process_return_refund(ret)

        # The claim must still be held (REFUNDING), not reset to APPROVED.
        ret.refresh_from_db()
        assert ret.status == ReturnStatus.REFUNDING


# ---------------------------------------------------------------------------
# View tests — buyer
# ---------------------------------------------------------------------------


class TestRequestReturnView:
    def test_buyer_can_request(self, buyer_client, placed_order, dispatched_sub_order):
        services.deliver_sub_order(dispatched_sub_order)
        dispatched_sub_order.refresh_from_db()
        response = buyer_client.post(
            f"/api/v1/orders/{placed_order.reference}/sub-orders/{dispatched_sub_order.id}/return/",
            {"reason": "Wrong size."},
            format="json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "REQUESTED"
        assert data["reason"] == "Wrong size."

    def test_cannot_request_on_dispatched(self, buyer_client, placed_order, dispatched_sub_order):
        response = buyer_client.post(
            f"/api/v1/orders/{placed_order.reference}/sub-orders/{dispatched_sub_order.id}/return/",
            {"reason": "Reason"},
            format="json",
        )
        assert response.status_code == 400

    def test_cannot_request_after_14_days(self, buyer_client, placed_order, dispatched_sub_order):
        services.deliver_sub_order(dispatched_sub_order)
        dispatched_sub_order.delivered_at = timezone.now() - timedelta(days=15)
        dispatched_sub_order.save(update_fields=["delivered_at"])
        response = buyer_client.post(
            f"/api/v1/orders/{placed_order.reference}/sub-orders/{dispatched_sub_order.id}/return/",
            {"reason": "Late"},
            format="json",
        )
        assert response.status_code == 400
        assert "14 days" in response.json()["detail"]

    def test_other_buyer_cannot_request(
        self, api_client, admin_user, placed_order, dispatched_sub_order
    ):
        services.deliver_sub_order(dispatched_sub_order)
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            f"/api/v1/orders/{placed_order.reference}/sub-orders/{dispatched_sub_order.id}/return/",
            {"reason": "Not mine"},
            format="json",
        )
        assert response.status_code == 404

    def test_unauthenticated_cannot_request(self, client, placed_order, dispatched_sub_order):
        services.deliver_sub_order(dispatched_sub_order)
        response = client.post(
            f"/api/v1/orders/{placed_order.reference}/sub-orders/{dispatched_sub_order.id}/return/",
            {"reason": "Anon"},
            format="json",
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# View tests — supplier
# ---------------------------------------------------------------------------


class TestSupplierReturnListView:
    def test_supplier_sees_own_returns(self, supplier_client, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        services.request_return(sub, buyer, "Broken")
        response = supplier_client.get("/api/v1/orders/supplier/returns/")
        assert response.status_code == 200
        assert len(response.json()["results"]) == 1

    def test_other_supplier_sees_nothing(self, second_supplier_client, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        services.request_return(sub, buyer, "Broken")
        response = second_supplier_client.get("/api/v1/orders/supplier/returns/")
        assert response.json()["results"] == []

    def test_filter_by_status(self, supplier_client, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Issue")
        services.approve_return(ret)
        response = supplier_client.get("/api/v1/orders/supplier/returns/?status=REQUESTED")
        assert response.json()["results"] == []
        response2 = supplier_client.get("/api/v1/orders/supplier/returns/?status=APPROVED")
        assert len(response2.json()["results"]) == 1


class TestSupplierApproveReturnView:
    def test_approve(self, supplier_client, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Reason")
        response = supplier_client.post(
            f"/api/v1/orders/supplier/returns/{ret.id}/approve/",
            {"notes": "Please post back."},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "APPROVED"
        assert response.json()["supplier_notes"] == "Please post back."

    def test_other_supplier_cannot_approve(
        self, second_supplier_client, buyer, dispatched_sub_order
    ):
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Reason")
        response = second_supplier_client.post(
            f"/api/v1/orders/supplier/returns/{ret.id}/approve/", {}, format="json"
        )
        assert response.status_code == 404


class TestSupplierRejectReturnView:
    def test_reject(self, supplier_client, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Reason")
        response = supplier_client.post(
            f"/api/v1/orders/supplier/returns/{ret.id}/reject/",
            {"notes": "Outside return policy."},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "REJECTED"

    def test_cannot_reject_approved(self, supplier_client, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Reason")
        services.approve_return(ret)
        response = supplier_client.post(
            f"/api/v1/orders/supplier/returns/{ret.id}/reject/", {}, format="json"
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# View tests — admin
# ---------------------------------------------------------------------------


class TestAdminReturnListView:
    def test_admin_can_list(self, admin_client, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        services.request_return(sub, buyer, "Issue")
        response = admin_client.get("/api/v1/orders/admin/returns/")
        assert response.status_code == 200
        assert len(response.json()["results"]) == 1

    def test_filter_by_status(self, admin_client, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Issue")
        services.approve_return(ret)
        response = admin_client.get("/api/v1/orders/admin/returns/?status=REQUESTED")
        assert response.json()["results"] == []
        response2 = admin_client.get("/api/v1/orders/admin/returns/?status=APPROVED")
        assert len(response2.json()["results"]) == 1

    def test_buyer_cannot_list(self, buyer_client):
        response = buyer_client.get("/api/v1/orders/admin/returns/")
        assert response.status_code == 403


class TestAdminProcessReturnRefundView:
    def test_admin_can_refund(self, admin_client, placed_order, buyer, dispatched_sub_order):
        from apps.payments.models import Payment, PaymentStatus

        Payment.objects.create(
            order=placed_order,
            stripe_payment_intent_id="pi_view_refund",
            amount=Decimal("7.98"),
            status=PaymentStatus.SUCCEEDED,
        )
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Faulty")
        services.approve_return(ret)

        intent = MagicMock()
        intent.latest_charge = "ch_view"
        with (
            patch("stripe.PaymentIntent.retrieve", return_value=intent),
            patch("stripe.Refund.create", return_value=MagicMock(id="re_view")),
        ):
            response = admin_client.post(
                f"/api/v1/orders/admin/returns/{ret.id}/refund/",
                {},
                format="json",
            )

        assert response.status_code == 200
        assert response.json()["status"] == "REFUNDED"

    def test_cannot_refund_requested(self, admin_client, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Reason")
        response = admin_client.post(
            f"/api/v1/orders/admin/returns/{ret.id}/refund/", {}, format="json"
        )
        assert response.status_code == 400

    def test_buyer_cannot_refund(self, buyer_client, buyer, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Reason")
        services.approve_return(ret)
        response = buyer_client.post(
            f"/api/v1/orders/admin/returns/{ret.id}/refund/", {}, format="json"
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Returns nested in order detail
# ---------------------------------------------------------------------------


class TestReturnsInOrderDetail:
    def test_returns_nested_in_sub_order(
        self, buyer_client, placed_order, dispatched_sub_order, buyer
    ):
        sub = services.deliver_sub_order(dispatched_sub_order)
        services.request_return(sub, buyer, "Test return")
        response = buyer_client.get(f"/api/v1/orders/{placed_order.reference}/")
        assert response.status_code == 200
        sub_data = response.json()["sub_orders"][0]
        assert len(sub_data["returns"]) == 1
        assert sub_data["returns"][0]["reason"] == "Test return"
        assert sub_data["returns"][0]["status"] == "REQUESTED"
