from decimal import Decimal

import pytest

from apps.catalogue import services
from apps.catalogue.models import Category, ProductStatus


class TestCategoryServices:
    def test_create_category(self, db):
        cat = services.create_category(name="Bakery", description="Fresh bread and pastries")
        assert cat.name == "Bakery"
        assert cat.slug == "bakery"
        assert cat.parent is None

    def test_create_subcategory(self, category):
        sub = services.create_category(name="Root Vegetables", parent=category)
        assert sub.parent == category
        assert sub in category.children.all()

    def test_create_category_slug_collision(self, db):
        services.create_category(name="Fruit")
        cat2 = services.create_category(name="Fruit")
        assert cat2.slug == "fruit-1"

    def test_update_category(self, category):
        updated = services.update_category(category, description="Updated description")
        assert updated.description == "Updated description"

    def test_delete_category(self, category):
        cat_id = category.id
        services.delete_category(category)
        assert not Category.objects.filter(id=cat_id).exists()

    def test_delete_category_nullifies_product_category(self, active_product, category):
        services.delete_category(category)
        active_product.refresh_from_db()
        assert active_product.category is None


class TestProductServices:
    def test_create_product(self, approved_supplier, category):
        product = services.create_product(
            supplier=approved_supplier,
            name="Organic Kale",
            category=category,
        )
        assert product.name == "Organic Kale"
        assert product.status == ProductStatus.DRAFT
        assert product.slug == "organic-kale"

    def test_create_product_slug_collision(self, approved_supplier, category):
        services.create_product(supplier=approved_supplier, name="Kale", category=category)
        p2 = services.create_product(supplier=approved_supplier, name="Kale", category=category)
        assert p2.slug == "kale-1"

    def test_update_product_name(self, active_product):
        services.update_product(active_product, name="Updated Carrots")
        active_product.refresh_from_db()
        assert active_product.name == "Updated Carrots"

    def test_publish_draft(self, draft_product):
        services.publish_product(draft_product)
        draft_product.refresh_from_db()
        assert draft_product.status == ProductStatus.ACTIVE

    def test_publish_already_active(self, active_product):
        services.publish_product(active_product)
        active_product.refresh_from_db()
        assert active_product.status == ProductStatus.ACTIVE

    def test_publish_archived_raises(self, active_product):
        services.archive_product(active_product)
        with pytest.raises(ValueError, match="Archived"):
            services.publish_product(active_product)

    def test_archive_product(self, active_product):
        services.archive_product(active_product)
        active_product.refresh_from_db()
        assert active_product.status == ProductStatus.ARCHIVED

    def test_feature_product(self, active_product, admin_user):
        services.feature_product(active_product, admin_user)
        active_product.refresh_from_db()
        assert active_product.is_featured is True

    def test_unfeature_product(self, active_product, admin_user):
        services.feature_product(active_product, admin_user)
        services.unfeature_product(active_product, admin_user)
        active_product.refresh_from_db()
        assert active_product.is_featured is False


class TestVariantServices:
    def test_add_variant(self, active_product):
        v = services.add_variant(
            product=active_product,
            name="500g",
            sku="CARR-500G",
            price=Decimal("2.49"),
            weight_grams=500,
        )
        assert v.sku == "CARR-500G"
        assert v.price == Decimal("2.49")

    def test_add_variant_duplicate_sku(self, active_product, variant):
        with pytest.raises(ValueError, match="SKU"):
            services.add_variant(
                product=active_product, name="Dupe", sku="CARR-1KG", price=Decimal("1.00")
            )

    def test_update_variant(self, variant):
        services.update_variant(variant, price=Decimal("4.50"))
        variant.refresh_from_db()
        assert variant.price == Decimal("4.50")

    def test_update_variant_sku_collision(self, active_product, variant):
        v2 = services.add_variant(
            product=active_product, name="2kg", sku="CARR-2KG", price=Decimal("7.00")
        )
        with pytest.raises(ValueError, match="SKU"):
            services.update_variant(v2, sku="CARR-1KG")

    def test_remove_variant(self, variant):
        v_id = variant.id
        services.remove_variant(variant)
        from apps.catalogue.models import ProductVariant

        assert not ProductVariant.objects.filter(id=v_id).exists()


class TestImageServices:
    def test_add_image(self, active_product):
        img = services.add_image(
            product=active_product,
            url="https://example.com/img.jpg",
            alt_text="Test image",
            is_primary=True,
        )
        assert img.is_primary is True
        assert img.url == "https://example.com/img.jpg"

    def test_add_primary_image_clears_others(self, active_product, image):
        assert image.is_primary is True
        new_img = services.add_image(
            product=active_product,
            url="https://example.com/new.jpg",
            is_primary=True,
        )
        image.refresh_from_db()
        assert image.is_primary is False
        assert new_img.is_primary is True

    def test_add_image_auto_position(self, active_product, image):
        img2 = services.add_image(product=active_product, url="https://example.com/b.jpg")
        assert img2.position == image.position + 1

    def test_update_image_set_primary(self, active_product, image):
        img2 = services.add_image(product=active_product, url="https://example.com/b.jpg")
        services.update_image(img2, is_primary=True)
        image.refresh_from_db()
        img2.refresh_from_db()
        assert image.is_primary is False
        assert img2.is_primary is True

    def test_remove_image(self, image):
        img_id = image.id
        services.remove_image(image)
        from apps.catalogue.models import ProductImage

        assert not ProductImage.objects.filter(id=img_id).exists()
