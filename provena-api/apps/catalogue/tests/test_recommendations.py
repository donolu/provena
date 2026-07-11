from decimal import Decimal

import pytest

from apps.catalogue.models import Category, Product, ProductStatus, ProductVariant
from apps.orders.models import Order, OrderItem, OrderStatus, SubOrder

URL = "/api/v1/catalogue/products/recommendations/"


def _product(supplier, category, name, slug, *, featured=False, status=ProductStatus.ACTIVE):
    product = Product.objects.create(
        supplier=supplier,
        category=category,
        name=name,
        slug=slug,
        status=status,
        is_featured=featured,
    )
    ProductVariant.objects.create(
        product=product, name="default", sku=f"{slug}-sku", price=Decimal("5.00")
    )
    return product


def _buy(buyer, product, *, status=OrderStatus.DELIVERED):
    """Give ``buyer`` a paid (DELIVERED by default) order line for ``product``.

    ``status`` is applied to both the order and its sub-order; recommendations
    key off the sub-order status.
    """
    order = Order.objects.create(
        buyer=buyer,
        reference=f"ORD-{product.slug}"[:24],
        status=status,
        shipping_name="Test Buyer",
        shipping_line1="1 Street",
        shipping_city="London",
        shipping_postcode="EC1A 1BB",
        shipping_country="GB",
    )
    sub = SubOrder.objects.create(order=order, supplier=product.supplier, status=status)
    variant = product.variants.first()
    OrderItem.objects.create(
        sub_order=sub,
        variant=variant,
        product_name=product.name,
        variant_name=variant.name,
        sku=variant.sku,
        quantity=1,
        unit_price=variant.price,
    )
    return order


@pytest.mark.django_db
class TestRecommendations:
    def test_anonymous_cold_start_ranks_featured_then_popular(
        self, api_client, approved_supplier, category, buyer
    ):
        featured = _product(approved_supplier, category, "Featured", "featured", featured=True)
        popular = _product(approved_supplier, category, "Popular", "popular")
        plain = _product(approved_supplier, category, "Plain", "plain")
        # `popular` has been ordered; `plain` never has.
        _buy(buyer, popular)

        res = api_client.get(URL)
        assert res.status_code == 200
        slugs = [p["slug"] for p in res.json()]
        # Featured first (editor's pick), then the most-ordered, then the rest.
        assert slugs.index(featured.slug) < slugs.index(popular.slug) < slugs.index(plain.slug)

    def test_personalised_by_category_and_supplier_affinity(
        self, api_client, buyer, approved_supplier, second_supplier, category
    ):
        other_cat = Category.objects.create(name="Dairy", slug="dairy")
        # Buyer's history: a product in `category` from `approved_supplier`.
        bought = _product(approved_supplier, category, "Bought", "bought")
        _buy(buyer, bought)

        both = _product(approved_supplier, category, "Same cat+supplier", "both")  # affinity 3
        cat_only = _product(second_supplier, category, "Same cat", "cat-only")  # affinity 2
        sup_only = _product(approved_supplier, other_cat, "Same supplier", "sup-only")  # affinity 1
        neither = _product(second_supplier, other_cat, "Unrelated", "neither")  # affinity 0

        api_client.force_authenticate(user=buyer)
        res = api_client.get(URL)
        assert res.status_code == 200
        slugs = [p["slug"] for p in res.json()]

        assert bought.slug not in slugs  # already purchased -> excluded
        assert slugs[:4] == [both.slug, cat_only.slug, sup_only.slug, neither.slug]

    def test_excludes_already_purchased(self, api_client, buyer, approved_supplier, category):
        bought = _product(approved_supplier, category, "Bought", "bought")
        available = _product(approved_supplier, category, "Available", "available")
        _buy(buyer, bought)

        api_client.force_authenticate(user=buyer)
        slugs = [p["slug"] for p in api_client.get(URL).json()]
        assert bought.slug not in slugs
        assert available.slug in slugs

    def test_excludes_inactive_products(self, api_client, approved_supplier, category):
        _product(approved_supplier, category, "Draft", "draft", status=ProductStatus.DRAFT)
        active = _product(approved_supplier, category, "Active", "active")

        slugs = [p["slug"] for p in api_client.get(URL).json()]
        assert "draft" not in slugs
        assert active.slug in slugs

    @pytest.mark.parametrize("status", [OrderStatus.PENDING, OrderStatus.CANCELLED])
    def test_unpaid_orders_do_not_exclude_or_drive_affinity(
        self, api_client, buyer, approved_supplier, category, status
    ):
        # PENDING = checkout started but never paid; CANCELLED = paid then voided.
        # Neither is real purchase history, so the product stays recommendable.
        unpaid = _product(approved_supplier, category, "Unpaid buy", "unpaid")
        _buy(buyer, unpaid, status=status)

        api_client.force_authenticate(user=buyer)
        slugs = [p["slug"] for p in api_client.get(URL).json()]
        assert unpaid.slug in slugs

    def test_pending_orders_do_not_count_towards_popularity(
        self, api_client, buyer, approved_supplier, category
    ):
        # A never-paid order must not boost a product above a genuinely paid one.
        paid = _product(approved_supplier, category, "Paid popular", "paid-popular")
        pending = _product(approved_supplier, category, "Pending popular", "pending-popular")
        _buy(buyer, paid, status=OrderStatus.DELIVERED)
        _buy(buyer, pending, status=OrderStatus.PENDING)

        slugs = [p["slug"] for p in api_client.get(URL).json()]  # anonymous cold-start
        assert slugs.index(paid.slug) < slugs.index(pending.slug)

    def test_caps_at_twelve(self, api_client, approved_supplier, category):
        for i in range(15):
            _product(approved_supplier, category, f"P{i}", f"p-{i}")
        res = api_client.get(URL)
        assert len(res.json()) == 12
