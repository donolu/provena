"""Tests for per-variant product images (Issue #10)."""

from apps.catalogue import services
from apps.catalogue.models import VariantImage

BASE = "/api/v1/catalogue/products/"


# ---------------------------------------------------------------------------
# Service layer
# ---------------------------------------------------------------------------


class TestAddVariantImageService:
    def test_creates_image(self, variant):
        img = services.add_variant_image(variant, url="https://example.com/red.jpg")
        assert img.variant == variant
        assert img.url == "https://example.com/red.jpg"
        assert img.position == 0
        assert img.is_primary is False

    def test_position_auto_increments(self, variant):
        first = services.add_variant_image(variant, url="https://example.com/a.jpg")
        second = services.add_variant_image(variant, url="https://example.com/b.jpg")
        assert second.position == first.position + 1

    def test_is_primary_clears_others(self, variant):
        existing = services.add_variant_image(
            variant, url="https://example.com/a.jpg", is_primary=True
        )
        assert existing.is_primary is True

        services.add_variant_image(variant, url="https://example.com/b.jpg", is_primary=True)

        existing.refresh_from_db()
        assert existing.is_primary is False

    def test_alt_text_stored(self, variant):
        img = services.add_variant_image(
            variant, url="https://example.com/c.jpg", alt_text="Red variant"
        )
        assert img.alt_text == "Red variant"


class TestUpdateVariantImageService:
    def test_updates_url(self, variant):
        img = services.add_variant_image(variant, url="https://example.com/old.jpg")
        updated = services.update_variant_image(img, url="https://example.com/new.jpg")
        assert updated.url == "https://example.com/new.jpg"

    def test_set_primary_clears_others(self, variant):
        a = services.add_variant_image(variant, url="https://example.com/a.jpg", is_primary=True)
        b = services.add_variant_image(variant, url="https://example.com/b.jpg")

        services.update_variant_image(b, is_primary=True)

        a.refresh_from_db()
        b.refresh_from_db()
        assert a.is_primary is False
        assert b.is_primary is True


class TestRemoveVariantImageService:
    def test_deletes_image(self, variant):
        img = services.add_variant_image(variant, url="https://example.com/x.jpg")
        img_id = img.id
        services.remove_variant_image(img)
        assert not VariantImage.objects.filter(pk=img_id).exists()


# ---------------------------------------------------------------------------
# API — POST /products/<slug>/variants/<pk>/images/
# ---------------------------------------------------------------------------


class TestVariantImageCreate:
    def test_supplier_can_add_image(self, supplier_client, active_product, variant):
        url = f"{BASE}{active_product.slug}/variants/{variant.id}/images/"
        res = supplier_client.post(
            url,
            {"url": "https://cdn.example.com/red-variant.jpg", "alt_text": "Red variant"},
            format="json",
        )
        assert res.status_code == 201
        data = res.json()
        assert data["url"] == "https://cdn.example.com/red-variant.jpg"
        assert data["alt_text"] == "Red variant"
        assert data["is_primary"] is False

    def test_first_image_can_be_primary(self, supplier_client, active_product, variant):
        url = f"{BASE}{active_product.slug}/variants/{variant.id}/images/"
        res = supplier_client.post(
            url,
            {"url": "https://cdn.example.com/primary.jpg", "is_primary": True},
            format="json",
        )
        assert res.status_code == 201
        assert res.json()["is_primary"] is True

    def test_other_supplier_cannot_add(self, second_supplier_client, active_product, variant):
        url = f"{BASE}{active_product.slug}/variants/{variant.id}/images/"
        res = second_supplier_client.post(
            url,
            {"url": "https://cdn.example.com/intruder.jpg"},
            format="json",
        )
        assert res.status_code == 404

    def test_unauthenticated_returns_403(self, api_client, active_product, variant):
        url = f"{BASE}{active_product.slug}/variants/{variant.id}/images/"
        res = api_client.post(url, {"url": "https://cdn.example.com/x.jpg"}, format="json")
        assert res.status_code in (401, 403)

    def test_invalid_url_rejected(self, supplier_client, active_product, variant):
        url = f"{BASE}{active_product.slug}/variants/{variant.id}/images/"
        res = supplier_client.post(url, {"url": "not-a-url"}, format="json")
        assert res.status_code == 400

    def test_nonexistent_variant_returns_404(self, supplier_client, active_product):
        import uuid

        url = f"{BASE}{active_product.slug}/variants/{uuid.uuid4()}/images/"
        res = supplier_client.post(url, {"url": "https://cdn.example.com/x.jpg"}, format="json")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# API — PATCH /products/<slug>/variants/<pk>/images/<img_pk>/
