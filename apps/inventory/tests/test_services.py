from datetime import date

import pytest

from apps.inventory import services
from apps.inventory.models import MovementType


class TestGetOrCreateStockLevel:
    def test_creates_when_absent(self, variant):
        level = services.get_or_create_stock_level(variant)
        assert level.variant == variant
        assert level.quantity_available == 0

    def test_returns_existing(self, stock_level, variant):
        level = services.get_or_create_stock_level(variant)
        assert level.id == stock_level.id


class TestReceiveStock:
    def test_increases_available(self, variant):
        level, _, _ = services.receive_stock(variant, 100)
        assert level.quantity_available == 100

    def test_creates_lot(self, variant):
        _, lot, _ = services.receive_stock(variant, 50, lot_number="LOT-B", notes="First batch")
        assert lot.lot_number == "LOT-B"
        assert lot.quantity_received == 50
        assert lot.quantity_remaining == 50

    def test_creates_inbound_movement(self, variant, admin_user):
        _, _, movement = services.receive_stock(variant, 30, performed_by=admin_user)
        assert movement.movement_type == MovementType.INBOUND
        assert movement.quantity == 30
        assert movement.quantity_after == 30
        assert movement.performed_by == admin_user

    def test_cumulative_receives(self, variant):
        services.receive_stock(variant, 20)
        level, _, _ = services.receive_stock(variant, 30)
        assert level.quantity_available == 50

    def test_zero_quantity_raises(self, variant):
        with pytest.raises(ValueError, match="positive"):
            services.receive_stock(variant, 0)

    def test_negative_quantity_raises(self, variant):
        with pytest.raises(ValueError, match="positive"):
            services.receive_stock(variant, -5)

    def test_with_expiry_date(self, variant):
        _, lot, _ = services.receive_stock(variant, 10, expires_at=date(2026, 12, 31))
        assert lot.expires_at == date(2026, 12, 31)


class TestAdjustStock:
    def test_positive_delta(self, stock_level, variant):
        level, movement = services.adjust_stock(variant, 10, notes="Found extra")
        assert level.quantity_available == 60
        assert movement.movement_type == MovementType.ADJUSTMENT
        assert movement.quantity == 10

    def test_negative_delta(self, stock_level, variant):
        level, movement = services.adjust_stock(variant, -20, notes="Damaged goods")
        assert level.quantity_available == 30
        assert movement.quantity == -20

    def test_adjustment_to_zero(self, stock_level, variant):
        level, _ = services.adjust_stock(variant, -50, notes="Stock write-off")
        assert level.quantity_available == 0

    def test_adjustment_below_zero_raises(self, stock_level, variant):
        with pytest.raises(ValueError, match="negative"):
            services.adjust_stock(variant, -51, notes="Too much")

    def test_zero_delta_raises(self, variant):
        with pytest.raises(ValueError, match="zero"):
            services.adjust_stock(variant, 0, notes="Nothing")


class TestSetLowStockThreshold:
    def test_sets_threshold(self, variant):
        level = services.set_low_stock_threshold(variant, 15)
        assert level.low_stock_threshold == 15

    def test_zero_is_valid(self, variant):
        level = services.set_low_stock_threshold(variant, 0)
        assert level.low_stock_threshold == 0

    def test_negative_raises(self, variant):
        with pytest.raises(ValueError, match="negative"):
            services.set_low_stock_threshold(variant, -1)


class TestReserveStock:
    def test_moves_available_to_reserved(self, stock_level, variant):
        level, movement = services.reserve_stock(variant, 10)
        assert level.quantity_available == 40
        assert level.quantity_reserved == 10
        assert movement.movement_type == MovementType.RESERVED
        assert movement.quantity == -10

    def test_insufficient_stock_raises(self, stock_level, variant):
        with pytest.raises(ValueError, match="Insufficient"):
            services.reserve_stock(variant, 100)

    def test_reserves_with_reference(self, stock_level, variant):
        _, movement = services.reserve_stock(variant, 5, reference="ORD-123")
        assert movement.reference == "ORD-123"

    def test_zero_quantity_raises(self, variant):
        with pytest.raises(ValueError, match="positive"):
            services.reserve_stock(variant, 0)


class TestReleaseReservation:
    def test_moves_reserved_to_available(self, stock_level, variant):
        services.reserve_stock(variant, 10)
        level, movement = services.release_reservation(variant, 10)
        assert level.quantity_available == 50
        assert level.quantity_reserved == 0
        assert movement.movement_type == MovementType.UNRESERVED

    def test_release_more_than_reserved_raises(self, stock_level, variant):
        with pytest.raises(ValueError, match="Cannot release"):
            services.release_reservation(variant, 1)


class TestDispatchStock:
    def test_removes_from_reserved(self, stock_level, variant):
        services.reserve_stock(variant, 10)
        level, movement = services.dispatch_stock(variant, 10, reference="ORD-456")
        assert level.quantity_reserved == 0
        assert movement.movement_type == MovementType.OUTBOUND
        assert movement.quantity == -10

    def test_dispatch_more_than_reserved_raises(self, stock_level, variant):
        with pytest.raises(ValueError, match="Cannot dispatch"):
            services.dispatch_stock(variant, 5)

    def test_zero_quantity_raises(self, variant):
        with pytest.raises(ValueError, match="positive"):
            services.dispatch_stock(variant, 0)


class TestReturnStock:
    def test_adds_to_available(self, stock_level, variant, admin_user):
        level, movement = services.return_stock(
            variant, 5, notes="Customer return", performed_by=admin_user
        )
        assert level.quantity_available == 55
        assert movement.movement_type == MovementType.RETURN
        assert movement.quantity == 5
        assert movement.performed_by == admin_user

    def test_zero_quantity_raises(self, variant):
        with pytest.raises(ValueError, match="positive"):
            services.return_stock(variant, 0)


class TestLowStockSignal:
    def test_signal_fired_when_stock_drops_below_threshold(self, stock_level, variant):
        from unittest.mock import MagicMock

        from apps.inventory.signals import low_stock_alert

        handler = MagicMock()
        low_stock_alert.connect(handler)
        try:
            stock_level.low_stock_threshold = 20
            stock_level.save()
            services.adjust_stock(variant, -40, notes="Dropped below threshold")
            handler.assert_called_once()
            kwargs = handler.call_args.kwargs
            assert kwargs["variant"] == variant
            assert kwargs["quantity_available"] == 10
        finally:
            low_stock_alert.disconnect(handler)

    def test_signal_not_fired_when_above_threshold(self, stock_level, variant):
        from unittest.mock import MagicMock

        from apps.inventory.signals import low_stock_alert

        handler = MagicMock()
        low_stock_alert.connect(handler)
        try:
            stock_level.low_stock_threshold = 5
            stock_level.save()
            services.adjust_stock(variant, -10, notes="Still above threshold")
            handler.assert_not_called()
        finally:
            low_stock_alert.disconnect(handler)
