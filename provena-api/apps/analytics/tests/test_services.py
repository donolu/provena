from datetime import timedelta
from decimal import Decimal

from apps.analytics import services
from apps.orders.models import OrderStatus


class TestSalesSummary:
    def test_returns_expected_keys(self, placed_order, today):
        result = services.sales_summary(today - timedelta(days=1), today + timedelta(days=1))
        assert "total_revenue" in result
        assert "total_orders" in result
        assert "total_items_sold" in result
        assert "avg_order_value" in result
        assert "cancelled_orders" in result
        assert "refunded_amount" in result

    def test_counts_placed_orders(self, placed_order, today):
        result = services.sales_summary(today - timedelta(days=1), today + timedelta(days=1))
        assert result["total_orders"] == 1
        assert Decimal(result["total_revenue"]) == Decimal("5.00")

    def test_excludes_cancelled_from_revenue(self, placed_order, today):
        placed_order.status = OrderStatus.CANCELLED
        placed_order.save()
        result = services.sales_summary(today - timedelta(days=1), today + timedelta(days=1))
        assert result["total_orders"] == 0
        assert Decimal(result["total_revenue"]) == Decimal("0.00")
        assert result["cancelled_orders"] == 1

    def test_counts_items_sold(self, placed_order, today):
        result = services.sales_summary(today - timedelta(days=1), today + timedelta(days=1))
        assert result["total_items_sold"] == 2

    def test_empty_range_returns_zeros(self, db, today):
        past = today - timedelta(days=10)
        result = services.sales_summary(past - timedelta(days=1), past)
        assert result["total_orders"] == 0
        assert Decimal(result["total_revenue"]) == Decimal("0.00")

    def test_uses_default_date_range_when_none(self, placed_order):
        result = services.sales_summary()
        assert result["total_orders"] >= 1

    def test_filter_by_supplier(self, placed_order, approved_supplier, today):
        result = services.sales_summary(
            today - timedelta(days=1), today + timedelta(days=1), supplier_id=approved_supplier.id
        )
        assert result["total_orders"] == 1

    def test_filter_by_wrong_supplier_returns_zero(self, placed_order, today):
        from django.contrib.auth import get_user_model

        from apps.suppliers.models import Supplier, SupplierStatus

        User = get_user_model()
        other_user = User.objects.create_user(email="other@example.com", password="x")
        other_supplier = Supplier.objects.create(
            user=other_user,
            business_name="Other Co",
            slug="other-co",
            status=SupplierStatus.APPROVED,
        )
        result = services.sales_summary(
            today - timedelta(days=1), today + timedelta(days=1), supplier_id=other_supplier.id
        )
        assert result["total_orders"] == 0


class TestRevenueOverTime:
    def test_returns_list(self, placed_order, today):
        result = services.revenue_over_time(
            today - timedelta(days=1), today + timedelta(days=1), "day"
        )
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "period" in result[0]
        assert "revenue" in result[0]
        assert "order_count" in result[0]

    def test_granularity_week(self, placed_order, today):
        result = services.revenue_over_time(
            today - timedelta(days=7), today + timedelta(days=1), "week"
        )
        assert isinstance(result, list)

    def test_granularity_month(self, placed_order, today):
        result = services.revenue_over_time(
            today - timedelta(days=30), today + timedelta(days=1), "month"
        )
        assert isinstance(result, list)

    def test_cancelled_excluded(self, placed_order, today):
        placed_order.status = OrderStatus.CANCELLED
        placed_order.save()
        result = services.revenue_over_time(
            today - timedelta(days=1), today + timedelta(days=1), "day"
        )
        assert result == []


