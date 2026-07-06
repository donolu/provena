import json
from decimal import Decimal
from unittest.mock import MagicMock

from apps.payments.models import PaymentStatus
from apps.payments.tests.conftest import FAKE_CLIENT_SECRET, FAKE_INTENT_ID


class TestCreatePaymentIntentView:
    def test_creates_intent(self, buyer_client, placed_order, mock_stripe_services):
        response = buyer_client.post(
            "/api/v1/payments/create-intent/",
            {"order_reference": placed_order.reference},
            format="json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["client_secret"] == FAKE_CLIENT_SECRET
        assert "payment_id" in data
        assert Decimal(data["amount"]) == placed_order.total_amount

    def test_idempotent_returns_same_payment(
        self, buyer_client, placed_order, mock_stripe_services
    ):
        r1 = buyer_client.post(
            "/api/v1/payments/create-intent/",
            {"order_reference": placed_order.reference},
            format="json",
        )
        r2 = buyer_client.post(
            "/api/v1/payments/create-intent/",
            {"order_reference": placed_order.reference},
            format="json",
        )
        assert r1.json()["payment_id"] == r2.json()["payment_id"]

    def test_404_for_another_buyers_order(
        self, supplier_client, placed_order, mock_stripe_services
    ):
        response = supplier_client.post(
            "/api/v1/payments/create-intent/",
            {"order_reference": placed_order.reference},
            format="json",
        )
        assert response.status_code == 404

    def test_404_for_nonexistent_order(self, buyer_client, mock_stripe_services):
        response = buyer_client.post(
            "/api/v1/payments/create-intent/",
            {"order_reference": "ORD-DOES-NOT-EXIST"},
            format="json",
        )
        assert response.status_code == 404

    def test_400_for_cancelled_order(self, buyer_client, placed_order, mock_stripe_services):
        from apps.orders import services as order_services

        order_services.cancel_order(placed_order)
        response = buyer_client.post(
            "/api/v1/payments/create-intent/",
            {"order_reference": placed_order.reference},
            format="json",
        )
        assert response.status_code == 400

    def test_unauthenticated(self, client):
        from rest_framework.test import APIClient

        c = APIClient()
        response = c.post(
            "/api/v1/payments/create-intent/",
            {"order_reference": "ORD-WHATEVER"},
            format="json",
        )
        assert response.status_code == 401


class TestPaymentListView:
    def test_lists_own_payments(self, buyer_client, payment):
        response = buyer_client.get("/api/v1/payments/")
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_does_not_show_other_buyers(self, supplier_client, payment):
        response = supplier_client.get("/api/v1/payments/")
        assert response.status_code == 200
        assert response.json()["results"] == []

    def test_unauthenticated(self, client):
        from rest_framework.test import APIClient

        response = APIClient().get("/api/v1/payments/")
        assert response.status_code == 401


class TestPaymentDetailView:
    def test_retrieve_own_payment(self, buyer_client, payment, placed_order):
        response = buyer_client.get(f"/api/v1/payments/{placed_order.reference}/")
        assert response.status_code == 200
        data = response.json()
        assert data["order_reference"] == placed_order.reference
        assert data["status"] == "PROCESSING"

    def test_404_for_another_buyers_payment(self, supplier_client, payment, placed_order):
        response = supplier_client.get(f"/api/v1/payments/{placed_order.reference}/")
        assert response.status_code == 404

    def test_404_nonexistent(self, buyer_client):
        response = buyer_client.get("/api/v1/payments/ORD-DOES-NOT-EXIST/")
        assert response.status_code == 404


class TestStripeWebhookView:
    def _post_event(self, client, event_type, obj_id, mock_stripe_views):
        event = {
            "type": event_type,
            "data": {"object": {"id": obj_id}},
        }
        mock_stripe_views.Webhook.construct_event.return_value = event
        return client.post(
            "/api/v1/payments/webhook/",
            data=json.dumps({}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=fake",
        )

    def test_webhook_payment_succeeded(self, client, payment, mock_stripe_views):
        from rest_framework.test import APIClient

        response = self._post_event(
            APIClient(), "payment_intent.succeeded", FAKE_INTENT_ID, mock_stripe_views
        )
        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.SUCCEEDED

    def test_webhook_payment_failed(self, client, payment, mock_stripe_views):
        from rest_framework.test import APIClient

        response = self._post_event(
            APIClient(), "payment_intent.payment_failed", FAKE_INTENT_ID, mock_stripe_views
        )
        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.FAILED

    def test_webhook_invalid_signature(self, client, mock_stripe_views):
        from rest_framework.test import APIClient
        from stripe import SignatureVerificationError

        mock_stripe_views.Webhook.construct_event.side_effect = SignatureVerificationError(
            "bad", "sig"
        )
        response = APIClient().post(
            "/api/v1/payments/webhook/",
            data=json.dumps({}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="bad",
        )
        assert response.status_code == 400

    def test_webhook_charge_refunded(self, client, payment, mock_stripe_views):
        from rest_framework.test import APIClient

        charge_obj = MagicMock()
        charge_obj.payment_intent = FAKE_INTENT_ID
        charge_obj.amount_refunded = int(payment.amount * 100)
        charge_obj.amount = int(payment.amount * 100)
        event = {
            "type": "charge.refunded",
            "data": {"object": charge_obj},
        }
        mock_stripe_views.Webhook.construct_event.return_value = event
        response = APIClient().post(
            "/api/v1/payments/webhook/",
            data=json.dumps({}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=fake",
        )
        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.REFUNDED

    def test_webhook_unknown_payment_intent_ignored(self, db, mock_stripe_views):
        from rest_framework.test import APIClient

        response = self._post_event(
            APIClient(), "payment_intent.succeeded", "pi_unknown_xyz", mock_stripe_views
        )
        assert response.status_code == 200

    def test_webhook_unhandled_event_returns_ok(self, client, mock_stripe_views):
        from rest_framework.test import APIClient

        event = {
            "type": "customer.created",
            "data": {"object": {"id": "cus_test"}},
        }
        mock_stripe_views.Webhook.construct_event.return_value = event
        response = APIClient().post(
            "/api/v1/payments/webhook/",
            data=json.dumps({}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=fake",
        )
        assert response.status_code == 200

    def test_webhook_account_updated_marks_onboarding_complete(
        self, db, mock_stripe_views, approved_supplier
    ):
        from unittest.mock import patch

        from rest_framework.test import APIClient

        approved_supplier.stripe_account_id = "acct_test123"
        approved_supplier.save(update_fields=["stripe_account_id"])

        event = {
            "type": "account.updated",
            "data": {"object": {"id": "acct_test123"}},
        }
        mock_stripe_views.Webhook.construct_event.return_value = event

        fake_account = {"charges_enabled": True, "payouts_enabled": True}
        with patch("apps.suppliers.services.stripe") as mock_supplier_stripe:
            mock_supplier_stripe.Account.retrieve.return_value = fake_account
            response = APIClient().post(
                "/api/v1/payments/webhook/",
                data=json.dumps({}),
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="t=1,v1=fake",
            )

        assert response.status_code == 200
        approved_supplier.refresh_from_db()
        assert approved_supplier.stripe_onboarding_complete is True

    def test_webhook_account_updated_unknown_account_ignored(self, db, mock_stripe_views):
        from rest_framework.test import APIClient

        event = {
            "type": "account.updated",
            "data": {"object": {"id": "acct_unknown"}},
        }
        mock_stripe_views.Webhook.construct_event.return_value = event
        response = APIClient().post(
            "/api/v1/payments/webhook/",
            data=json.dumps({}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=fake",
        )
        assert response.status_code == 200


class TestSupplierPayoutListView:
    def test_lists_own_payouts(self, supplier_client, succeeded_payment, sub_order):
        response = supplier_client.get("/api/v1/payments/payouts/")
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_filter_by_status(self, supplier_client, succeeded_payment):
        response = supplier_client.get("/api/v1/payments/payouts/?status=PENDING")
        assert response.json()["count"] == 1
        response2 = supplier_client.get("/api/v1/payments/payouts/?status=PAID")
        assert response2.json()["results"] == []

    def test_requires_approved_supplier(self, buyer_client):
        response = buyer_client.get("/api/v1/payments/payouts/")
        assert response.status_code == 403

    def test_payout_fields(self, supplier_client, succeeded_payment, sub_order, placed_order):
        response = supplier_client.get("/api/v1/payments/payouts/")
        data = response.json()["results"][0]
        assert data["order_reference"] == placed_order.reference
        assert data["supplier_name"] == "Green Roots Farm"
        assert "gross_amount" in data
        assert "platform_fee" in data
        assert "net_amount" in data


class TestAdminPaymentListView:
    def test_lists_all_payments(self, admin_client, payment):
        response = admin_client.get("/api/v1/payments/admin/")
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_filter_by_status(self, admin_client, payment):
        response = admin_client.get("/api/v1/payments/admin/?status=PROCESSING")
        assert response.json()["count"] == 1
        response2 = admin_client.get("/api/v1/payments/admin/?status=SUCCEEDED")
        assert response2.json()["results"] == []

    def test_requires_admin(self, buyer_client):
        response = buyer_client.get("/api/v1/payments/admin/")
        assert response.status_code == 403


class TestAdminPayoutListView:
    def test_lists_all_payouts(self, admin_client, succeeded_payment):
        response = admin_client.get("/api/v1/payments/admin/payouts/")
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_filter_by_status(self, admin_client, succeeded_payment):
        response = admin_client.get("/api/v1/payments/admin/payouts/?status=PENDING")
        assert response.json()["count"] == 1

    def test_filter_by_supplier(self, admin_client, succeeded_payment):
        response = admin_client.get("/api/v1/payments/admin/payouts/?supplier=green-roots-farm")
        assert response.json()["count"] == 1
        response2 = admin_client.get("/api/v1/payments/admin/payouts/?supplier=nonexistent")
        assert response2.json()["results"] == []

    def test_requires_admin(self, supplier_client):
        response = supplier_client.get("/api/v1/payments/admin/payouts/")
        assert response.status_code == 403
