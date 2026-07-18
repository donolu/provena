from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.delivery import services as delivery_services
from apps.delivery.models import CourierDelivery
from apps.delivery.providers import DeliveryStatus, NotServiceable, get_provider
from apps.delivery.providers.mock import MockUberDirectProvider
from apps.delivery.tests.conftest import SHIPPING, UNSERVICEABLE_SHIPPING
from apps.orders import services as order_services
from apps.orders.models import OrderStatus
from apps.payments import services as payment_services
from apps.payments.models import Payment, PaymentStatus, Payout


class TestMockProvider:
    def test_quote_fee_is_base_plus_per_item(self):
        q = MockUberDirectProvider().get_quote(pickup={}, dropoff=SHIPPING, items=[{"quantity": 2}])
        assert q.fee == Decimal("4.99")  # 3.99 + 0.50*2
        assert q.courier_cost == q.fee  # pass-through at cost
        assert q.currency == "GBP"

    def test_unserviceable_postcode_raises(self):
        with pytest.raises(NotServiceable):
            MockUberDirectProvider().get_quote(
                pickup={}, dropoff=UNSERVICEABLE_SHIPPING, items=[{"quantity": 1}]
            )

    def test_parse_status_event_maps_to_canonical(self):
        provider = MockUberDirectProvider()
        payload = provider.simulate_event("mockd_x", "delivered")
        assert provider.parse_status_event(payload) == ("mockd_x", DeliveryStatus.DELIVERED)


@pytest.mark.django_db
class TestCourierCheckout:
    def test_quote_becomes_shipping_and_records_delivery(self, courier_buyer, platform_variant):
        order = order_services.place_order(
            courier_buyer, [{"variant": platform_variant, "quantity": 2}], SHIPPING
        )
        sub = order.sub_orders.first()
        # goods 20.00 + courier fee 4.99
        assert sub.shipping_amount == Decimal("4.99")
        assert order.total_amount == Decimal("24.99")
        cd = CourierDelivery.objects.get(sub_order=sub)
        assert cd.status == DeliveryStatus.QUOTED
        assert cd.fee_charged == Decimal("4.99")
        assert cd.courier_cost == Decimal("4.99")

    def test_unserviceable_address_blocks_checkout(self, courier_buyer, platform_variant):
        with pytest.raises(ValueError, match="not available"):
            order_services.place_order(
                courier_buyer,
                [{"variant": platform_variant, "quantity": 1}],
                UNSERVICEABLE_SHIPPING,
            )

    def test_expired_quote_rejected_at_payment(self, courier_buyer, platform_variant):
        order = order_services.place_order(
            courier_buyer, [{"variant": platform_variant, "quantity": 1}], SHIPPING
        )
        CourierDelivery.objects.filter(sub_order__order=order).update(
            quote_expires_at="2000-01-01T00:00:00Z"
        )
        with pytest.raises(ValueError, match="expired"):
            payment_services.create_payment_intent(order)


@pytest.mark.django_db
class TestCourierDispatchAndWebhook:
    def _paid_dispatched(self, buyer, variant, django_capture_on_commit_callbacks):
        order = order_services.place_order(buyer, [{"variant": variant, "quantity": 2}], SHIPPING)
        payment = Payment.objects.create(
            order=order,
            stripe_payment_intent_id="pi_courier",
            amount=order.total_amount,
            status=PaymentStatus.SUCCEEDED,
        )
        payment_services._create_payouts(payment)  # goods-only payout (excludes courier fee)
        sub = order.sub_orders.first()
        with django_capture_on_commit_callbacks(execute=True):
            order_services.dispatch_sub_order(sub)  # books the courier on commit
        sub.refresh_from_db()
        return order, sub

    def test_dispatch_books_the_courier(
        self, courier_buyer, platform_variant, django_capture_on_commit_callbacks
    ):
        _, sub = self._paid_dispatched(
            courier_buyer, platform_variant, django_capture_on_commit_callbacks
        )
        cd = CourierDelivery.objects.get(sub_order=sub)
        assert cd.status == DeliveryStatus.BOOKED
        assert cd.provider_delivery_id
        assert cd.tracking_url

    def test_delivered_webhook_marks_delivered_and_pays_out(
        self, courier_buyer, platform_variant, django_capture_on_commit_callbacks
    ):
        _order, sub = self._paid_dispatched(
            courier_buyer, platform_variant, django_capture_on_commit_callbacks
        )
        cd = CourierDelivery.objects.get(sub_order=sub)
        payload = get_provider().simulate_event(cd.provider_delivery_id, "delivered")
        # Do not execute on_commit callbacks: deliver_sub_order registers a payout-trigger task we
        # don't want to run here (it would call Stripe). The status change itself is synchronous.
        delivery_services.handle_status_event(payload)

        sub.refresh_from_db()
        cd.refresh_from_db()
        assert cd.status == DeliveryStatus.DELIVERED
        assert sub.status == OrderStatus.DELIVERED
        # Payout excludes the platform delivery fee (goods only).
        payout = Payout.objects.get(sub_order=sub)
        assert payout.gross_amount == Decimal("20.00")

    def test_failed_webhook_refunds_delivery_fee(
        self, courier_buyer, platform_variant, django_capture_on_commit_callbacks
    ):
        _order, sub = self._paid_dispatched(
            courier_buyer, platform_variant, django_capture_on_commit_callbacks
        )
        cd = CourierDelivery.objects.get(sub_order=sub)
        payload = get_provider().simulate_event(cd.provider_delivery_id, "failed")
        with patch("stripe.PaymentIntent.retrieve") as pi, patch("stripe.Refund.create") as refund:
            pi.return_value.latest_charge = "ch_x"
            refund.return_value.id = "re_x"
            delivery_services.handle_status_event(payload)

        cd.refresh_from_db()
        assert cd.status == DeliveryStatus.FAILED
        # The buyer's delivery fee (4.99) was refunded.
        assert refund.call_args[1]["amount"] == 499


@pytest.mark.django_db
class TestReconciliation:
    def test_summary_sums_fees_and_costs(self, courier_buyer, platform_variant):
        order_services.place_order(
            courier_buyer, [{"variant": platform_variant, "quantity": 2}], SHIPPING
        )
        summary = delivery_services.reconciliation_summary()
        assert summary["fee_charged_total"] == "4.99"
        assert summary["courier_cost_total"] == "4.99"  # pass-through parity