class TestTopProducts:
    def test_returns_list(self, placed_order, today):
        result = services.top_products(today - timedelta(days=1), today + timedelta(days=1))
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["variant_sku"] == "CARR-1KG"
        assert result[0]["units_sold"] == 2
        assert Decimal(result[0]["revenue"]) == Decimal("5.00")

    def test_limit_respected(self, placed_order, today):
        result = services.top_products(
            today - timedelta(days=1), today + timedelta(days=1), limit=1
        )
        assert len(result) <= 1

    def test_empty_returns_empty_list(self, db, today):
        past = today - timedelta(days=10)
        result = services.top_products(past - timedelta(days=1), past)
        assert result == []


class TestSupplierPerformance:
    def test_returns_list_with_supplier(self, placed_order, approved_supplier, today):
        result = services.supplier_performance(today - timedelta(days=1), today + timedelta(days=1))
        assert len(result) == 1
        assert result[0]["supplier_name"] == "Fresh Farms"
        assert Decimal(result[0]["total_revenue"]) == Decimal("5.00")

    def test_pending_payout_included(self, placed_order, payout, approved_supplier, today):
        result = services.supplier_performance(today - timedelta(days=1), today + timedelta(days=1))
        assert Decimal(result[0]["pending_payout"]) == Decimal("4.50")


class TestSupplierOwnSummary:
    def test_returns_own_summary(self, placed_order, approved_supplier, today):
        result = services.supplier_own_summary(
            approved_supplier, today - timedelta(days=1), today + timedelta(days=1)
        )
        assert Decimal(result["total_revenue"]) == Decimal("5.00")
        assert result["sub_order_count"] == 1

    def test_payout_totals(self, placed_order, payout, approved_supplier):
        result = services.supplier_own_summary(approved_supplier)
        assert Decimal(result["pending_payout"]) == Decimal("4.50")
        assert Decimal(result["paid_payout"]) == Decimal("0.00")


class TestInventoryHealth:
    def test_returns_counts(self, variant):
        result = services.inventory_health()
        assert "total_variants" in result
        assert result["total_variants"] >= 1
        assert "low_stock_count" in result
        assert "out_of_stock_count" in result

    def test_out_of_stock_counted(self, variant):
        from apps.inventory.models import StockLevel

        level = StockLevel.objects.get(variant=variant)
        level.quantity_available = 0
        level.save()
        result = services.inventory_health()
        assert result["out_of_stock_count"] >= 1


class TestReviewsSummary:
    def test_returns_summary_keys(self, db):
        result = services.reviews_summary()
        assert "total_reviews" in result
        assert "approved_reviews" in result
        assert "pending_reviews" in result
        assert "verified_purchase_count" in result
        assert "avg_rating" in result

    def test_counts_reviews(self, variant, buyer):
        from apps.marketplace.models import Review

        Review.objects.create(
            variant=variant, reviewer=buyer, rating=4, title="Good", body="Nice", is_approved=True
        )
        result = services.reviews_summary()
        assert result["total_reviews"] == 1
        assert result["approved_reviews"] == 1
        assert result["pending_reviews"] == 0
        assert result["avg_rating"] == 4.0

    def test_pending_reviews_counted(self, variant, buyer):
        from apps.marketplace.models import Review

        Review.objects.create(
            variant=variant, reviewer=buyer, rating=3, title="OK", body="Fine", is_approved=False
        )
        result = services.reviews_summary()
        assert result["pending_reviews"] == 1
        assert result["avg_rating"] is None

    def test_filter_by_variant(self, variant, buyer):
        from apps.marketplace.models import Review

        Review.objects.create(
            variant=variant,
            reviewer=buyer,
            rating=5,
            title="Great",
            body="Love it",
            is_approved=True,
        )
        result = services.reviews_summary(variant_id=variant.id)
        assert result["total_reviews"] == 1


class TestPayoutsSummary:
    def test_returns_status_totals(self, payout):
        result = services.payouts_summary()
        assert Decimal(result["pending"]) == Decimal("4.50")
        assert Decimal(result["paid"]) == Decimal("0.00")

    def test_filter_by_supplier(self, payout, approved_supplier):
        result = services.payouts_summary(supplier=approved_supplier)
        assert Decimal(result["pending"]) == Decimal("4.50")
