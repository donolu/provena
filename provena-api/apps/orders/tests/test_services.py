from decimal import Decimal

import pytest

from apps.inventory.models import StockLevel
from apps.orders import services
from apps.orders.models import OrderStatus
from apps.orders.tests.conftest import SHIPPING


class TestPlaceOrder:
    def test_creates_order(self, buyer, variant):
        order = services.place_order(buyer, [{"variant": variant, "quantity": 3}], SHIPPING)
        assert order.buyer == buyer
        assert order.reference.startswith("ORD-")
        assert order.total_amount == variant.price * 3

    def test_creates_sub_order_per_supplier(self, buyer, variant):
        order = services.place_order(buyer, [{"variant": variant, "quantity": 1}], SHIPPING)
        assert order.sub_orders.count() == 1

    def test_multi_supplier_creates_multiple_sub_orders(self, buyer, variant, second_variant):
        order = services.place_order(
            buyer,
            [
                {"variant": variant, "quantity": 1},
                {"variant": second_variant, "quantity": 2},
            ],
            SHIPPING,
        )
        assert order.sub_orders.count() == 2

    def test_reserves_stock(self, buyer, variant):
        services.place_order(buyer, [{"variant": variant, "quantity": 5}], SHIPPING)
        level = StockLevel.objects.get(variant=variant)
        assert level.quantity_available == 95
        assert level.quantity_reserved == 5

    def test_insufficient_stock_raises(self, buyer, variant):
        with pytest.raises(ValueError, match="Insufficient"):
            services.place_order(buyer, [{"variant": variant, "quantity": 999}], SHIPPING)

    def test_stock_not_modified_on_failure(self, buyer, variant):
        try:
            services.place_order(buyer, [{"variant": variant, "quantity": 999}], SHIPPING)
        except ValueError:
            pass
        level = StockLevel.objects.get(variant=variant)
        assert level.quantity_available == 100

    def test_empty_items_raises(self, buyer):
        with pytest.raises(ValueError, match="at least one item"):
            services.place_order(buyer, [], SHIPPING)

    def test_snapshots_price_at_order_time(self, buyer, variant):
        original_price = variant.price
        order = services.place_order(buyer, [{"variant": variant, "quantity": 1}], SHIPPING)
        # Change price after order
        variant.price = Decimal("99.99")
        variant.save()
        item = order.sub_orders.first().items.first()
        assert item.unit_price == original_price

    def test_inactive_variant_raises(self, buyer, variant):
        variant.is_active = False
        variant.save()
        with pytest.raises(ValueError, match="not available"):
            services.place_order(buyer, [{"variant": variant, "quantity": 1}], SHIPPING)


class TestConfirmSubOrder:
    def test_confirms_pending(self, sub_order):
        sub = services.confirm_sub_order(sub_order)
        assert sub.status == OrderStatus.CONFIRMED

    def test_syncs_order_to_confirmed(self, sub_order):
        sub = services.confirm_sub_order(sub_order)
        sub.order.refresh_from_db()
        assert sub.order.status == OrderStatus.CONFIRMED

    def test_cannot_confirm_already_confirmed(self, sub_order):
        services.confirm_sub_order(sub_order)
        with pytest.raises(ValueError, match="CONFIRMED"):
            services.confirm_sub_order(sub_order)


class TestDispatchSubOrder:
    def test_dispatches_pending(self, sub_order):
        sub = services.dispatch_sub_order(sub_order, tracking_number="TRK-001")
        assert sub.status == OrderStatus.DISPATCHED
        assert sub.tracking_number == "TRK-001"

    def test_dispatches_confirmed(self, sub_order):
        services.confirm_sub_order(sub_order)
        sub = services.dispatch_sub_order(sub_order)
        assert sub.status == OrderStatus.DISPATCHED

    def test_removes_from_reserved(self, sub_order, variant):
        services.dispatch_sub_order(sub_order)
        level = StockLevel.objects.get(variant=variant)
        assert level.quantity_reserved == 0

    def test_syncs_order_to_dispatched(self, sub_order):
        services.dispatch_sub_order(sub_order)
        sub_order.order.refresh_from_db()
        assert sub_order.order.status == OrderStatus.DISPATCHED

    def test_cannot_dispatch_delivered(self, sub_order):
        services.dispatch_sub_order(sub_order)
        services.deliver_sub_order(sub_order)
        with pytest.raises(ValueError, match="DELIVERED"):
            services.dispatch_sub_order(sub_order)


class TestDeliverSubOrder:
    def test_delivers_dispatched(self, dispatched_sub_order):
        sub = services.deliver_sub_order(dispatched_sub_order)
        assert sub.status == OrderStatus.DELIVERED

    def test_syncs_order_to_delivered(self, dispatched_sub_order):
        services.deliver_sub_order(dispatched_sub_order)
        dispatched_sub_order.order.refresh_from_db()
        assert dispatched_sub_order.order.status == OrderStatus.DELIVERED

    def test_cannot_deliver_pending(self, sub_order):
        with pytest.raises(ValueError, match="PENDING"):
            services.deliver_sub_order(sub_order)


class TestCancelSubOrder:
    def test_cancels_pending(self, sub_order, variant):
        services.cancel_sub_order(sub_order)
        sub_order.refresh_from_db()
        assert sub_order.status == OrderStatus.CANCELLED

    def test_releases_stock_on_cancel(self, sub_order, variant):
        services.cancel_sub_order(sub_order)
        level = StockLevel.objects.get(variant=variant)
        assert level.quantity_available == 100
        assert level.quantity_reserved == 0

    def test_syncs_order_to_cancelled(self, sub_order):
        services.cancel_sub_order(sub_order)
        sub_order.order.refresh_from_db()
        assert sub_order.order.status == OrderStatus.CANCELLED

    def test_cannot_cancel_delivered(self, dispatched_sub_order):
        services.deliver_sub_order(dispatched_sub_order)
        with pytest.raises(ValueError, match="delivered"):
            services.cancel_sub_order(dispatched_sub_order)

    def test_idempotent_on_already_cancelled(self, sub_order):
        services.cancel_sub_order(sub_order)
        sub = services.cancel_sub_order(sub_order)
        assert sub.status == OrderStatus.CANCELLED


class TestCancelOrder:
    def test_cancels_all_sub_orders(self, placed_order):
        services.cancel_order(placed_order)
        placed_order.refresh_from_db()
        assert placed_order.status == OrderStatus.CANCELLED
        assert all(s.status == OrderStatus.CANCELLED for s in placed_order.sub_orders.all())

    def test_cannot_cancel_delivered_order(self, dispatched_sub_order):
        services.deliver_sub_order(dispatched_sub_order)
        with pytest.raises(ValueError, match="delivered"):
            services.cancel_order(dispatched_sub_order.order)
