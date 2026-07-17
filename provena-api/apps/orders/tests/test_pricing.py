import importlib
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.apps import apps as global_apps

from apps.catalogue.models import VatRate
from apps.orders import services
from apps.orders.models import (
    DiscountCode,
    DiscountFunding,
    DiscountRedemption,
    DiscountType,
)
from apps.orders.pricing import allocate_largest_remainder, compute_order_pricing, extract_vat
from apps.orders.tests.conftest import SHIPPING
from apps.suppliers.models import ShippingPolicy, Supplier


def _fake_variant(price: str, vat_rate: str) -> SimpleNamespace:
    return SimpleNamespace(
        price=Decimal(price),
        sku="SKU",
        product=SimpleNamespace(vat_rate=vat_rate),
    )


def _free_supplier() -> Supplier:
    # Unsaved instance — no DB needed; default policy is flat £0 (free).
    return Supplier(shipping_policy=ShippingPolicy.FLAT, shipping_flat_rate=Decimal("0.00"))


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
                "supplier": _free_supplier(),
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
                "supplier": _free_supplier(),
                "items": [
                    {
                        "variant": _fake_variant("10.00", VatRate.STANDARD),
                        "quantity": 1,
                        "line_total": Decimal("10.00"),
                    }
                ],
            },
            2: {
                "supplier": _free_supplier(),
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


class TestShippingPricing:
    def _group(self, supplier: Supplier, price: str, qty: int) -> dict:
        return {
            1: {
                "supplier": supplier,
                "items": [
                    {
                        "variant": _fake_variant(price, VatRate.STANDARD),
                        "quantity": qty,
                        "line_total": Decimal(price) * qty,
                    }
                ],
            }
        }

    def test_flat_rate_added_to_total_with_vat(self):
        supplier = Supplier(shipping_policy=ShippingPolicy.FLAT, shipping_flat_rate=Decimal("4.99"))
        sub = compute_order_pricing(self._group(supplier, "10.00", 1)).sub_orders[0]
        assert sub.shipping_amount == Decimal("4.99")
        assert sub.total == Decimal("14.99")
        assert sub.vat_amount == extract_vat(Decimal("10.00"), VatRate.STANDARD) + extract_vat(
            Decimal("4.99"), VatRate.STANDARD
        )

    def test_per_item_rate(self):
        supplier = Supplier(
            shipping_policy=ShippingPolicy.PER_ITEM, shipping_per_item_rate=Decimal("1.50")
        )
        sub = compute_order_pricing(self._group(supplier, "10.00", 3)).sub_orders[0]
        assert sub.shipping_amount == Decimal("4.50")  # 1.50 * 3
        assert sub.total == Decimal("34.50")

    def test_free_over_threshold_below_charges_flat(self):
        supplier = Supplier(
            shipping_policy=ShippingPolicy.FREE_OVER_THRESHOLD,
            shipping_flat_rate=Decimal("5.00"),
            free_shipping_threshold=Decimal("50.00"),
        )
        sub = compute_order_pricing(self._group(supplier, "10.00", 1)).sub_orders[0]
        assert sub.shipping_amount == Decimal("5.00")

    def test_free_over_threshold_at_boundary_is_free(self):
        supplier = Supplier(
            shipping_policy=ShippingPolicy.FREE_OVER_THRESHOLD,
            shipping_flat_rate=Decimal("5.00"),
            free_shipping_threshold=Decimal("50.00"),
        )
        sub = compute_order_pricing(self._group(supplier, "50.00", 1)).sub_orders[0]
        assert sub.shipping_amount == Decimal("0.00")


@pytest.mark.django_db
class TestShippingViaPlaceOrder:
    def test_flat_shipping_snapshotted_into_total_and_vat(self, buyer, variant, approved_supplier):
        approved_supplier.shipping_policy = ShippingPolicy.FLAT
        approved_supplier.shipping_flat_rate = Decimal("4.99")
        approved_supplier.save()

        order = services.place_order(buyer, [{"variant": variant, "quantity": 2}], SHIPPING)
        sub = order.sub_orders.first()
        item = sub.items.first()
        goods = variant.price * 2  # 7.98

        assert sub.shipping_amount == Decimal("4.99")
        assert order.shipping_amount == Decimal("4.99")
        assert sub.subtotal == goods + Decimal("4.99")
        assert order.total_amount == goods + Decimal("4.99")
        # Item VAT is goods-only; the sub-order VAT additionally carries the shipping VAT.
        assert sub.vat_amount == item.vat_amount + extract_vat(Decimal("4.99"), VatRate.STANDARD)


class TestAllocateLargestRemainder:
    def test_sums_exactly_on_uneven_split(self):
        parts = allocate_largest_remainder(
            Decimal("10.00"), [Decimal("1"), Decimal("1"), Decimal("1")]
        )
        assert sum(parts) == Decimal("10.00")  # no lost/invented penny
        assert parts == [Decimal("3.34"), Decimal("3.33"), Decimal("3.33")]

    def test_proportional_split(self):
        parts = allocate_largest_remainder(Decimal("9.00"), [Decimal("10"), Decimal("20")])
        assert parts == [Decimal("3.00"), Decimal("6.00")]

    def test_zero_total_returns_zeros(self):
        assert allocate_largest_remainder(Decimal("0.00"), [Decimal("1"), Decimal("2")]) == [
            Decimal("0.00"),
            Decimal("0.00"),
        ]


class TestDiscountPricing:
    def _one_supplier(self, price: str, qty: int) -> dict:
        return {
            1: {
                "supplier": _free_supplier(),
                "items": [
                    {
                        "variant": _fake_variant(price, VatRate.STANDARD),
                        "quantity": qty,
                        "line_total": Decimal(price) * qty,
                    }
                ],
            }
        }

    def test_percentage_reduces_total_and_vat_base(self):
        code = DiscountCode(discount_type=DiscountType.PERCENTAGE, value=Decimal("10"))
        pricing = compute_order_pricing(self._one_supplier("100.00", 1), discount_code=code)
        sub = pricing.sub_orders[0]
        assert sub.discount_amount == Decimal("10.00")
        assert sub.total == Decimal("90.00")
        # VAT is on the post-discount 90.00, not the pre-discount 100.
        assert sub.vat_amount == extract_vat(Decimal("90.00"), VatRate.STANDARD)
        assert pricing.total_amount == Decimal("90.00")

    def test_fixed_discount_capped_at_goods(self):
        code = DiscountCode(discount_type=DiscountType.FIXED, value=Decimal("20.00"))
        pricing = compute_order_pricing(self._one_supplier("5.00", 1), discount_code=code)
        assert pricing.discount_amount == Decimal("5.00")
        assert pricing.total_amount == Decimal("0.00")

    def test_allocated_across_suppliers_sums_exactly(self):
        groups = {
            1: {
                "supplier": _free_supplier(),
                "items": [
                    {
                        "variant": _fake_variant("10.00", VatRate.STANDARD),
                        "quantity": 1,
                        "line_total": Decimal("10.00"),
                    }
                ],
            },
            2: {
                "supplier": _free_supplier(),
                "items": [
                    {
                        "variant": _fake_variant("20.00", VatRate.STANDARD),
                        "quantity": 1,
                        "line_total": Decimal("20.00"),
                    }
                ],
            },
        }
        code = DiscountCode(discount_type=DiscountType.FIXED, value=Decimal("9.00"))
        subs = compute_order_pricing(groups, discount_code=code).sub_orders
        assert subs[0].discount_amount == Decimal("3.00")  # 10/30 of 9
        assert subs[1].discount_amount == Decimal("6.00")  # 20/30 of 9
        assert subs[0].discount_amount + subs[1].discount_amount == Decimal("9.00")


@pytest.mark.django_db
class TestDiscountViaPlaceOrder:
    def _code(self, **kw) -> DiscountCode:
        defaults = dict(
            code="SAVE10",
            discount_type=DiscountType.PERCENTAGE,
            value=Decimal("10"),
            funded_by=DiscountFunding.PLATFORM,
        )
        defaults.update(kw)
        return DiscountCode.objects.create(**defaults)

    def test_valid_code_applied_and_recorded(self, buyer, variant):
        self._code()
        order = services.place_order(
            buyer, [{"variant": variant, "quantity": 4}], SHIPPING, discount_code="save10"
        )
        goods = variant.price * 4
        expected = (goods * Decimal("0.10")).quantize(Decimal("0.01"))
        assert order.discount_amount == expected
        assert order.discount_code == "SAVE10"
        assert order.discount_funded_by == "PLATFORM"
        assert order.total_amount == goods - expected
        assert DiscountRedemption.objects.filter(order=order).count() == 1

    def test_unknown_code_rejected(self, buyer, variant):
        with pytest.raises(ValueError, match="not found"):
            services.place_order(
                buyer, [{"variant": variant, "quantity": 1}], SHIPPING, discount_code="NOPE"
            )

    def test_minimum_spend_enforced(self, buyer, variant):
        self._code(minimum_spend=Decimal("100.00"))
        with pytest.raises(ValueError, match="Spend at least"):
            services.place_order(
                buyer, [{"variant": variant, "quantity": 1}], SHIPPING, discount_code="SAVE10"
            )

    def test_expired_code_rejected(self, buyer, variant):
        from datetime import timedelta

        from django.utils import timezone

        self._code(valid_until=timezone.now() - timedelta(days=1))
        with pytest.raises(ValueError, match="not currently valid"):
            services.place_order(
                buyer, [{"variant": variant, "quantity": 1}], SHIPPING, discount_code="SAVE10"
            )

    def test_global_usage_limit(self, buyer, variant, second_variant):
        self._code(max_uses=1)
        services.place_order(
            buyer, [{"variant": variant, "quantity": 1}], SHIPPING, discount_code="SAVE10"
        )
        with pytest.raises(ValueError, match="usage limit"):
            services.place_order(
                buyer,
                [{"variant": second_variant, "quantity": 1}],
                SHIPPING,
                discount_code="SAVE10",
            )

    def test_per_buyer_usage_limit(self, buyer, variant, second_variant):
        self._code(max_uses_per_buyer=1)
        services.place_order(
            buyer, [{"variant": variant, "quantity": 1}], SHIPPING, discount_code="SAVE10"
        )
        with pytest.raises(ValueError, match="already used"):
            services.place_order(
                buyer,
                [{"variant": second_variant, "quantity": 1}],
                SHIPPING,
                discount_code="SAVE10",
            )
