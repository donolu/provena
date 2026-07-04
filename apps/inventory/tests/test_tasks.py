import datetime

import pytest

from apps.inventory.tasks import check_lot_expiry
from apps.notifications.models import Notification


@pytest.fixture
def stock_lot(variant, approved_supplier, db):
    from apps.inventory.models import StockLot

    today = datetime.date.today()
    return StockLot.objects.create(
        variant=variant,
        lot_number="LOT-001",
        quantity_received=50,
        quantity_remaining=50,
        expires_at=today + datetime.timedelta(days=2),
    )


@pytest.fixture
def expired_lot(variant, db):
    from apps.inventory.models import StockLot

    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    return StockLot.objects.create(
        variant=variant,
        lot_number="LOT-OLD",
        quantity_received=10,
        quantity_remaining=10,
        expires_at=yesterday,
    )


@pytest.fixture
def far_future_lot(variant, db):
    from apps.inventory.models import StockLot

    future = datetime.date.today() + datetime.timedelta(days=30)
    return StockLot.objects.create(
        variant=variant,
        lot_number="LOT-FUTURE",
        quantity_received=20,
        quantity_remaining=20,
        expires_at=future,
    )


class TestCheckLotExpiry:
    def test_creates_notification_for_expiring_lot(self, stock_lot, approved_supplier):
        count = check_lot_expiry(days_ahead=3)

        assert count == 1
        notif = Notification.objects.get(recipient=approved_supplier.user)
        assert "LOT-001" in notif.title
        assert "expires in" in notif.title

    def test_ignores_already_expired_lots(self, expired_lot):
        count = check_lot_expiry(days_ahead=3)
        assert count == 0

    def test_ignores_far_future_lots(self, far_future_lot):
        count = check_lot_expiry(days_ahead=3)
        assert count == 0

    def test_idempotent_does_not_duplicate(self, stock_lot, approved_supplier):
        check_lot_expiry(days_ahead=3)
        check_lot_expiry(days_ahead=3)

        assert Notification.objects.filter(recipient=approved_supplier.user).count() == 1

    def test_ignores_lots_with_no_remaining_stock(self, variant, approved_supplier, db):
        from apps.inventory.models import StockLot

        today = datetime.date.today()
        StockLot.objects.create(
            variant=variant,
            lot_number="LOT-EMPTY",
            quantity_received=10,
            quantity_remaining=0,
            expires_at=today + datetime.timedelta(days=1),
        )

        count = check_lot_expiry(days_ahead=3)
        assert count == 0

    def test_days_ahead_parameter_controls_window(self, stock_lot, approved_supplier):
        count = check_lot_expiry(days_ahead=1)
        assert count == 0

        count = check_lot_expiry(days_ahead=3)
        assert count == 1
