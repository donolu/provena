"""Tests for the admin per-item refund: select items, refund the buyer, and reverse the
payout of the supplier that sold each item (ADR-012 refund tail)."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.inventory.models import StockLevel
from apps.orders import services
from apps.orders.models import ReturnStatus
from apps.orders.tests.conftest import SHIPPING
from apps.payments.models import Payment, PaymentStatus, Payout, PayoutStatus


def _stripe_mocks():
    intent = MagicMock()
    intent.latest_charge = "ch_test"
    return (
        patch("stripe.PaymentIntent.retrieve", return_value=intent),
        patch("stripe.Refund.create", return_value=MagicMock(id="re_test")),
        patch("stripe.Transfer.create_reversal", return_value=MagicMock(id="trr_test")),
    )


def _pay(order):
    return Payment.objects.create(
        order=order,
        stripe_payment_intent_id=f"pi_{order.reference}",
        amount=order.total_amount,
        status=PaymentStatus.SUCCEEDED,
    )


def _paid_payout(sub, *, net, transfer_id):
    return Payout.objects.create(
        sub_order=sub,
        supplier=sub.supplier,
        gross_amount=sub.subtotal,
        platform_fee=sub.subtotal - net,
        net_amount=net,
        status=PayoutStatus.PAID,
        stripe_transfer_id=transfer_id,
    )


@pytest.mark.django_db
class TestAdminItemRefundService:
    def test_refunds_item_and_reverses_only_selling_supplier(self, buyer, variant, second_variant):
        # Two suppliers on one order; refund an item sold by supplier A only.
        order = services.place_order(
            buyer,
            [{"variant": variant, "quantity": 2}, {"variant": second_variant, "quantity": 2}],
            SHIPPING,
        )
        _pay(order)
        sub_a = order.sub_orders.get(supplier=variant.product.supplier)
        sub_b = order.sub_orders.get(supplier=second_variant.product.supplier)
        payout_a = _paid_payout(sub_a, net=Decimal("7.00"), transfer_id="tr_a")
        payout_b = _paid_payout(sub_b, net=Decimal("4.50"), transfer_id="tr_b")
        item_a = sub_a.items.first()

        pi, refund, reversal = _stripe_mocks()
        with pi, refund as mock_refund, reversal as mock_reversal:
            returns = services.admin_refund_order_items(
                order,
                [{"order_item": item_a, "quantity": 1}],
                raised_by=None,
                reason="Damaged on arrival",
            )

        assert len(returns) == 1
        assert returns[0].sub_order_id == sub_a.id
        assert returns[0].status == ReturnStatus.REFUNDED
        # One unit of a £3.99 item, goods-only for a partial selection.
        assert returns[0].refund_amount == Decimal("3.99")
        mock_refund.assert_called_once()
        assert mock_refund.call_args[1]["amount"] == 399

        # Only supplier A's payout is reversed; B is untouched.
        mock_reversal.assert_called_once()
        assert mock_reversal.call_args[0][0] == "tr_a"
        payout_a.refresh_from_db()
        payout_b.refresh_from_db()
        assert payout_a.status == PayoutStatus.REVERSED
        assert payout_b.status == PayoutStatus.PAID

    def test_multi_supplier_selection_refunds_each(self, buyer, variant, second_variant):
        order = services.place_order(
            buyer,
            [{"variant": variant, "quantity": 1}, {"variant": second_variant, "quantity": 1}],
            SHIPPING,
        )
        _pay(order)
        sub_a = order.sub_orders.get(supplier=variant.product.supplier)
        sub_b = order.sub_orders.get(supplier=second_variant.product.supplier)
        _paid_payout(sub_a, net=Decimal("3.50"), transfer_id="tr_a")
        _paid_payout(sub_b, net=Decimal("2.20"), transfer_id="tr_b")

        pi, refund, reversal = _stripe_mocks()
        with pi, refund as mock_refund, reversal as mock_reversal:
            returns = services.admin_refund_order_items(
                order,
                [
                    {"order_item": sub_a.items.first(), "quantity": 1},
                    {"order_item": sub_b.items.first(), "quantity": 1},
                ],
                raised_by=None,
            )

        assert len(returns) == 2
        assert all(r.status == ReturnStatus.REFUNDED for r in returns)
        assert mock_refund.call_count == 2
        assert mock_reversal.call_count == 2

    def test_restocks_refunded_units(self, buyer, variant):
        order = services.place_order(buyer, [{"variant": variant, "quantity": 2}], SHIPPING)
        _pay(order)
        sub = order.sub_orders.first()
        _paid_payout(sub, net=Decimal("7.00"), transfer_id="tr_a")
        before = StockLevel.objects.get(variant=variant).quantity_available

        pi, refund, reversal = _stripe_mocks()
        with pi, refund, reversal:
            services.admin_refund_order_items(
                order, [{"order_item": sub.items.first(), "quantity": 1}], raised_by=None
            )

        after = StockLevel.objects.get(variant=variant).quantity_available
        assert after == before + 1

    def test_not_gated_on_delivery_status(self, buyer, variant):
        # A buyer return needs a delivered sub-order in the window; an admin refund does not.
        order = services.place_order(buyer, [{"variant": variant, "quantity": 1}], SHIPPING)
        _pay(order)
        sub = order.sub_orders.first()
        assert sub.status == "PENDING"
        _paid_payout(sub, net=Decimal("3.50"), transfer_id="tr_a")

        pi, refund, reversal = _stripe_mocks()
        with pi, refund, reversal:
            returns = services.admin_refund_order_items(
                order, [{"order_item": sub.items.first(), "quantity": 1}], raised_by=None
            )
        assert returns[0].status == ReturnStatus.REFUNDED

    def test_rejects_over_quantity(self, buyer, variant):
        order = services.place_order(buyer, [{"variant": variant, "quantity": 1}], SHIPPING)
        _pay(order)
        sub = order.sub_orders.first()
        with pytest.raises(ValueError, match="remain refundable"):
            services.admin_refund_order_items(
                order, [{"order_item": sub.items.first(), "quantity": 5}], raised_by=None
            )

    def test_rejects_item_from_other_order(self, buyer, variant):
        order = services.place_order(buyer, [{"variant": variant, "quantity": 1}], SHIPPING)
        other = services.place_order(buyer, [{"variant": variant, "quantity": 1}], SHIPPING)
        _pay(order)
        foreign_item = other.sub_orders.first().items.first()
        with pytest.raises(ValueError, match="does not belong to this order"):
            services.admin_refund_order_items(
                order, [{"order_item": foreign_item, "quantity": 1}], raised_by=None
            )

    def test_empty_selection_rejected(self, buyer, variant):
        order = services.place_order(buyer, [{"variant": variant, "quantity": 1}], SHIPPING)
        with pytest.raises(ValueError, match="at least one item"):
            services.admin_refund_order_items(order, [], raised_by=None)


@pytest.mark.django_db
class TestAdminItemRefundEndpoint:
    def _url(self, order):
        return f"/api/v1/orders/admin/{order.reference}/refund-items/"

    def test_admin_can_refund_items(self, admin_client, buyer, variant):
        order = services.place_order(buyer, [{"variant": variant, "quantity": 2}], SHIPPING)
        _pay(order)
        sub = order.sub_orders.first()
        _paid_payout(sub, net=Decimal("7.00"), transfer_id="tr_a")
        item = sub.items.first()

        pi, refund, reversal = _stripe_mocks()
        with pi, refund, reversal:
            res = admin_client.post(
                self._url(order),
                {"items": [{"order_item_id": str(item.id), "quantity": 1}], "reason": "Faulty"},
                format="json",
            )
        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["status"] == ReturnStatus.REFUNDED
        assert res.data[0]["refund_amount"] == "3.99"

    def test_non_admin_forbidden(self, buyer_client, buyer, variant):
        order = services.place_order(buyer, [{"variant": variant, "quantity": 1}], SHIPPING)
        sub = order.sub_orders.first()
        res = buyer_client.post(
            self._url(order),
            {"items": [{"order_item_id": str(sub.items.first().id), "quantity": 1}]},
            format="json",
        )
        assert res.status_code == 403

    def test_item_from_other_order_400(self, admin_client, buyer, variant):
        order = services.place_order(buyer, [{"variant": variant, "quantity": 1}], SHIPPING)
        other = services.place_order(buyer, [{"variant": variant, "quantity": 1}], SHIPPING)
        _pay(order)
        foreign_item = other.sub_orders.first().items.first()
        res = admin_client.post(
            self._url(order),
            {"items": [{"order_item_id": str(foreign_item.id), "quantity": 1}]},
            format="json",
        )
        assert res.status_code == 400

    def test_empty_items_400(self, admin_client, buyer, variant):
        order = services.place_order(buyer, [{"variant": variant, "quantity": 1}], SHIPPING)
        res = admin_client.post(self._url(order), {"items": []}, format="json")
        assert res.status_code == 400
