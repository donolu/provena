from decimal import Decimal

from rest_framework.test import APIClient


class TestSalesSummaryView:
    def test_returns_200(self, admin_client, placed_order):
        response = admin_client.get("/api/v1/analytics/sales/summary/")
        assert response.status_code == 200
        data = response.json()
        assert "total_revenue" in data
        assert "total_orders" in data

    def test_requires_admin(self, supplier_client):
        response = supplier_client.get("/api/v1/analytics/sales/summary/")
        assert response.status_code == 403

    def test_unauthenticated(self):
        response = APIClient().get("/api/v1/analytics/sales/summary/")
        assert response.status_code == 401

    def test_date_filter(self, admin_client, placed_order, today):
        response = admin_client.get(
            f"/api/v1/analytics/sales/summary/?from_date={today}&to_date={today}"
        )
        assert response.status_code == 200

    def test_supplier_filter(self, admin_client, placed_order, approved_supplier):
        response = admin_client.get(
            f"/api/v1/analytics/sales/summary/?supplier_id={approved_supplier.id}"
        )
        assert response.status_code == 200
        assert response.json()["total_orders"] == 1


class TestRevenueOverTimeView:
    def test_returns_list(self, admin_client, placed_order):
        response = admin_client.get("/api/v1/analytics/sales/over-time/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_granularity_param(self, admin_client, placed_order):
        for granularity in ("day", "week", "month"):
            response = admin_client.get(
                f"/api/v1/analytics/sales/over-time/?granularity={granularity}"
            )
            assert response.status_code == 200

    def test_requires_admin(self, supplier_client):
        response = supplier_client.get("/api/v1/analytics/sales/over-time/")
        assert response.status_code == 403


class TestTopProductsView:
    def test_returns_list(self, admin_client, placed_order):
        response = admin_client.get("/api/v1/analytics/products/top/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["variant_sku"] == "CARR-1KG"

    def test_limit_param(self, admin_client, placed_order):
        response = admin_client.get("/api/v1/analytics/products/top/?limit=1")
        assert response.status_code == 200
        assert len(response.json()) <= 1

    def test_requires_admin(self, supplier_client):
        response = supplier_client.get("/api/v1/analytics/products/top/")
        assert response.status_code == 403


class TestSupplierPerformanceView:
    def test_returns_list(self, admin_client, placed_order, approved_supplier):
        response = admin_client.get("/api/v1/analytics/suppliers/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["supplier_name"] == "Fresh Farms"

    def test_requires_admin(self, supplier_client):
        response = supplier_client.get("/api/v1/analytics/suppliers/")
        assert response.status_code == 403


class TestInventoryHealthView:
    def test_returns_counts(self, admin_client, variant):
        response = admin_client.get("/api/v1/analytics/inventory/")
        assert response.status_code == 200
        data = response.json()
        assert data["total_variants"] >= 1
        assert "low_stock_count" in data
        assert "out_of_stock_count" in data

    def test_requires_admin(self, supplier_client):
        response = supplier_client.get("/api/v1/analytics/inventory/")
        assert response.status_code == 403


class TestReviewsSummaryView:
    def test_returns_summary(self, admin_client, db):
        response = admin_client.get("/api/v1/analytics/reviews/")
        assert response.status_code == 200
        data = response.json()
        assert "total_reviews" in data
        assert "avg_rating" in data

    def test_variant_filter(self, admin_client, variant):
        response = admin_client.get(f"/api/v1/analytics/reviews/?variant_id={variant.id}")
        assert response.status_code == 200

    def test_requires_admin(self, supplier_client):
        response = supplier_client.get("/api/v1/analytics/reviews/")
        assert response.status_code == 403


class TestPayoutsSummaryView:
    def test_returns_summary(self, admin_client, payout):
        response = admin_client.get("/api/v1/analytics/payouts/")
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["pending"]) == Decimal("4.50")

    def test_requires_admin(self, supplier_client):
        response = supplier_client.get("/api/v1/analytics/payouts/")
        assert response.status_code == 403


class TestSupplierOwnSummaryView:
    def test_returns_own_summary(self, supplier_client, approved_supplier, placed_order):
        response = supplier_client.get("/api/v1/analytics/me/summary/")
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["total_revenue"]) == Decimal("5.00")
        assert data["sub_order_count"] == 1

    def test_requires_approved_supplier(self, admin_client):
        response = admin_client.get("/api/v1/analytics/me/summary/")
        assert response.status_code == 403

    def test_unauthenticated(self):
        response = APIClient().get("/api/v1/analytics/me/summary/")
        assert response.status_code == 401


class TestSupplierPayoutsSummaryView:
    def test_returns_own_payouts(self, supplier_client, approved_supplier, payout):
        response = supplier_client.get("/api/v1/analytics/me/payouts/")
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["pending"]) == Decimal("4.50")

    def test_requires_approved_supplier(self, admin_client):
        response = admin_client.get("/api/v1/analytics/me/payouts/")
        assert response.status_code == 403


class TestAnalyticsExportView:
    def test_returns_csv_content_type(self, admin_client):
        response = admin_client.get("/api/v1/analytics/export/csv/")
        assert response.status_code == 200
        assert "text/csv" in response["Content-Type"]

    def test_csv_contains_all_sections(self, admin_client, placed_order):
        response = admin_client.get("/api/v1/analytics/export/csv/")
        content = b"".join(response.streaming_content).decode()
        assert "# revenue_over_time" in content
        assert "# top_products" in content
        assert "# supplier_performance" in content

    def test_csv_headers_present(self, admin_client):
        response = admin_client.get("/api/v1/analytics/export/csv/")
        content = b"".join(response.streaming_content).decode()
        assert "period,revenue,order_count" in content
        assert "variant_sku,product_name,units_sold,revenue" in content

    def test_filename_contains_date_range(self, admin_client):
        response = admin_client.get(
            "/api/v1/analytics/export/csv/?from_date=2024-01-01&to_date=2024-01-31"
        )
        assert response.status_code == 200
        disposition = response["Content-Disposition"]
        assert "2024-01-01" in disposition
        assert "2024-01-31" in disposition

    def test_requires_admin(self, supplier_client):
        response = supplier_client.get("/api/v1/analytics/export/csv/")
        assert response.status_code == 403

    def test_unauthenticated(self):
        response = APIClient().get("/api/v1/analytics/export/csv/")
        assert response.status_code == 401


class TestParseDatesInvalidInput:
    def test_invalid_from_date_falls_back_to_default(self, admin_client):
        response = admin_client.get(
            "/api/v1/analytics/sales/summary/?from_date=not-a-date&to_date=also-bad"
        )
        assert response.status_code == 200
        data = response.json()
        assert "from_date" in data
        assert "to_date" in data

    def test_invalid_date_on_revenue_endpoint(self, admin_client):
        response = admin_client.get("/api/v1/analytics/sales/over-time/?from_date=baddate")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
