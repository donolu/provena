import importlib
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.apps import apps as global_apps

from apps.catalogue.models import VatRate
from apps.orders import services
from apps.orders.pricing import compute_order_pricing, extract_vat
from apps.orders.tests.conftest import SHIPPING


def _fake_variant(price: str, vat_rate: str) -> SimpleNamespace:
    return SimpleNamespace(
        price=Decimal(price),
        sku="SKU",
        product=SimpleNamespace(vat_rate=vat_rate),
    )


class TestExtractVat:
    def test_standard_rate_of_120_gross_is_20(self):
        assert extract_vat(Decimal("120.00"), VatRate.STANDARD) == Decimal("20.00")

    def test_reduced_rate_of_105_gross_is_5(self):
        assert extract_vat(Decimal("105.00"), VatRate.REDUCED) == Decimal("5.00")

    def test_zero_rate_is_zero(self):
        assert extract_vat(Decimal("50.00"), VatRate.ZERO) == Decimal("0.00")

    def test_rounds_half_up(self):
        # 3.99 * 0.20 / 1.20 = 0.665 -> 0.67
        assert extract_vat(Decimal("3.99"), VatRate.STANDARD) == Decimal("0.67")


class TestComputeOrderPricing:
    def test_per_line_vat_rounds_independently_then_sums(self):
        # Two identical lines rounded independently (0.67 each) sum to 1.34, which is
        # deliberately not the VAT of the combined 7.98 gross (1.33): per-line is the
        # stored boundary (OrderItem.vat_amount), so it is where rounding happens.
        groups = {
            1: {
                "supplier": object(),
                "items": [
                    {
                        "variant": _fake_variant("3.99", VatRate.STANDARD),
                        "quantity": 1,
                        "line_total": Decimal("3.99"),
                    },
                    {
                        "variant": _fake_variant("3.99", VatRate.STANDARD),
                        "quantity": 1,
                        "line_total": Decimal("3.99"),
                    },
                ],
            }
        }
        pricing = compute_order_pricing(groups)
        sub = pricing.sub_orders[0]
        assert [line.vat_amount for line in sub.lines] == [Decimal("0.67"), Decimal("0.67")]
        assert sub.vat_amount == Decimal("1.34")
        assert extract_vat(Decimal("7.98"), VatRate.STANDARD) == Decimal("1.33")

    def test_totals_aggregate_across_suppliers(self):
        groups = {
            1: {
                "supplier": object(),
                "items": [
                    {
                        "variant": _fake_variant("10.00", VatRate.STANDARD),
                        "quantity": 1,
                        "line_total": Decimal("10.00"),
                    }
                ],
            },
            2: {
                "supplier": object(),
                "items": [
                    {
                        "variant": _fake_variant("20.00", VatRate.ZERO),
                        "quantity": 1,
                        "line_total": Decimal("20.00"),
                    }
                ],
            },
        }
        pricing = compute_order_pricing(groups)
        assert pricing.goods_subtotal == Decimal("30.00")
        assert pricing.total_amount == Decimal("30.00")
        assert pricing.discount_amount == Decimal("0.00")
        assert pricing.shipping_amount == Decimal("0.00")
        # Only the standard-rated supplier contributes VAT: 10 * 0.2/1.2 = 1.67.
        assert pricing.vat_amount == Decimal("1.67")


@pytest.mark.django_db
class TestPricingViaPlaceOrder:
    def test_standard_vat_snapshotted_on_items(self, buyer, variant):
        order = services.place_order(buyer, [{"variant": variant, "quantity": 2}], SHIPPING)
        item = order.sub_orders.first().items.first()
        assert item.vat_rate == VatRate.STANDARD
        # 7.98 gross * 0.2/1.2 = 1.33
        assert item.vat_amount == Decimal("1.33")

    def test_inclusive_vat_leaves_total_unchanged(self, buyer, variant):
        order = services.place_order(buyer, [{"variant": variant, "quantity": 3}], SHIPPING)
        expected = variant.price * 3
        assert order.total_amount == expected
        assert order.goods_subtotal == expected
        assert order.discount_amount == Decimal("0.00")
        assert order.shipping_amount == Decimal("0.00")

    def test_vat_reconciles_order_suborder_item(self, buyer, variant, second_variant):
        order = services.place_order(
            buyer,
            [{"variant": variant, "quantity": 2}, {"variant": second_variant, "quantity": 3}],
            SHIPPING,
        )
        subs = list(order.sub_orders.all())
        assert order.vat_amount == sum((s.vat_amount for s in subs), Decimal("0.00"))
        for sub in subs:
            assert sub.vat_amount == sum((i.vat_amount for i in sub.items.all()), Decimal("0.00"))
            assert sub.goods_subtotal == sub.subtotal

    def test_reduced_rate_product(self, buyer, variant):
        variant.product.vat_rate = VatRate.REDUCED
        variant.product.save()
        order = services.place_order(buyer, [{"variant": variant, "quantity": 1}], SHIPPING)
        item = order.sub_orders.first().items.first()
        assert item.vat_rate == VatRate.REDUCED
        assert item.vat_amount == extract_vat(Decimal("3.99"), VatRate.REDUCED)

    def test_zero_rate_product_has_no_vat(self, buyer, variant):
        variant.product.vat_rate = VatRate.ZERO
        variant.product.save()
        order = services.place_order(buyer, [{"variant": variant, "quantity": 4}], SHIPPING)
        item = order.sub_orders.first().items.first()
        assert item.vat_amount == Decimal("0.00")
        assert order.vat_amount == Decimal("0.00")
        # Total is still the full inclusive price.
        assert order.total_amount == variant.price * 4


@pytest.mark.django_db
class TestBackfillMigration:
    def test_backfill_repopulates_breakdown(self, buyer, variant):
        # place_order already fills the columns; zero them to simulate a pre-migration row,
        # then run the migration's backfill and confirm it reconstructs the breakdown.
        order = services.place_order(buyer, [{"variant": variant, "quantity": 2}], SHIPPING)
        sub = order.sub_orders.first()
        item = sub.items.first()

        order.goods_subtotal = order.vat_amount = Decimal("0.00")
        order.save(update_fields=["goods_subtotal", "vat_amount"])
        sub.goods_subtotal = sub.vat_amount = Decimal("0.00")
        sub.save(update_fields=["goods_subtotal", "vat_amount"])
        item.vat_amount = Decimal("0.00")
        item.save(update_fields=["vat_amount"])

        migration = importlib.import_module("apps.orders.migrations.0006_pricing_breakdown")
        migration.backfill_pricing(global_apps, None)

        order.refresh_from_db()
        sub.refresh_from_db()
        item.refresh_from_db()
        assert order.goods_subtotal == order.total_amount
        assert item.vat_amount == extract_vat(variant.price * 2, VatRate.STANDARD)
        assert sub.vat_amount == item.vat_amount
        assert order.vat_amount == sub.vat_amount
