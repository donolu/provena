"""Real-thread concurrency tests for the payout / refund race fixes.

Two workers hit the same critical section together (synced by a barrier); we assert exactly
one wins and no money is double-moved or over-reserved. Needs real PostgreSQL row locking, so
these skip on sqlite.
"""

from decimal import Decimal
from queue import Queue
from unittest.mock import MagicMock

import pytest

from apps.payments import services
from apps.payments.models import PaymentRefundRequest, Payout, PayoutStatus


@pytest.mark.django_db(transaction=True)
class TestPayoutProcessingRace:
    def test_payout_paid_once(
        self,
        requires_postgres,
        run_concurrently,
        approved_supplier,
        succeeded_payment,
        sub_order,
        mock_stripe_services,
    ):
        approved_supplier.stripe_account_id = "acct_race"
        approved_supplier.stripe_onboarding_complete = True
        approved_supplier.save(update_fields=["stripe_account_id", "stripe_onboarding_complete"])

        transfer_mock = MagicMock()
        transfer_mock.id = "tr_race"
        mock_stripe_services.Transfer.create.return_value = transfer_mock

        payout = Payout.objects.get(sub_order=sub_order)

        def run():
            return services.process_payout(payout)

        results = run_concurrently(run, 2)
        oks = [r for r in results if r[0] == "ok"]
        errs = [r for r in results if r[0] == "error"]

        assert len(oks) == 1  # one worker processed it
        assert len(errs) == 1
        assert "already being processed" in str(errs[0][1])

        payout.refresh_from_db()
        assert payout.status == PayoutStatus.PAID
        mock_stripe_services.Transfer.create.assert_called_once()  # transfer made exactly once


@pytest.mark.django_db(transaction=True)
class TestRefundReservationRace:
    def test_balance_not_over_reserved(
        self, requires_postgres, run_concurrently, succeeded_payment, mock_stripe_services
    ):
        payment = succeeded_payment  # amount £5.00

        intent = MagicMock()
        intent.latest_charge = "ch_race"
        mock_stripe_services.PaymentIntent.retrieve.return_value = intent
        mock_stripe_services.Refund.create.return_value = MagicMock(id="re_race")

        # Two different amounts, each within balance alone but summing over it (3.00 + 2.99 > 5.00),
        # so a different idempotency key each and only one can be reserved.
        amounts: Queue = Queue()
        amounts.put(Decimal("3.00"))
        amounts.put(Decimal("2.99"))

        def refund():
            return services.initiate_refund(payment, amount=amounts.get())

        results = run_concurrently(refund, 2)
        oks = [r for r in results if r[0] == "ok"]
        errs = [r for r in results if r[0] == "error"]

        assert len(oks) == 1  # exactly one reservation fit the balance
        assert len(errs) == 1
        assert "exceeds refundable balance" in str(errs[0][1])

        payment.refresh_from_db()
        # Never reserved beyond the outstanding balance.
        assert payment.pending_refund_amount <= payment.amount
        # The loser cleaned up its request row; only the winner's remains.
        assert PaymentRefundRequest.objects.filter(payment=payment).count() == 1
