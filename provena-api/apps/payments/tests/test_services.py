from datetime import timedelta
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

    def test_drains_pending_refund_amount_on_webhook(self, succeeded_payment):
        # Simulate an in-flight refund reservation of £1.
        succeeded_payment.pending_refund_amount = Decimal("1.00")
        succeeded_payment.save(update_fields=["pending_refund_amount"])
        amount_pence = int(succeeded_payment.amount * 100)
        services.handle_refund(
            succeeded_payment.stripe_payment_intent_id,
            amount_refunded_pence=100,
            charge_amount_pence=amount_pence,
        )
        succeeded_payment.refresh_from_db()
        assert succeeded_payment.pending_refund_amount == Decimal("0.00")


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

    def test_raises_if_paid(self, pending_payout, onboarded_supplier, mock_stripe_transfer):
        pending_payout.status = PayoutStatus.PAID
        pending_payout.save(update_fields=["status"])
        with pytest.raises(ValueError, match="status"):
            services.process_payout(pending_payout)

    def test_raises_if_active_processing_payout(
        self, pending_payout, onboarded_supplier, mock_stripe_transfer
    ):
        from django.utils import timezone

        # Mark as recently started — should be treated as active, not stale.
        pending_payout.status = PayoutStatus.PROCESSING
        pending_payout.processing_started_at = timezone.now()
        pending_payout.save(update_fields=["status", "processing_started_at"])

        with pytest.raises(ValueError, match="already being processed"):
            services.process_payout(pending_payout)
        mock_stripe_transfer.Transfer.create.assert_not_called()

    def test_raises_if_no_stripe_account(self, pending_payout, mock_stripe_transfer):
        with pytest.raises(ValueError, match="Stripe Connect onboarding"):
            services.process_payout(pending_payout)
        pending_payout.refresh_from_db()
        assert pending_payout.status == PayoutStatus.PENDING

    def test_raises_if_onboarding_incomplete(
        self, pending_payout, approved_supplier, mock_stripe_transfer
    ):
        approved_supplier.stripe_account_id = "acct_test_123"
        approved_supplier.stripe_onboarding_complete = False
        approved_supplier.save(update_fields=["stripe_account_id", "stripe_onboarding_complete"])
        with pytest.raises(ValueError, match="Stripe Connect onboarding"):
            services.process_payout(pending_payout)
        pending_payout.refresh_from_db()
        assert pending_payout.status == PayoutStatus.PENDING

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

    def test_stripe_error_does_not_overwrite_paid_payout(
        self, pending_payout, onboarded_supplier, mock_stripe_transfer
    ):
        # Simulate: Transfer.create raised but payout was already written as PAID
        # (e.g. by the first worker whose commit arrived after we raised).
        def _mark_paid_then_raise(*args, **kwargs):
            pending_payout.status = PayoutStatus.PAID
            pending_payout.save(update_fields=["status"])
            raise Exception("network blip")

        mock_stripe_transfer.StripeError = Exception
        mock_stripe_transfer.Transfer.create.side_effect = _mark_paid_then_raise

        with pytest.raises(ValueError, match="Stripe transfer failed"):
            services.process_payout(pending_payout)
        pending_payout.refresh_from_db()
        assert pending_payout.status == PayoutStatus.PAID

    def test_transfer_uses_idempotency_key(
        self, pending_payout, onboarded_supplier, mock_stripe_transfer
    ):
        services.process_payout(pending_payout)
        call_kwargs = mock_stripe_transfer.Transfer.create.call_args[1]
        assert call_kwargs["idempotency_key"] == f"payout-{pending_payout.id}"

    def test_resumes_stale_processing_payout(
        self, pending_payout, onboarded_supplier, mock_stripe_transfer
    ):
        from django.utils import timezone

        # Simulate process dying after PROCESSING was set but before PAID was saved.
        pending_payout.status = PayoutStatus.PROCESSING
        pending_payout.processing_started_at = timezone.now() - timedelta(minutes=15)
        pending_payout.save(update_fields=["status", "processing_started_at"])

        services.process_payout(pending_payout)
        pending_payout.refresh_from_db()
        assert pending_payout.status == PayoutStatus.PAID
        mock_stripe_transfer.Transfer.create.assert_called_once()

    def test_sets_processing_started_at_on_pending_transition(
        self, pending_payout, onboarded_supplier, mock_stripe_transfer
    ):
        services.process_payout(pending_payout)
        pending_payout.refresh_from_db()
        assert pending_payout.processing_started_at is not None


