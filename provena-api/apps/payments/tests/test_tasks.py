from unittest.mock import MagicMock, patch

import pytest

from apps.payments.models import Payout, PayoutStatus
from apps.payments.tasks import trigger_payout


@pytest.fixture
def pending_payout(succeeded_payment, sub_order):
    return Payout.objects.get(sub_order=sub_order)


@pytest.fixture
def stripe_connect_mocks():
    intent = MagicMock()
    intent.latest_charge = "ch_test"
    with patch("apps.payments.services.stripe") as mock:
        mock.PaymentIntent.retrieve.return_value = intent
        mock.Transfer.create.return_value = MagicMock(id="tr_test")
        yield mock


class TestTriggerPayoutTask:
    def test_processes_pending_payout(
        self, pending_payout, approved_supplier, stripe_connect_mocks
    ):
        approved_supplier.stripe_account_id = "acct_test"
        approved_supplier.stripe_onboarding_complete = True
        approved_supplier.save()

        result = trigger_payout(str(pending_payout.id))

        assert result["status"] == "processed"
        assert result["payout_id"] == str(pending_payout.id)
        pending_payout.refresh_from_db()
        assert pending_payout.status == PayoutStatus.PAID

    def test_skips_non_pending_payout(
        self, pending_payout, approved_supplier, stripe_connect_mocks
    ):
        approved_supplier.stripe_account_id = "acct_test"
        approved_supplier.stripe_onboarding_complete = True
        approved_supplier.save()

        pending_payout.status = PayoutStatus.PAID
        pending_payout.save()

        result = trigger_payout(str(pending_payout.id))

        assert result["status"] == "skipped"
        stripe_connect_mocks.Transfer.create.assert_not_called()

    def test_resumes_processing_payout_via_task(
        self, pending_payout, approved_supplier, stripe_connect_mocks
    ):
        approved_supplier.stripe_account_id = "acct_test"
        approved_supplier.stripe_onboarding_complete = True
        approved_supplier.save()

        pending_payout.status = PayoutStatus.PROCESSING
        pending_payout.save()

        result = trigger_payout(str(pending_payout.id))

        assert result["status"] == "processed"
        stripe_connect_mocks.Transfer.create.assert_called_once()

    def test_skips_supplier_without_stripe(self, pending_payout):
        result = trigger_payout(str(pending_payout.id))

        assert result["status"] == "no_stripe_account"
        pending_payout.refresh_from_db()
        assert pending_payout.status == PayoutStatus.PENDING

    def test_returns_not_found_for_missing_payout(self, db):
        import uuid

        result = trigger_payout(str(uuid.uuid4()))
        assert result["status"] == "not_found"

    def test_deliver_sub_order_queues_payout_task(
        self, succeeded_payment, sub_order, approved_supplier
    ):
        from apps.orders import services as order_services

        order_services.confirm_sub_order(sub_order)
        order_services.dispatch_sub_order(sub_order, tracking_number="TRK123")

        with patch("apps.payments.tasks.trigger_payout.delay") as mock_delay:
            order_services.deliver_sub_order(sub_order)
            mock_delay.assert_called_once_with(str(Payout.objects.get(sub_order=sub_order).id))
