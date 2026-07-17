"""Real-thread concurrency tests for the order/stock/discount race fixes.

These fire two ``place_order`` transactions simultaneously (a barrier syncs them into the
critical section) and assert exactly one wins. They need real PostgreSQL row locking, so
they skip on sqlite — run them against the Postgres CI service (or a local Postgres).
"""

from decimal import Decimal

import pytest

from apps.inventory.models import StockLevel
from apps.orders import services
from apps.orders.models import DiscountCode, DiscountRedemption, DiscountType
from apps.orders.tests.conftest import SHIPPING


@pytest.mark.django_db(transaction=True)
class TestStockReservationRace:
    def test_no_oversell_on_last_unit(self, requires_postgres, run_concurrently, buyer, variant):
        StockLevel.objects.filter(variant=variant).update(quantity_available=1, quantity_reserved=0)

        def buy():
            return services.place_order(buyer, [{"variant": variant, "quantity": 1}], SHIPPING)

        results = run_concurrently(buy, 2)
        oks = [r for r in results if r[0] == "ok"]
        errs = [r for r in results if r[0] == "error"]

        assert len(oks) == 1  # exactly one buyer got the last unit
        assert len(errs) == 1
        assert "Insufficient" in str(errs[0][1])

        level = StockLevel.objects.get(variant=variant)
        assert level.quantity_available == 0
        assert level.quantity_reserved == 1  # never oversold


@pytest.mark.django_db(transaction=True)
class TestDiscountUsageLimitRace:
    def test_global_limit_not_exceeded(self, requires_postgres, run_concurrently, buyer, variant):
        DiscountCode.objects.create(
            code="ONCE",
            discount_type=DiscountType.PERCENTAGE,
            value=Decimal("10"),
            max_uses=1,
        )
        StockLevel.objects.filter(variant=variant).update(
            quantity_available=50, quantity_reserved=0
        )

        def buy():
            return services.place_order(
                buyer, [{"variant": variant, "quantity": 1}], SHIPPING, discount_code="ONCE"
            )

        results = run_concurrently(buy, 2)
        oks = [r for r in results if r[0] == "ok"]
        errs = [r for r in results if r[0] == "error"]

        assert len(oks) == 1  # code redeemed exactly once despite the tie
        assert len(errs) == 1
        assert "usage limit" in str(errs[0][1])
        assert DiscountRedemption.objects.filter(code__code="ONCE").count() == 1