class TestInitiateRefund:
    @pytest.fixture
    def mock_stripe_refund(self):
        from unittest.mock import patch

        intent = MagicMock()
        intent.latest_charge = "ch_test_refund"
        with patch("apps.payments.services.stripe") as mock:
            mock.PaymentIntent.retrieve.return_value = intent
            mock.Refund.create.return_value = MagicMock(id="re_test")
            yield mock

    def test_raises_if_payment_not_succeeded(self, payment, mock_stripe_refund):
        with pytest.raises(ValueError, match="status"):
            services.initiate_refund(payment)

    def test_raises_if_amount_exceeds_balance(self, succeeded_payment, mock_stripe_refund):
        with pytest.raises(ValueError, match="exceeds refundable balance"):
            services.initiate_refund(succeeded_payment, amount=succeeded_payment.amount + 1)

    def test_raises_if_amount_is_zero(self, succeeded_payment, mock_stripe_refund):
        with pytest.raises(ValueError, match="greater than zero"):
            services.initiate_refund(succeeded_payment, amount=Decimal("0.00"))

    def test_raises_if_amount_is_negative(self, succeeded_payment, mock_stripe_refund):
        with pytest.raises(ValueError, match="greater than zero"):
            services.initiate_refund(succeeded_payment, amount=Decimal("-1.00"))

    def test_full_refund_sends_correct_amount(self, succeeded_payment, mock_stripe_refund):
        services.initiate_refund(succeeded_payment)
        call_kwargs = mock_stripe_refund.Refund.create.call_args[1]
        assert call_kwargs["amount"] == int(succeeded_payment.amount * 100)

    def test_partial_refund_sends_correct_amount(self, succeeded_payment, mock_stripe_refund):
        services.initiate_refund(succeeded_payment, amount=Decimal("1.00"))
        call_kwargs = mock_stripe_refund.Refund.create.call_args[1]
        assert call_kwargs["amount"] == 100

    def test_uses_idempotency_key(self, succeeded_payment, mock_stripe_refund):
        services.initiate_refund(succeeded_payment)
        call_kwargs = mock_stripe_refund.Refund.create.call_args[1]
        expected_amount_pence = int(succeeded_payment.amount * 100)
        assert (
            call_kwargs["idempotency_key"]
            == f"refund-{succeeded_payment.id}-{expected_amount_pence}"
        )

    def test_raises_if_no_charge_on_intent(self, succeeded_payment, mock_stripe_refund):
        mock_stripe_refund.PaymentIntent.retrieve.return_value.latest_charge = None
        with pytest.raises(ValueError, match="No charge found"):
            services.initiate_refund(succeeded_payment)

    def test_creates_refund_request_and_drains_after_stripe(
        self, succeeded_payment, mock_stripe_refund
    ):
        from apps.payments.models import PaymentRefundRequest, PaymentRefundRequestStatus

        amount = Decimal("1.00")
        services.initiate_refund(succeeded_payment, amount=amount)

        succeeded_payment.refresh_from_db()
        # Reservation is drained to zero once Stripe confirms.
        assert succeeded_payment.pending_refund_amount == Decimal("0.00")

        req = PaymentRefundRequest.objects.get(payment=succeeded_payment)
        assert req.amount == amount
        assert req.status == PaymentRefundRequestStatus.COMPLETED
        assert req.stripe_refund_id == "re_test"

    def test_concurrent_refunds_blocked_by_reservation(self, succeeded_payment, mock_stripe_refund):
        from apps.payments.models import PaymentRefundRequest, PaymentRefundRequestStatus

        # Simulate an in-flight full-refund reservation (another worker is calling Stripe).
        amount_pence = int(succeeded_payment.amount * 100)
        PaymentRefundRequest.objects.create(
            payment=succeeded_payment,
            amount=succeeded_payment.amount,
            stripe_idempotency_key=f"refund-{succeeded_payment.id}-{amount_pence}",
            status=PaymentRefundRequestStatus.PENDING,
        )
        succeeded_payment.pending_refund_amount = succeeded_payment.amount
        succeeded_payment.save(update_fields=["pending_refund_amount"])

        # A concurrent call for a different amount should find no refundable balance.
        with pytest.raises(ValueError, match="exceeds refundable balance"):
            services.initiate_refund(succeeded_payment, amount=Decimal("0.01"))

    def test_retry_with_same_amount_does_not_double_reserve(
        self, succeeded_payment, mock_stripe_refund
    ):
        from apps.payments.models import PaymentRefundRequest, PaymentRefundRequestStatus

        amount = Decimal("1.00")
        amount_pence = 100

        # Simulate a PENDING request whose reservation is already in place.
        PaymentRefundRequest.objects.create(
            payment=succeeded_payment,
            amount=amount,
            stripe_idempotency_key=f"refund-{succeeded_payment.id}-{amount_pence}",
            status=PaymentRefundRequestStatus.PENDING,
        )
        succeeded_payment.pending_refund_amount = amount
        succeeded_payment.save(update_fields=["pending_refund_amount"])

        # Retry: same idempotency key → should find PENDING, skip increment, call Stripe,
        # then drain the existing reservation on success.
        services.initiate_refund(succeeded_payment, amount=amount)

        succeeded_payment.refresh_from_db()
        assert succeeded_payment.pending_refund_amount == Decimal("0.00")
        # Stripe was called exactly once by this retry.
        mock_stripe_refund.Refund.create.assert_called_once()

    def test_failed_request_can_be_retried(self, succeeded_payment, mock_stripe_refund):
        from apps.payments.models import PaymentRefundRequest, PaymentRefundRequestStatus

        amount = Decimal("1.00")
        amount_pence = 100

        # Simulate a previously-failed attempt with no pending reservation.
        PaymentRefundRequest.objects.create(
            payment=succeeded_payment,
            amount=amount,
            stripe_idempotency_key=f"refund-{succeeded_payment.id}-{amount_pence}",
            status=PaymentRefundRequestStatus.FAILED,
        )

        # Retry: should reset to PENDING, re-reserve, and call Stripe.
        services.initiate_refund(succeeded_payment, amount=amount)

        req = PaymentRefundRequest.objects.get(payment=succeeded_payment)
        assert req.status == PaymentRefundRequestStatus.COMPLETED
        mock_stripe_refund.Refund.create.assert_called_once()

    def test_releases_reservation_on_stripe_error(self, succeeded_payment, mock_stripe_refund):
        mock_stripe_refund.StripeError = Exception
        mock_stripe_refund.Refund.create.side_effect = Exception("stripe down")
        with pytest.raises(ValueError, match="Stripe refund failed"):
            services.initiate_refund(succeeded_payment, amount=Decimal("1.00"))
        succeeded_payment.refresh_from_db()
        assert succeeded_payment.pending_refund_amount == Decimal("0.00")
