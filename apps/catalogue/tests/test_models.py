from decimal import Decimal

import pytest

from apps.catalogue.models import (
    Category,
    Product,
    ProductImage,
    ProductStatus,
    ProductVariant,
    _unique_category_slug,
    _unique_product_slug,
)


class TestCategory:
    def test_str(self, category):
        assert str(category) == "Fresh Produce"

    def test_hierarchy(self, subcategory, category):
        assert subcategory.parent == category
        assert subcategory in category.children.all()

    def test_slug_uniqueness(self, db):
        Category.objects.create(name="Fruit", slug="fruit")
        slug = _unique_category_slug("Fruit")
        assert slug == "fruit-1"

    def test_defaults(self, db):
        cat = Category.objects.create(name="Dairy", slug="dairy")
        assert cat.is_active is True
        assert cat.position == 0
        assert cat.description == ""


class TestProduct:
    def test_str(self, active_product):
        assert str(active_product) == "Organic Carrots"

    def test_is_published_active(self, active_product):
        assert active_product.is_published is True

    def test_is_published_draft(self, draft_product):
        assert draft_product.is_published is False

    def test_uuid_pk(self, active_product):
        import uuid

        assert isinstance(active_product.id, uuid.UUID)

    def test_slug_uniqueness(self, approved_supplier, category):
        Product.objects.create(
            supplier=approved_supplier,
            category=category,
            name="Test Product",
            slug="test-product",
            status=ProductStatus.DRAFT,
        )
        slug = _unique_product_slug("Test Product")
        assert slug == "test-product-1"

    def test_default_status_is_draft(self, approved_supplier):
        slug = _unique_product_slug("New Product")
        p = Product.objects.create(
            supplier=approved_supplier,
            name="New Product",
            slug=slug,
        )
        assert p.status == ProductStatus.DRAFT


class TestProductVariant:
    def test_str(self, variant, active_product):
        assert "Organic Carrots" in str(variant)
        assert "CARR-1KG" in str(variant)

    def test_on_sale_false_when_no_compare_price(self, variant):
        assert variant.on_sale is False
        assert variant.discount_percent is None

    def test_on_sale_true(self, active_product):
        v = ProductVariant.objects.create(
            product=active_product,
            name="2kg bag",
            sku="CARR-2KG",
            price=Decimal("5.00"),
            compare_at_price=Decimal("8.00"),
        )
        assert v.on_sale is True
        assert v.discount_percent == Decimal("37.50")

    def test_sku_unique(self, db, active_product, approved_supplier, category):
        ProductVariant.objects.create(
            product=active_product, name="500g", sku="UNIQUE-SKU", price=Decimal("2.00")
        )
        other = Product.objects.create(
            supplier=approved_supplier,
            category=category,
            name="Other",
            slug="other-product",
            status=ProductStatus.DRAFT,
        )
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            ProductVariant.objects.create(
                product=other, name="500g", sku="UNIQUE-SKU", price=Decimal("2.00")
            )


class TestProductImage:
    def test_str(self, image, active_product):
        assert "Organic Carrots" in str(image)

    def test_is_primary(self, image):
        assert image.is_primary is True

    def test_ordering_by_position(self, active_product):
        ProductImage.objects.create(
            product=active_product, url="https://example.com/a.jpg", position=2
        )
        ProductImage.objects.create(
            product=active_product, url="https://example.com/b.jpg", position=0
        )
        images = list(active_product.images.all())
        assert images[0].position <= images[1].position
