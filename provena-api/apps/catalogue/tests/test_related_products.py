from decimal import Decimal

import pytest

from apps.catalogue.models import Category, Product, ProductStatus, ProductVariant

RELATED_URL = "/api/v1/catalogue/products/{slug}/related/"


def _product(supplier, cat, name, slug, status=ProductStatus.ACTIVE):
    p = Product.objects.create(supplier=supplier, category=cat, name=name, slug=slug, status=status)
    ProductVariant.objects.create(
        product=p, name="default", sku=f"{slug}-sku", price=Decimal("5.00")
    )
    return p


@pytest.mark.django_db
class TestRelatedProducts:
    def test_ranks_by_shared_category_and_supplier(
        self, api_client, active_product, category, approved_supplier, second_supplier
    ):
        other_cat = Category.objects.create(name="Dairy", slug="dairy")
        _product(approved_supplier, category, "Same cat & supplier", "a")  # relevance 3
        _product(second_supplier, category, "Same cat", "b")  # relevance 2
        _product(approved_supplier, other_cat, "Same supplier", "c")  # relevance 1
        _product(second_supplier, other_cat, "Unrelated", "d")  # excluded

        res = api_client.get(RELATED_URL.format(slug=active_product.slug))
        assert res.status_code == 200
        slugs = [p["slug"] for p in res.json()]
        assert active_product.slug not in slugs  # self excluded
        assert "d" not in slugs  # shares nothing
        assert slugs[:3] == ["a", "b", "c"]  # ranked by relevance

    def test_excludes_inactive(self, api_client, active_product, category, approved_supplier):
        _product(approved_supplier, category, "Draft", "draft-p", status=ProductStatus.DRAFT)
        res = api_client.get(RELATED_URL.format(slug=active_product.slug))
        assert "draft-p" not in [p["slug"] for p in res.json()]

    def test_caps_at_eight(self, api_client, active_product, category, approved_supplier):
        for i in range(10):
            _product(approved_supplier, category, f"P{i}", f"p-{i}")
        res = api_client.get(RELATED_URL.format(slug=active_product.slug))
        assert len(res.json()) == 8

    def test_404_for_draft_or_missing(self, api_client, draft_product):
        assert api_client.get(RELATED_URL.format(slug=draft_product.slug)).status_code == 404
        assert api_client.get(RELATED_URL.format(slug="does-not-exist")).status_code == 404

    def test_null_category_falls_back_to_supplier(
        self, api_client, approved_supplier, category, second_supplier
    ):
        _product(approved_supplier, None, "No category", "no-cat")
        _product(approved_supplier, category, "Same supplier", "same-sup")
        _product(second_supplier, category, "Different supplier", "diff-sup")

        res = api_client.get(RELATED_URL.format(slug="no-cat"))
        slugs = [p["slug"] for p in res.json()]
        assert "same-sup" in slugs
        assert "diff-sup" not in slugs  # no shared category or supplier
