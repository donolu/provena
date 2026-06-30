from apps.inventory.models import StockLevel


class TestInventoryListView:
    def test_list_own_inventory(self, supplier_client, stock_level):
        response = supplier_client.get("/api/v1/inventory/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["variant_sku"] == "CARR-1KG"

    def test_does_not_show_other_supplier_inventory(
        self, supplier_client, second_variant, stock_level
    ):
        StockLevel.objects.create(variant=second_variant, quantity_available=20)
        response = supplier_client.get("/api/v1/inventory/")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_filter_low_stock(self, supplier_client, stock_level):
        stock_level.low_stock_threshold = 60
        stock_level.save()
        response = supplier_client.get("/api/v1/inventory/?low_stock=true")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_filter_low_stock_excludes_healthy(self, supplier_client, stock_level):
        stock_level.low_stock_threshold = 10
        stock_level.save()
        response = supplier_client.get("/api/v1/inventory/?low_stock=true")
        assert response.status_code == 200
        assert response.json() == []

    def test_requires_approved_supplier(self, buyer_client):
        response = buyer_client.get("/api/v1/inventory/")
        assert response.status_code == 403

    def test_unauthenticated(self, client):
        response = client.get("/api/v1/inventory/")
        assert response.status_code == 401


class TestInventoryDetailView:
    def test_get_stock_level(self, supplier_client, variant, stock_level):
        response = supplier_client.get(f"/api/v1/inventory/{variant.id}/")
        assert response.status_code == 200
        data = response.json()
        assert data["quantity_available"] == 50
        assert "is_low_stock" in data
        assert "quantity_on_hand" in data

    def test_creates_stock_level_if_absent(self, supplier_client, variant):
        response = supplier_client.get(f"/api/v1/inventory/{variant.id}/")
        assert response.status_code == 200
        assert response.json()["quantity_available"] == 0

    def test_cannot_see_other_supplier_variant(self, supplier_client, second_variant):
        response = supplier_client.get(f"/api/v1/inventory/{second_variant.id}/")
        assert response.status_code == 404

    def test_set_low_stock_threshold(self, supplier_client, variant):
        response = supplier_client.patch(
            f"/api/v1/inventory/{variant.id}/",
            {"low_stock_threshold": 10},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["low_stock_threshold"] == 10

    def test_set_negative_threshold_fails(self, supplier_client, variant):
        response = supplier_client.patch(
            f"/api/v1/inventory/{variant.id}/",
            {"low_stock_threshold": -1},
            format="json",
        )
        assert response.status_code == 400


class TestReceiveStockView:
    def test_receive_stock(self, supplier_client, variant):
        response = supplier_client.post(
            f"/api/v1/inventory/{variant.id}/receive/",
            {"quantity": 100, "lot_number": "LOT-001"},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["quantity_available"] == 100

    def test_receive_with_expiry(self, supplier_client, variant):
        response = supplier_client.post(
            f"/api/v1/inventory/{variant.id}/receive/",
            {"quantity": 50, "expires_at": "2026-12-31"},
            format="json",
        )
        assert response.status_code == 201

    def test_receive_increments_existing(self, supplier_client, variant, stock_level):
        response = supplier_client.post(
            f"/api/v1/inventory/{variant.id}/receive/",
            {"quantity": 25},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["quantity_available"] == 75

    def test_zero_quantity_rejected(self, supplier_client, variant):
        response = supplier_client.post(
            f"/api/v1/inventory/{variant.id}/receive/",
            {"quantity": 0},
            format="json",
        )
        assert response.status_code == 400

    def test_cannot_receive_for_other_supplier(self, supplier_client, second_variant):
        response = supplier_client.post(
            f"/api/v1/inventory/{second_variant.id}/receive/",
            {"quantity": 10},
            format="json",
        )
        assert response.status_code == 404


class TestAdjustStockView:
    def test_positive_adjustment(self, supplier_client, variant, stock_level):
        response = supplier_client.post(
            f"/api/v1/inventory/{variant.id}/adjust/",
            {"delta": 10, "notes": "Found extra crates"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["quantity_available"] == 60

    def test_negative_adjustment(self, supplier_client, variant, stock_level):
        response = supplier_client.post(
            f"/api/v1/inventory/{variant.id}/adjust/",
            {"delta": -20, "notes": "Damaged goods"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["quantity_available"] == 30

    def test_adjustment_below_zero_returns_400(self, supplier_client, variant, stock_level):
        response = supplier_client.post(
            f"/api/v1/inventory/{variant.id}/adjust/",
            {"delta": -100, "notes": "Cannot go negative"},
            format="json",
        )
        assert response.status_code == 400
        assert "negative" in response.json()["detail"]

    def test_zero_delta_rejected(self, supplier_client, variant):
        response = supplier_client.post(
            f"/api/v1/inventory/{variant.id}/adjust/",
            {"delta": 0, "notes": "Nothing"},
            format="json",
        )
        assert response.status_code == 400

    def test_notes_required(self, supplier_client, variant):
        response = supplier_client.post(
            f"/api/v1/inventory/{variant.id}/adjust/",
            {"delta": 5},
            format="json",
        )
        assert response.status_code == 400


class TestStockMovementListView:
    def test_list_movements(self, supplier_client, variant):
        from apps.inventory import services

        services.receive_stock(variant, 50)
        services.adjust_stock(variant, -10, notes="Adjustment")
        response = supplier_client.get(f"/api/v1/inventory/{variant.id}/movements/")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_movement_fields(self, supplier_client, variant):
        from apps.inventory import services

        services.receive_stock(variant, 30)
        response = supplier_client.get(f"/api/v1/inventory/{variant.id}/movements/")
        m = response.json()[0]
        assert m["movement_type"] == "INBOUND"
        assert m["quantity"] == 30
        assert m["quantity_after"] == 30

    def test_cannot_see_other_supplier_movements(self, supplier_client, second_variant):
        response = supplier_client.get(f"/api/v1/inventory/{second_variant.id}/movements/")
        assert response.status_code == 404


class TestStockLotListView:
    def test_list_lots(self, supplier_client, variant):
        from apps.inventory import services

        services.receive_stock(variant, 100, lot_number="LOT-A")
        services.receive_stock(variant, 50, lot_number="LOT-B")
        response = supplier_client.get(f"/api/v1/inventory/{variant.id}/lots/")
        assert response.status_code == 200
        lot_numbers = [lot["lot_number"] for lot in response.json()]
        assert "LOT-A" in lot_numbers
        assert "LOT-B" in lot_numbers

    def test_empty_lots(self, supplier_client, variant):
        response = supplier_client.get(f"/api/v1/inventory/{variant.id}/lots/")
        assert response.status_code == 200
        assert response.json() == []

    def test_cannot_see_other_supplier_lots(self, supplier_client, second_variant):
        response = supplier_client.get(f"/api/v1/inventory/{second_variant.id}/lots/")
        assert response.status_code == 404


class TestAdminInventoryListView:
    def test_admin_sees_all(self, admin_client, stock_level, second_variant):
        StockLevel.objects.create(variant=second_variant, quantity_available=20)
        response = admin_client.get("/api/v1/inventory/admin/")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_admin_filter_low_stock(self, admin_client, stock_level):
        stock_level.low_stock_threshold = 60
        stock_level.save()
        response = admin_client.get("/api/v1/inventory/admin/?low_stock=true")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_admin_filter_by_supplier(self, admin_client, stock_level, second_variant):
        StockLevel.objects.create(variant=second_variant, quantity_available=20)
        response = admin_client.get("/api/v1/inventory/admin/?supplier=green-roots-farm")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_supplier_cannot_access(self, supplier_client):
        response = supplier_client.get("/api/v1/inventory/admin/")
        assert response.status_code == 403

    def test_unauthenticated_cannot_access(self, client):
        response = client.get("/api/v1/inventory/admin/")
        assert response.status_code == 401
