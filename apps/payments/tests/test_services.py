from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from apps.payments import services
from apps.payments.models import Payment, PaymentStatus, Payout, PayoutStatus
from apps.payments.tests.conftest import FAKE_INTENT_ID


class TestCreatePaymentIntent:
    def test_creates_payment(self, placed_order, mock_stripe_services):
        payment = services.create_payment_intent(placed_order)
        assert payment.stripe_payment_intent_id == FAKE_INTENT_ID
        assert payment.status == PaymentStatus.PROCESSING
        assert payment.amount == placed_order.total_amount
        assert payment.currency == "gbp"

    def test_idempotent_if_payment_exists(self, payment, placed_order, mock_stripe_services):
        payment2 = services.create_payment_intent(placed_order)
        assert payment2.id == payment.id
        assert mock_stripe_services.PaymentIntent.create.call_count == 1

    def test_raises_if_order_not_pending(self, placed_order, mock_stripe_services):
        from apps.orders import services as order_services

        order_services.cancel_order(placed_order)
        with pytest.raises(ValueError, match="status"):
            services.create_payment_intent(placed_order)

    def test_calls_stripe_with_correct_amount(self, placed_order, mock_stripe_services):
        services.create_payment_intent(placed_order)
        call_kwargs = mock_stripe_services.PaymentIntent.create.call_args[1]
        assert call_kwargs["amount"] == int(placed_order.total_amount * 100)
        assert call_kwargs["currency"] == "gbp"
        assert call_kwargs["metadata"]["order_reference"] == placed_order.reference


class TestHandlePaymentSucceeded:
    def test_updates_status(self, payment):
        result = services.handle_payment_succeeded(payment.stripe_payment_intent_id)
        assert result.status == PaymentStatus.SUCCEEDED

    def test_idempotent_if_already_succeeded(self, payment):
        services.handle_payment_succeeded(payment.stripe_payment_intent_id)
        result = services.handle_payment_succeeded(payment.stripe_payment_intent_id)
        assert result.status == PaymentStatus.SUCCEEDED

    def test_creates_payouts(self, payment, sub_order):
        services.handle_payment_succeeded(payment.stripe_payment_intent_id)
        assert Payout.objects.filter(sub_order=sub_order).count() == 1

    def test_payout_amounts(self, payment, sub_order, placed_order):
        services.handle_payment_succeeded(payment.stripe_payment_intent_id)
        payout = Payout.objects.get(sub_order=sub_order)
        assert payout.gross_amount == sub_order.subtotal
        assert payout.platform_fee == (
            sub_order.subtotal * Decimal("10") / Decimal("100")
        ).quantize(Decimal("0.01"))
        assert payout.net_amount == payout.gross_amount - payout.platform_fee

    def test_payout_linked_to_supplier(self, payment, sub_order, approved_supplier):
        services.handle_payment_succeeded(payment.stripe_payment_intent_id)
        payout = Payout.objects.get(sub_order=sub_order)
        assert payout.supplier == approved_supplier

    def test_payout_status_pending(self, payment, sub_order):
        services.handle_payment_succeeded(payment.stripe_payment_intent_id)
        payout = Payout.objects.get(sub_order=sub_order)
        assert payout.status == PayoutStatus.PENDING

    def test_payout_idempotent(self, payment, sub_order):
        services.handle_payment_succeeded(payment.stripe_payment_intent_id)
        services.handle_payment_succeeded(payment.stripe_payment_intent_id)
        assert Payout.objects.filter(sub_order=sub_order).count() == 1

    def test_raises_if_payment_not_found(self, db):
        with pytest.raises(Payment.DoesNotExist):
            services.handle_payment_succeeded("pi_nonexistent")


class TestHandlePaymentFailed:
    def test_updates_status(self, payment):
        result = services.handle_payment_failed(payment.stripe_payment_intent_id)
        assert result.status == PaymentStatus.FAILED

    def test_idempotent(self, payment):
        services.handle_payment_failed(payment.stripe_payment_intent_id)
        result = services.handle_payment_failed(payment.stripe_payment_intent_id)
        assert result.status == PaymentStatus.FAILED

    def test_raises_if_payment_not_found(self, db):
        with pytest.raises(Payment.DoesNotExist):
            services.handle_payment_failed("pi_nonexistent")


