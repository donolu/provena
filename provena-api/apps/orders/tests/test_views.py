from apps.orders.tests.conftest import SHIPPING


class TestOrderListCreate:
    def test_place_order(self, buyer_client, variant):
        response = buyer_client.post(
            "/api/v1/orders/",
            {
                "items": [{"variant_id": str(variant.id), "quantity": 2}],
                "shipping_name": "Test Buyer",
                "shipping_line1": "1 Test St",
                "shipping_city": "London",
                "shipping_postcode": "EC1A 1BB",
                "shipping_country": "GB",
            },
            format="json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "PENDING"
        assert data["reference"].startswith("ORD-")
        assert len(data["sub_orders"]) == 1
        assert data["sub_orders"][0]["items"][0]["sku"] == "CARR-1KG"

    def test_place_multi_supplier_order(self, buyer_client, variant, second_variant):
        response = buyer_client.post(
            "/api/v1/orders/",
            {
                "items": [
                    {"variant_id": str(variant.id), "quantity": 1},
                    {"variant_id": str(second_variant.id), "quantity": 2},
                ],
                "shipping_name": "Test Buyer",
                "shipping_line1": "1 Test St",
                "shipping_city": "London",
                "shipping_postcode": "EC1A 1BB",
                "shipping_country": "GB",
            },
            format="json",
        )
        assert response.status_code == 201
        assert len(response.json()["sub_orders"]) == 2

    def test_place_order_inactive_variant(self, buyer_client, variant):
        variant.is_active = False
        variant.save()
        response = buyer_client.post(
            "/api/v1/orders/",
            {
                "items": [{"variant_id": str(variant.id), "quantity": 1}],
                "shipping_name": "X",
                "shipping_line1": "1 St",
                "shipping_city": "London",
                "shipping_postcode": "EC1",
                "shipping_country": "GB",
            },
            format="json",
        )
        assert response.status_code == 400

    def test_place_order_insufficient_stock(self, buyer_client, variant):
        response = buyer_client.post(
            "/api/v1/orders/",
            {
                "items": [{"variant_id": str(variant.id), "quantity": 999}],
                "shipping_name": "X",
                "shipping_line1": "1 St",
                "shipping_city": "London",
                "shipping_postcode": "EC1",
                "shipping_country": "GB",
            },
            format="json",
        )
        assert response.status_code == 400

    def test_list_own_orders(self, buyer_client, placed_order):
        response = buyer_client.get("/api/v1/orders/")
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 1
        assert results[0]["reference"] == placed_order.reference

    def test_list_filter_by_status(self, buyer_client, placed_order):
        response = buyer_client.get("/api/v1/orders/?status=PENDING")
        assert response.status_code == 200
        assert len(response.json()["results"]) == 1
        response2 = buyer_client.get("/api/v1/orders/?status=DELIVERED")
        assert response2.json()["results"] == []

    def test_buyer_cannot_see_other_buyer_orders(self, buyer_client, admin_user, variant):
        from apps.orders import services

        services.place_order(admin_user, [{"variant": variant, "quantity": 1}], SHIPPING)
        response = buyer_client.get("/api/v1/orders/")
        assert response.status_code == 200
        assert response.json()["results"] == []

    def test_unauthenticated(self, client):
        response = client.post("/api/v1/orders/", {}, format="json")
        assert response.status_code == 401


class TestOrderDetail:
    def test_get_own_order(self, buyer_client, placed_order):
        response = buyer_client.get(f"/api/v1/orders/{placed_order.reference}/")
        assert response.status_code == 200
        assert response.json()["reference"] == placed_order.reference

    def test_cannot_get_other_buyer_order(self, supplier_client, placed_order):
        response = supplier_client.get(f"/api/v1/orders/{placed_order.reference}/")
        assert response.status_code == 404

    def test_not_found(self, buyer_client):
        response = buyer_client.get("/api/v1/orders/ORD-DOES-NOT-EXIST/")
        assert response.status_code == 404


class TestOrderCancel:
    def test_cancel_pending_order(self, buyer_client, placed_order):
        response = buyer_client.post(f"/api/v1/orders/{placed_order.reference}/cancel/")
        assert response.status_code == 200
        assert response.json()["status"] == "CANCELLED"

    def test_cannot_cancel_dispatched(self, buyer_client, placed_order, sub_order):
        from apps.orders import services

        services.dispatch_sub_order(sub_order)
        response = buyer_client.post(f"/api/v1/orders/{placed_order.reference}/cancel/")
        assert response.status_code == 400

    def test_cannot_cancel_other_buyers_order(self, supplier_client, placed_order):
        response = supplier_client.post(f"/api/v1/orders/{placed_order.reference}/cancel/")
        assert response.status_code == 404


class TestSupplierSubOrderList:
    def test_list_own_sub_orders(self, supplier_client, sub_order):
        response = supplier_client.get("/api/v1/orders/supplier/")
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 1
        assert results[0]["status"] == "PENDING"

    def test_does_not_show_other_supplier(self, second_supplier_client, sub_order):
        response = second_supplier_client.get("/api/v1/orders/supplier/")
        assert response.status_code == 200
        assert response.json()["results"] == []

    def test_filter_by_status(self, supplier_client, sub_order):
        response = supplier_client.get("/api/v1/orders/supplier/?status=PENDING")
        assert len(response.json()["results"]) == 1
        response2 = supplier_client.get("/api/v1/orders/supplier/?status=CONFIRMED")
        assert response2.json()["results"] == []

    def test_requires_approved_supplier(self, buyer_client):
        response = buyer_client.get("/api/v1/orders/supplier/")
        assert response.status_code == 403


class TestSupplierSubOrderDetail:
    def test_get_own_sub_order(self, supplier_client, sub_order):
        response = supplier_client.get(f"/api/v1/orders/supplier/{sub_order.id}/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PENDING"
        assert len(data["items"]) == 1

    def test_cannot_get_other_supplier_sub_order(self, second_supplier_client, sub_order):
        response = second_supplier_client.get(f"/api/v1/orders/supplier/{sub_order.id}/")
        assert response.status_code == 404


class TestSupplierConfirmView:
    def test_confirm(self, supplier_client, sub_order):
        response = supplier_client.post(f"/api/v1/orders/supplier/{sub_order.id}/confirm/")
        assert response.status_code == 200
        assert response.json()["status"] == "CONFIRMED"

    def test_cannot_confirm_other_supplier(self, second_supplier_client, sub_order):
        response = second_supplier_client.post(f"/api/v1/orders/supplier/{sub_order.id}/confirm/")
        assert response.status_code == 404

    def test_double_confirm_returns_400(self, supplier_client, sub_order):
        supplier_client.post(f"/api/v1/orders/supplier/{sub_order.id}/confirm/")
        response = supplier_client.post(f"/api/v1/orders/supplier/{sub_order.id}/confirm/")
        assert response.status_code == 400


class TestSupplierDispatchView:
    def test_dispatch_with_tracking(self, supplier_client, sub_order):
        response = supplier_client.post(
            f"/api/v1/orders/supplier/{sub_order.id}/dispatch/",
            {"tracking_number": "TRACK-XYZ"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "DISPATCHED"
        assert response.json()["tracking_number"] == "TRACK-XYZ"

    def test_dispatch_without_tracking(self, supplier_client, sub_order):
        response = supplier_client.post(
            f"/api/v1/orders/supplier/{sub_order.id}/dispatch/",
            {},
            format="json",
        )
        assert response.status_code == 200

    def test_cannot_dispatch_other_supplier(self, second_supplier_client, sub_order):
        response = second_supplier_client.post(
            f"/api/v1/orders/supplier/{sub_order.id}/dispatch/",
            {},
            format="json",
        )
        assert response.status_code == 404


class TestSupplierDeliverView:
    def test_deliver(self, supplier_client, dispatched_sub_order):
        response = supplier_client.post(
            f"/api/v1/orders/supplier/{dispatched_sub_order.id}/deliver/"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "DELIVERED"

    def test_cannot_deliver_pending(self, supplier_client, sub_order):
        response = supplier_client.post(f"/api/v1/orders/supplier/{sub_order.id}/deliver/")
        assert response.status_code == 400


class TestAdminOrderViews:
    def test_list_all_orders(self, admin_client, placed_order):
        response = admin_client.get("/api/v1/orders/admin/")
        assert response.status_code == 200
        assert len(response.json()["results"]) == 1

    def test_filter_by_status(self, admin_client, placed_order):
        response = admin_client.get("/api/v1/orders/admin/?status=PENDING")
        assert len(response.json()["results"]) == 1
        response2 = admin_client.get("/api/v1/orders/admin/?status=DELIVERED")
        assert response2.json()["results"] == []

    def test_order_detail(self, admin_client, placed_order):
        response = admin_client.get(f"/api/v1/orders/admin/{placed_order.reference}/")
        assert response.status_code == 200
        assert response.json()["reference"] == placed_order.reference

    def test_requires_admin(self, buyer_client):
        response = buyer_client.get("/api/v1/orders/admin/")
        assert response.status_code == 403
