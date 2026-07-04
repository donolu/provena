from apps.inventory.models import MovementType, StockLevel, StockLot, StockMovement


class TestStockLevel:
    def test_str(self, variant):
        level = StockLevel.objects.create(variant=variant, quantity_available=20)
        assert "CARR-1KG" in str(level)
        assert "20" in str(level)

    def test_quantity_on_hand(self, variant):
        level = StockLevel.objects.create(
            variant=variant, quantity_available=30, quantity_reserved=10
        )
        assert level.quantity_on_hand == 40

    def test_is_low_stock_below_threshold(self, variant):
        level = StockLevel.objects.create(
            variant=variant, quantity_available=5, low_stock_threshold=10
        )
        assert level.is_low_stock is True

    def test_is_low_stock_at_threshold(self, variant):
        level = StockLevel.objects.create(
            variant=variant, quantity_available=10, low_stock_threshold=10
        )
        assert level.is_low_stock is True

    def test_is_low_stock_above_threshold(self, variant):
        level = StockLevel.objects.create(
            variant=variant, quantity_available=11, low_stock_threshold=10
        )
        assert level.is_low_stock is False

    def test_is_low_stock_no_threshold(self, variant):
        level = StockLevel.objects.create(
            variant=variant, quantity_available=0, low_stock_threshold=0
        )
        assert level.is_low_stock is False

    def test_default_quantities(self, variant):
        level = StockLevel.objects.create(variant=variant)
        assert level.quantity_available == 0
        assert level.quantity_reserved == 0
        assert level.low_stock_threshold == 0


class TestStockLot:
    def test_str_with_lot_number(self, variant):
        lot = StockLot.objects.create(
            variant=variant,
            lot_number="LOT-001",
            quantity_received=100,
            quantity_remaining=100,
        )
        assert "LOT-001" in str(lot)
        assert "CARR-1KG" in str(lot)

    def test_str_without_lot_number(self, variant):
        lot = StockLot.objects.create(variant=variant, quantity_received=50, quantity_remaining=50)
        assert "CARR-1KG" in str(lot)

    def test_expiry_nullable(self, variant):
        lot = StockLot.objects.create(variant=variant, quantity_received=10, quantity_remaining=10)
        assert lot.expires_at is None


class TestStockMovement:
    def test_str_positive(self, variant):
        m = StockMovement.objects.create(
            variant=variant,
            movement_type=MovementType.INBOUND,
            quantity=50,
            quantity_after=50,
        )
        assert "+50" in str(m)
        assert "INBOUND" in str(m)

    def test_str_negative(self, variant):
        m = StockMovement.objects.create(
            variant=variant,
            movement_type=MovementType.OUTBOUND,
            quantity=-10,
            quantity_after=40,
        )
        assert "-10" in str(m)
        assert "OUTBOUND" in str(m)

    def test_performed_by_nullable(self, variant):
        m = StockMovement.objects.create(
            variant=variant,
            movement_type=MovementType.ADJUSTMENT,
            quantity=5,
            quantity_after=55,
        )
        assert m.performed_by is None