class TestHandleRefund:
    def test_updates_status_to_refunded(self, payment):
        result = services.handle_refund(payment.stripe_payment_intent_id)
        assert result.status == PaymentStatus.REFUNDED

    def test_cancels_pending_payouts(self, payment, sub_order):
        services.handle_payment_succeeded(payment.stripe_payment_intent_id)
        services.handle_refund(payment.stripe_payment_intent_id)
        payout = Payout.objects.get(sub_order=sub_order)
        assert payout.status == PayoutStatus.FAILED

    def test_raises_if_payment_not_found(self, db):
        with pytest.raises(Payment.DoesNotExist):
            services.handle_refund("pi_nonexistent")


class TestHandlePaymentCancelled:
    def test_updates_status(self, payment):
        result = services.handle_payment_cancelled(payment.stripe_payment_intent_id)
        assert result.status == PaymentStatus.CANCELLED


class TestProcessPayout:
    @pytest.fixture
    def onboarded_supplier(self, approved_supplier):
        approved_supplier.stripe_account_id = "acct_test_123"
        approved_supplier.stripe_onboarding_complete = True
        approved_supplier.save(update_fields=["stripe_account_id", "stripe_onboarding_complete"])
        return approved_supplier

    @pytest.fixture
    def pending_payout(self, succeeded_payment, sub_order):
        return Payout.objects.get(sub_order=sub_order)

    @pytest.fixture
    def mock_stripe_transfer(self, mock_stripe_services):
        intent_mock = MagicMock()
        intent_mock.latest_charge = "ch_test_abc"
        mock_stripe_services.PaymentIntent.retrieve.return_value = intent_mock

        transfer_mock = MagicMock()
        transfer_mock.id = "tr_test_abc"
        mock_stripe_services.Transfer.create.return_value = transfer_mock
        return mock_stripe_services

    def test_raises_if_not_pending(self, pending_payout, onboarded_supplier, mock_stripe_transfer):
        pending_payout.status = PayoutStatus.PROCESSING
        pending_payout.save(update_fields=["status"])
        with pytest.raises(ValueError, match="status"):
            services.process_payout(pending_payout)

    def test_raises_if_no_stripe_account(self, pending_payout, mock_stripe_transfer):
        with pytest.raises(ValueError, match="Stripe Connect onboarding"):
            services.process_payout(pending_payout)

    def test_raises_if_onboarding_incomplete(
        self, pending_payout, approved_supplier, mock_stripe_transfer
    ):
        approved_supplier.stripe_account_id = "acct_test_123"
        approved_supplier.stripe_onboarding_complete = False
        approved_supplier.save(update_fields=["stripe_account_id", "stripe_onboarding_complete"])
        with pytest.raises(ValueError, match="Stripe Connect onboarding"):
            services.process_payout(pending_payout)

    def test_creates_transfer_to_supplier(
        self, pending_payout, onboarded_supplier, mock_stripe_transfer
    ):
        services.process_payout(pending_payout)
        call_kwargs = mock_stripe_transfer.Transfer.create.call_args[1]
        assert call_kwargs["destination"] == "acct_test_123"
        assert call_kwargs["currency"] == "gbp"

    def test_transfer_amount_is_net(self, pending_payout, onboarded_supplier, mock_stripe_transfer):
        net_pence = int(pending_payout.net_amount * 100)
        services.process_payout(pending_payout)
        call_kwargs = mock_stripe_transfer.Transfer.create.call_args[1]
        assert call_kwargs["amount"] == net_pence

    def test_transfer_uses_source_transaction(
        self, pending_payout, onboarded_supplier, mock_stripe_transfer
    ):
        services.process_payout(pending_payout)
        call_kwargs = mock_stripe_transfer.Transfer.create.call_args[1]
        assert call_kwargs["source_transaction"] == "ch_test_abc"

    def test_saves_transfer_id(self, pending_payout, onboarded_supplier, mock_stripe_transfer):
        services.process_payout(pending_payout)
        pending_payout.refresh_from_db()
        assert pending_payout.stripe_transfer_id == "tr_test_abc"

    def test_marks_paid(self, pending_payout, onboarded_supplier, mock_stripe_transfer):
        services.process_payout(pending_payout)
        pending_payout.refresh_from_db()
        assert pending_payout.status == PayoutStatus.PAID

    def test_stripe_error_marks_failed_and_raises(
        self, pending_payout, onboarded_supplier, mock_stripe_transfer
    ):
        mock_stripe_transfer.StripeError = Exception
        mock_stripe_transfer.Transfer.create.side_effect = Exception("card declined")
        with pytest.raises(ValueError, match="Stripe transfer failed"):
            services.process_payout(pending_payout)
        pending_payout.refresh_from_db()
        assert pending_payout.status == PayoutStatus.FAILED
