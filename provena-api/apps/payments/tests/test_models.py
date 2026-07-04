from apps.payments.models import PaymentStatus, PayoutStatus


class TestPaymentModel:
    def test_str(self, payment):
        assert "ORD-" in str(payment)
        assert "PROCESSING" in str(payment)

    def test_default_currency(self, payment):
        assert payment.currency == "gbp"

    def test_stores_stripe_intent_id(self, payment):
        from apps.payments.tests.conftest import FAKE_INTENT_ID

        assert payment.stripe_payment_intent_id == FAKE_INTENT_ID

    def test_stores_client_secret(self, payment):
        from apps.payments.tests.conftest import FAKE_CLIENT_SECRET

        assert payment.stripe_client_secret == FAKE_CLIENT_SECRET

    def test_amount_matches_order(self, payment, placed_order):
        assert payment.amount == placed_order.total_amount

    def test_status_processing_on_creation(self, payment):
        assert payment.status == PaymentStatus.PROCESSING


class TestPayoutModel:
    def test_str(self, succeeded_payment):
        from apps.payments.models import Payout

        payout = Payout.objects.first()
        assert payout is not None
        assert "PENDING" in str(payout)

    def test_net_amount_is_gross_minus_fee(self, succeeded_payment):
        from apps.payments.models import Payout

        payout = Payout.objects.first()
        assert payout.net_amount == payout.gross_amount - payout.platform_fee

    def test_default_status_pending(self, succeeded_payment):
        from apps.payments.models import Payout

        payout = Payout.objects.first()
        assert payout.status == PayoutStatus.PENDING
