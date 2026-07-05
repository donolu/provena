from apps.catalogue.models import Category


class TestCategoryViews:
    def test_list_categories_public(self, client, category, subcategory):
        response = client.get("/api/v1/catalogue/categories/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["slug"] == "fresh-produce"
        assert len(data[0]["children"]) == 1

    def test_list_categories_inactive_hidden(self, client, category):
        category.is_active = False
        category.save()
        response = client.get("/api/v1/catalogue/categories/")
        assert response.status_code == 200
        assert response.json() == []

    def test_category_detail(self, client, category):
        response = client.get(f"/api/v1/catalogue/categories/{category.slug}/")
        assert response.status_code == 200
        assert response.json()["name"] == "Fresh Produce"

    def test_category_detail_not_found(self, client, db):
        response = client.get("/api/v1/catalogue/categories/nonexistent/")
        assert response.status_code == 404


class TestAdminCategoryViews:
    def test_create_category(self, admin_client):
        response = admin_client.post(
            "/api/v1/catalogue/admin/categories/",
            {"name": "Dairy", "description": "Milk and cheese"},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["slug"] == "dairy"

    def test_create_subcategory(self, admin_client, category):
        response = admin_client.post(
            "/api/v1/catalogue/admin/categories/",
            {"name": "Leafy Greens", "parent": category.slug},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["parent_slug"] == category.slug

    def test_create_category_requires_admin(self, supplier_client):
        response = supplier_client.post(
            "/api/v1/catalogue/admin/categories/",
            {"name": "Grains"},
            format="json",
        )
        assert response.status_code == 403

    def test_update_category(self, admin_client, category):
        response = admin_client.patch(
            f"/api/v1/catalogue/admin/categories/{category.slug}/",
            {"description": "Updated"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Updated"

    def test_delete_category(self, admin_client, category):
        response = admin_client.delete(f"/api/v1/catalogue/admin/categories/{category.slug}/")
        assert response.status_code == 204
        assert not Category.objects.filter(slug=category.slug).exists()


class TestProductListCreate:
    def test_public_list_shows_active_only(self, client, active_product, draft_product):
        response = client.get("/api/v1/catalogue/products/")
        assert response.status_code == 200
        slugs = [p["slug"] for p in response.json()["results"]]
        assert "organic-carrots" in slugs
        assert "heritage-tomatoes" not in slugs

    def test_filter_by_category(self, client, active_product, category):
        response = client.get(f"/api/v1/catalogue/products/?category={category.slug}")
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_filter_by_supplier(self, client, active_product, approved_supplier):
        response = client.get(f"/api/v1/catalogue/products/?supplier={approved_supplier.slug}")
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_search_by_name(self, client, active_product):
        response = client.get("/api/v1/catalogue/products/?search=Carrot")
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_search_no_match(self, client, active_product):
        response = client.get("/api/v1/catalogue/products/?search=Broccoli")
        assert response.status_code == 200
        assert response.json()["count"] == 0

    def test_featured_filter(self, client, active_product):
        active_product.is_featured = True
        active_product.save()
        response = client.get("/api/v1/catalogue/products/?featured=true")
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_create_product_as_supplier(self, supplier_client, category):
        response = supplier_client.post(
            "/api/v1/catalogue/products/",
            {"name": "Fresh Spinach", "category": category.slug},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["status"] == "DRAFT"
        assert response.json()["slug"] == "fresh-spinach"

    def test_create_product_requires_approved_supplier(self, buyer_client):
        response = buyer_client.post(
            "/api/v1/catalogue/products/",
            {"name": "Anything"},
            format="json",
        )
        assert response.status_code == 403

    def test_create_product_unauthenticated(self, client):
        response = client.post("/api/v1/catalogue/products/", {"name": "Anything"}, format="json")
        assert response.status_code == 401


class TestProductDetail:
    def test_public_detail_active(self, client, active_product):
        response = client.get(f"/api/v1/catalogue/products/{active_product.slug}/")
        assert response.status_code == 200
        assert response.json()["name"] == "Organic Carrots"

    def test_public_detail_draft_returns_404(self, client, draft_product):
        response = client.get(f"/api/v1/catalogue/products/{draft_product.slug}/")
        assert response.status_code == 404

    def test_update_own_product(self, supplier_client, draft_product):
        response = supplier_client.patch(
            f"/api/v1/catalogue/products/{draft_product.slug}/",
            {"description": "Freshly picked heirloom tomatoes"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Freshly picked heirloom tomatoes"

    def test_cannot_update_other_suppliers_product(self, second_supplier_client, active_product):
        response = second_supplier_client.patch(
            f"/api/v1/catalogue/products/{active_product.slug}/",
            {"description": "Hacked"},
            format="json",
        )
        assert response.status_code == 404


class TestProductPublishArchive:
    def test_publish_draft(self, supplier_client, draft_product):
        response = supplier_client.post(f"/api/v1/catalogue/products/{draft_product.slug}/publish/")
        assert response.status_code == 200
        assert response.json()["status"] == "ACTIVE"

    def test_publish_archived_returns_400(self, supplier_client, draft_product):
        from apps.catalogue import services

        services.archive_product(draft_product)
        response = supplier_client.post(f"/api/v1/catalogue/products/{draft_product.slug}/publish/")
        assert response.status_code == 400

    def test_archive_product(self, supplier_client, active_product):
        response = supplier_client.post(
            f"/api/v1/catalogue/products/{active_product.slug}/archive/"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ARCHIVED"

    def test_cannot_publish_other_suppliers_product(self, second_supplier_client, draft_product):
        response = second_supplier_client.post(
            f"/api/v1/catalogue/products/{draft_product.slug}/publish/"
        )
        assert response.status_code == 404


class TestSupplierProductList:
    def test_list_own_products(self, supplier_client, active_product, draft_product):
        response = supplier_client.get("/api/v1/catalogue/products/me/")
        assert response.status_code == 200
        slugs = [p["slug"] for p in response.json()["results"]]
        assert "organic-carrots" in slugs
        assert "heritage-tomatoes" in slugs

    def test_filter_by_status(self, supplier_client, active_product, draft_product):
        response = supplier_client.get("/api/v1/catalogue/products/me/?status=DRAFT")
        assert response.status_code == 200
        assert all(p["status"] == "DRAFT" for p in response.json()["results"])

    def test_requires_approved_supplier(self, buyer_client):
        response = buyer_client.get("/api/v1/catalogue/products/me/")
        assert response.status_code == 403


class TestVariantViews:
    def test_add_variant(self, supplier_client, draft_product):
        response = supplier_client.post(
            f"/api/v1/catalogue/products/{draft_product.slug}/variants/",
            {"name": "250g", "sku": "TOM-250G", "price": "1.99", "weight_grams": 250},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["sku"] == "TOM-250G"

    def test_add_variant_duplicate_sku(self, supplier_client, draft_product, variant):
        response = supplier_client.post(
            f"/api/v1/catalogue/products/{draft_product.slug}/variants/",
            {"name": "Dupe", "sku": "CARR-1KG", "price": "1.00"},
            format="json",
        )
        assert response.status_code == 400

    def test_compare_at_price_must_be_higher(self, supplier_client, draft_product):
        response = supplier_client.post(
            f"/api/v1/catalogue/products/{draft_product.slug}/variants/",
            {
                "name": "1kg",
                "sku": "TOM-1KG",
                "price": "5.00",
                "compare_at_price": "3.00",
            },
            format="json",
        )
        assert response.status_code == 400

    def test_update_variant(self, supplier_client, active_product, variant):
        response = supplier_client.patch(
            f"/api/v1/catalogue/products/{active_product.slug}/variants/{variant.id}/",
            {"price": "4.50"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["price"] == "4.50"

    def test_delete_variant(self, supplier_client, active_product, variant):
        response = supplier_client.delete(
            f"/api/v1/catalogue/products/{active_product.slug}/variants/{variant.id}/"
        )
        assert response.status_code == 204

    def test_cannot_add_variant_to_other_product(self, second_supplier_client, active_product):
        response = second_supplier_client.post(
            f"/api/v1/catalogue/products/{active_product.slug}/variants/",
            {"name": "1kg", "sku": "HACK-1KG", "price": "1.00"},
            format="json",
        )
        assert response.status_code == 404


class TestImageViews:
    def test_add_image(self, supplier_client, draft_product):
        response = supplier_client.post(
            f"/api/v1/catalogue/products/{draft_product.slug}/images/",
            {"url": "https://example.com/tomato.jpg", "alt_text": "Tomato", "is_primary": True},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["is_primary"] is True

    def test_set_primary_clears_others(self, supplier_client, active_product, image):
        assert image.is_primary is True
        response = supplier_client.post(
            f"/api/v1/catalogue/products/{active_product.slug}/images/",
            {"url": "https://example.com/new.jpg", "is_primary": True},
            format="json",
        )
        assert response.status_code == 201
        image.refresh_from_db()
        assert image.is_primary is False

    def test_delete_image(self, supplier_client, active_product, image):
        response = supplier_client.delete(
            f"/api/v1/catalogue/products/{active_product.slug}/images/{image.id}/"
        )
        assert response.status_code == 204

    def test_cannot_delete_other_suppliers_image(
        self, second_supplier_client, active_product, image
    ):
        response = second_supplier_client.delete(
            f"/api/v1/catalogue/products/{active_product.slug}/images/{image.id}/"
        )
        assert response.status_code == 404


class TestAdminProductViews:
    def test_admin_list_all_statuses(self, admin_client, active_product, draft_product):
        response = admin_client.get("/api/v1/catalogue/admin/products/")
        assert response.status_code == 200
        slugs = [p["slug"] for p in response.json()]
        assert "organic-carrots" in slugs
        assert "heritage-tomatoes" in slugs

    def test_admin_filter_by_status(self, admin_client, active_product, draft_product):
        response = admin_client.get("/api/v1/catalogue/admin/products/?status=DRAFT")
        assert response.status_code == 200
        assert all(p["status"] == "DRAFT" for p in response.json())

    def test_feature_product(self, admin_client, active_product):
        response = admin_client.post(
            f"/api/v1/catalogue/admin/products/{active_product.slug}/feature/"
        )
        assert response.status_code == 200
        assert response.json()["is_featured"] is True

    def test_unfeature_product(self, admin_client, active_product):
        active_product.is_featured = True
        active_product.save()
        response = admin_client.post(
            f"/api/v1/catalogue/admin/products/{active_product.slug}/feature/"
        )
        assert response.status_code == 200
        assert response.json()["is_featured"] is False

    def test_admin_product_list_requires_admin(self, supplier_client):
        response = supplier_client.get("/api/v1/catalogue/admin/products/")
        assert response.status_code == 403


class TestAdminProductBulkAction:
    URL = "/api/v1/catalogue/admin/products/bulk/"

    def test_bulk_set_status(self, admin_client, active_product, draft_product):
        response = admin_client.post(
            self.URL,
            {
                "slugs": [active_product.slug, draft_product.slug],
                "action": "set_status",
                "status": "ARCHIVED",
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["updated"] == 2
        active_product.refresh_from_db()
        draft_product.refresh_from_db()
        assert active_product.status == "ARCHIVED"
        assert draft_product.status == "ARCHIVED"

    def test_bulk_set_featured(self, admin_client, active_product, draft_product):
        response = admin_client.post(
            self.URL,
            {
                "slugs": [active_product.slug, draft_product.slug],
                "action": "set_featured",
                "is_featured": True,
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["updated"] == 2
        active_product.refresh_from_db()
        assert active_product.is_featured is True

    def test_bulk_unfeature(self, admin_client, active_product):
        active_product.is_featured = True
        active_product.save()
        response = admin_client.post(
            self.URL,
            {"slugs": [active_product.slug], "action": "set_featured", "is_featured": False},
            format="json",
        )
        assert response.status_code == 200
        active_product.refresh_from_db()
        assert active_product.is_featured is False

    def test_bulk_set_category(self, admin_client, active_product, subcategory):
        response = admin_client.post(
            self.URL,
            {
                "slugs": [active_product.slug],
                "action": "set_category",
                "category": subcategory.slug,
            },
            format="json",
        )
        assert response.status_code == 200
        active_product.refresh_from_db()
        assert active_product.category_id == subcategory.id

    def test_bulk_clear_category(self, admin_client, active_product):
        response = admin_client.post(
            self.URL,
            {"slugs": [active_product.slug], "action": "set_category", "category": None},
            format="json",
        )
        assert response.status_code == 200
        active_product.refresh_from_db()
        assert active_product.category is None

    def test_missing_status_for_set_status(self, admin_client, active_product):
        response = admin_client.post(
            self.URL,
            {"slugs": [active_product.slug], "action": "set_status"},
            format="json",
        )
        assert response.status_code == 400

    def test_missing_is_featured_for_set_featured(self, admin_client, active_product):
        response = admin_client.post(
            self.URL,
            {"slugs": [active_product.slug], "action": "set_featured"},
            format="json",
        )
        assert response.status_code == 400

    def test_empty_slugs_rejected(self, admin_client):
        response = admin_client.post(
            self.URL,
            {"slugs": [], "action": "set_status", "status": "ACTIVE"},
            format="json",
        )
        assert response.status_code == 400

    def test_unknown_slugs_update_zero(self, admin_client):
        response = admin_client.post(
            self.URL,
            {"slugs": ["does-not-exist"], "action": "set_status", "status": "ACTIVE"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["updated"] == 0

    def test_requires_admin(self, supplier_client, active_product):
        response = supplier_client.post(
            self.URL,
            {"slugs": [active_product.slug], "action": "set_status", "status": "ACTIVE"},
            format="json",
        )
        assert response.status_code == 403
