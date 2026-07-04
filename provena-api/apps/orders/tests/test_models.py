from apps.orders.models import (
    DisputeStatus,
    OrderDispute,
    OrderStatus,
    _generate_order_reference,
)


class TestOrderReference:
    def test_format(self, db):
        ref = _generate_order_reference()
        parts = ref.split("-")
        assert parts[0] == "ORD"
        assert len(parts[1]) == 8
        assert len(parts[2]) == 6

    def test_uniqueness(self, db):
        refs = {_generate_order_reference() for _ in range(20)}
        assert len(refs) == 20


class TestOrder:
    def test_str(self, placed_order):
        assert str(placed_order).startswith("ORD-")

    def test_default_status(self, placed_order):
        assert placed_order.status == OrderStatus.PENDING

    def test_total_amount(self, placed_order, variant):
        assert placed_order.total_amount == variant.price * 2


class TestSubOrder:
    def test_str(self, sub_order):
        assert "ORD-" in str(sub_order)
        assert "Green Roots Farm" in str(sub_order)

    def test_default_status(self, sub_order):
        assert sub_order.status == OrderStatus.PENDING

    def test_subtotal(self, sub_order, variant):
        assert sub_order.subtotal == variant.price * 2


class TestOrderItem:
    def test_str(self, sub_order):
        item = sub_order.items.first()
        assert "CARR-1KG" in str(item)
        assert "2" in str(item)

    def test_total_price(self, sub_order, variant):
        item = sub_order.items.first()
        assert item.total_price == variant.price * 2

    def test_snapshot_fields(self, sub_order, variant):
        item = sub_order.items.first()
        assert item.product_name == "Organic Carrots"
        assert item.variant_name == "1kg bag"
        assert item.sku == "CARR-1KG"
        assert item.unit_price == variant.price


class TestOrderDispute:
    def test_str(self, dispatched_sub_order, buyer):
        dispute = OrderDispute.objects.create(
            sub_order=dispatched_sub_order, raised_by=buyer, reason="Wrong item"
        )
        assert "OPEN" in str(dispute)

    def test_default_status(self, dispatched_sub_order, buyer):
        dispute = OrderDispute.objects.create(
            sub_order=dispatched_sub_order, raised_by=buyer, reason="Damaged"
        )
        assert dispute.status == DisputeStatus.OPEN