# ---------------------------------------------------------------------------


class TestVariantImageUpdate:
    def test_supplier_can_update_image(self, supplier_client, active_product, variant):
        img = services.add_variant_image(variant, url="https://cdn.example.com/old.jpg")
        url = f"{BASE}{active_product.slug}/variants/{variant.id}/images/{img.id}/"
        res = supplier_client.patch(url, {"url": "https://cdn.example.com/new.jpg"}, format="json")
        assert res.status_code == 200
        assert res.json()["url"] == "https://cdn.example.com/new.jpg"

    def test_setting_primary_clears_others(self, supplier_client, active_product, variant):
        a = services.add_variant_image(
            variant, url="https://cdn.example.com/a.jpg", is_primary=True
        )
        b = services.add_variant_image(variant, url="https://cdn.example.com/b.jpg")

        url = f"{BASE}{active_product.slug}/variants/{variant.id}/images/{b.id}/"
        res = supplier_client.patch(url, {"is_primary": True}, format="json")

        assert res.status_code == 200
        a.refresh_from_db()
        assert a.is_primary is False
        assert res.json()["is_primary"] is True

    def test_other_supplier_cannot_update(self, second_supplier_client, active_product, variant):
        img = services.add_variant_image(variant, url="https://cdn.example.com/a.jpg")
        url = f"{BASE}{active_product.slug}/variants/{variant.id}/images/{img.id}/"
        res = second_supplier_client.patch(url, {"alt_text": "Intruder"}, format="json")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# API — DELETE /products/<slug>/variants/<pk>/images/<img_pk>/
# ---------------------------------------------------------------------------


class TestVariantImageDelete:
    def test_supplier_can_delete_image(self, supplier_client, active_product, variant):
        img = services.add_variant_image(variant, url="https://cdn.example.com/x.jpg")
        url = f"{BASE}{active_product.slug}/variants/{variant.id}/images/{img.id}/"
        res = supplier_client.delete(url)
        assert res.status_code == 204
        assert not VariantImage.objects.filter(pk=img.id).exists()

    def test_other_supplier_cannot_delete(self, second_supplier_client, active_product, variant):
        img = services.add_variant_image(variant, url="https://cdn.example.com/x.jpg")
        url = f"{BASE}{active_product.slug}/variants/{variant.id}/images/{img.id}/"
        res = second_supplier_client.delete(url)
        assert res.status_code == 404
        assert VariantImage.objects.filter(pk=img.id).exists()


# ---------------------------------------------------------------------------
# Variant images appear inline in product responses
# ---------------------------------------------------------------------------


class TestVariantImagesInProductResponse:
    def test_images_field_present_on_variant(self, api_client, active_product, variant):
        services.add_variant_image(variant, url="https://cdn.example.com/colour.jpg")
        res = api_client.get(f"{BASE}{active_product.slug}/")
        assert res.status_code == 200
        variants = res.json()["variants"]
        assert len(variants) == 1
        assert "images" in variants[0]
        assert len(variants[0]["images"]) == 1
        assert variants[0]["images"][0]["url"] == "https://cdn.example.com/colour.jpg"

    def test_empty_images_list_when_no_variant_images(self, api_client, active_product, variant):
        res = api_client.get(f"{BASE}{active_product.slug}/")
        assert res.status_code == 200
        variant_data = res.json()["variants"][0]
        assert variant_data["images"] == []
