from decimal import Decimal

from rest_framework.test import APIClient

from apps.marketplace import services
from apps.marketplace.models import CartItem, Review, WishlistItem


class TestCartView:
    def test_get_empty_cart(self, buyer_client, buyer):
        response = buyer_client.get("/api/v1/marketplace/cart/")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert Decimal(data["total"]) == Decimal("0.00")
        assert data["item_count"] == 0

    def test_get_cart_with_items(self, buyer_client, buyer, variant):
        services.add_to_cart(buyer, variant.id, 2)
        response = buyer_client.get("/api/v1/marketplace/cart/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2

    def test_clear_cart(self, buyer_client, buyer, variant):
        services.add_to_cart(buyer, variant.id, 3)
        response = buyer_client.delete("/api/v1/marketplace/cart/")
        assert response.status_code == 204
        assert CartItem.objects.filter(cart__buyer=buyer).count() == 0

    def test_unauthenticated(self):
        response = APIClient().get("/api/v1/marketplace/cart/")
        assert response.status_code == 401


class TestCartItemCreateView:
    def test_add_item(self, buyer_client, variant):
        response = buyer_client.post(
            "/api/v1/marketplace/cart/items/",
            {"variant_id": str(variant.id), "quantity": 3},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["quantity"] == 3
        assert response.json()["variant_sku"] == "CARR-1KG"

    def test_add_increments_existing(self, buyer_client, buyer, variant):
        services.add_to_cart(buyer, variant.id, 2)
        response = buyer_client.post(
            "/api/v1/marketplace/cart/items/",
            {"variant_id": str(variant.id), "quantity": 3},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["quantity"] == 5

    def test_add_inactive_variant_returns_404(self, buyer_client, variant):
        variant.is_active = False
        variant.save()
        response = buyer_client.post(
            "/api/v1/marketplace/cart/items/",
            {"variant_id": str(variant.id), "quantity": 1},
            format="json",
        )
        assert response.status_code == 404

    def test_add_zero_quantity_returns_400(self, buyer_client, variant):
        response = buyer_client.post(
            "/api/v1/marketplace/cart/items/",
            {"variant_id": str(variant.id), "quantity": 0},
            format="json",
        )
        assert response.status_code == 400

    def test_unauthenticated(self, variant):
        response = APIClient().post(
            "/api/v1/marketplace/cart/items/",
            {"variant_id": str(variant.id), "quantity": 1},
            format="json",
        )
        assert response.status_code == 401


class TestCartItemDetailView:
    def test_update_quantity(self, buyer_client, buyer, variant):
        item = services.add_to_cart(buyer, variant.id, 2)
        response = buyer_client.patch(
            f"/api/v1/marketplace/cart/items/{item.id}/",
            {"quantity": 7},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["quantity"] == 7

    def test_update_zero_returns_400(self, buyer_client, buyer, variant):
        item = services.add_to_cart(buyer, variant.id, 2)
        response = buyer_client.patch(
            f"/api/v1/marketplace/cart/items/{item.id}/",
            {"quantity": 0},
            format="json",
        )
        assert response.status_code == 400

    def test_update_other_buyers_item_returns_404(self, second_buyer_client, buyer, variant):
        item = services.add_to_cart(buyer, variant.id, 2)
        response = second_buyer_client.patch(
            f"/api/v1/marketplace/cart/items/{item.id}/",
            {"quantity": 5},
            format="json",
        )
        assert response.status_code == 404

    def test_delete_item(self, buyer_client, buyer, variant):
        item = services.add_to_cart(buyer, variant.id, 1)
        response = buyer_client.delete(f"/api/v1/marketplace/cart/items/{item.id}/")
        assert response.status_code == 204
        assert CartItem.objects.filter(id=item.id).count() == 0

    def test_delete_other_buyers_item_returns_404(self, second_buyer_client, buyer, variant):
        item = services.add_to_cart(buyer, variant.id, 1)
        response = second_buyer_client.delete(f"/api/v1/marketplace/cart/items/{item.id}/")
        assert response.status_code == 404


class TestWishlistView:
    def test_list_empty(self, buyer_client):
        response = buyer_client.get("/api/v1/marketplace/wishlist/")
        assert response.status_code == 200
        assert response.json() == []

    def test_add_to_wishlist(self, buyer_client, variant):
        response = buyer_client.post(
            "/api/v1/marketplace/wishlist/",
            {"variant_id": str(variant.id)},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["variant_sku"] == "CARR-1KG"

    def test_add_idempotent(self, buyer_client, buyer, variant):
        services.add_to_wishlist(buyer, variant.id)
        response = buyer_client.post(
            "/api/v1/marketplace/wishlist/",
            {"variant_id": str(variant.id)},
            format="json",
        )
        assert response.status_code == 201
        assert WishlistItem.objects.filter(buyer=buyer, variant=variant).count() == 1

    def test_list_own_items(self, buyer_client, buyer, variant, second_variant):
        services.add_to_wishlist(buyer, variant.id)
        services.add_to_wishlist(buyer, second_variant.id)
        response = buyer_client.get("/api/v1/marketplace/wishlist/")
        assert len(response.json()) == 2

    def test_does_not_show_other_buyers_wishlist(self, second_buyer_client, buyer, variant):
        services.add_to_wishlist(buyer, variant.id)
        response = second_buyer_client.get("/api/v1/marketplace/wishlist/")
        assert response.json() == []

    def test_add_inactive_variant_returns_404(self, buyer_client, variant):
        variant.is_active = False
        variant.save()
        response = buyer_client.post(
            "/api/v1/marketplace/wishlist/",
            {"variant_id": str(variant.id)},
            format="json",
        )
        assert response.status_code == 404

    def test_unauthenticated(self):
        response = APIClient().get("/api/v1/marketplace/wishlist/")
        assert response.status_code == 401


class TestWishlistItemDeleteView:
    def test_remove_item(self, buyer_client, buyer, variant):
        item = services.add_to_wishlist(buyer, variant.id)
        response = buyer_client.delete(f"/api/v1/marketplace/wishlist/{item.id}/")
        assert response.status_code == 204
        assert WishlistItem.objects.filter(id=item.id).count() == 0

    def test_remove_other_buyers_item_returns_404(self, second_buyer_client, buyer, variant):
        item = services.add_to_wishlist(buyer, variant.id)
        response = second_buyer_client.delete(f"/api/v1/marketplace/wishlist/{item.id}/")
        assert response.status_code == 404


class TestProductReviewListCreateView:
    def test_list_approved_reviews_public(self, variant, buyer):
        review = Review.objects.create(
            variant=variant,
            reviewer=buyer,
            rating=5,
            title="Great",
            body="Loved it",
            is_verified_purchase=True,
            is_approved=True,
        )
        services.approve_review(review)
        response = APIClient().get(f"/api/v1/marketplace/products/{variant.id}/reviews/")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_unapproved_not_in_public_list(self, variant, buyer):
        Review.objects.create(
            variant=variant,
            reviewer=buyer,
            rating=4,
            title="Good",
            body="Nice",
            is_verified_purchase=True,
            is_approved=False,
        )
        response = APIClient().get(f"/api/v1/marketplace/products/{variant.id}/reviews/")
        assert response.json() == []

    def test_unverified_buyer_cannot_submit_review(self, buyer_client, variant):
        response = buyer_client.post(
            f"/api/v1/marketplace/products/{variant.id}/reviews/",
            {"rating": 4, "title": "Good product", "body": "Would buy again."},
            format="json",
        )
        assert response.status_code == 400
        assert "purchased and received" in response.json()["detail"]

    def test_verified_purchaser_can_submit_review(
        self, buyer_client, buyer, variant, delivered_order
    ):
        response = buyer_client.post(
            f"/api/v1/marketplace/products/{variant.id}/reviews/",
            {"rating": 5, "title": "Perfect", "body": "Excellent quality."},
            format="json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == 5
        assert data["is_approved"] is False
        assert data["is_verified_purchase"] is True

    def test_duplicate_review_returns_400(self, buyer_client, buyer, variant, delivered_order):
        services.create_review(buyer, variant.id, 3, "OK", "Fine")
        response = buyer_client.post(
            f"/api/v1/marketplace/products/{variant.id}/reviews/",
            {"rating": 4, "title": "Changed mind", "body": "Actually better."},
            format="json",
        )
        assert response.status_code == 400

    def test_submit_requires_auth(self, variant):
        response = APIClient().post(
            f"/api/v1/marketplace/products/{variant.id}/reviews/",
            {"rating": 5, "title": "X", "body": "Y"},
            format="json",
        )
        assert response.status_code == 401

    def test_invalid_rating_returns_400(self, buyer_client, variant):
        response = buyer_client.post(
            f"/api/v1/marketplace/products/{variant.id}/reviews/",
            {"rating": 6, "title": "X", "body": "Y"},
            format="json",
        )
        assert response.status_code == 400


class TestAdminReviewViews:
    def _make_review(self, buyer, variant, rating=3, title="OK", body="Fine", approved=False):
        return Review.objects.create(
            variant=variant,
            reviewer=buyer,
            rating=rating,
            title=title,
            body=body,
            is_verified_purchase=True,
            is_approved=approved,
        )

    def test_list_all_reviews(self, admin_client, buyer, variant):
        self._make_review(buyer, variant)
        response = admin_client.get("/api/v1/marketplace/admin/reviews/")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_filter_approved(self, admin_client, buyer, variant):
        review = self._make_review(buyer, variant, rating=4, title="Good", body="Nice")
        services.approve_review(review)
        response = admin_client.get("/api/v1/marketplace/admin/reviews/?is_approved=true")
        assert len(response.json()) == 1
        response2 = admin_client.get("/api/v1/marketplace/admin/reviews/?is_approved=false")
        assert response2.json() == []

    def test_filter_by_variant(self, admin_client, buyer, second_buyer, variant, second_variant):
        self._make_review(buyer, variant, rating=4, title="Good", body="Nice")
        self._make_review(second_buyer, second_variant, rating=3, title="OK", body="Fine")
        response = admin_client.get(f"/api/v1/marketplace/admin/reviews/?variant={variant.id}")
        assert len(response.json()) == 1

    def test_approve_review(self, admin_client, buyer, variant):
        review = self._make_review(buyer, variant, rating=5, title="Great", body="Awesome")
        response = admin_client.post(f"/api/v1/marketplace/admin/reviews/{review.id}/approve/")
        assert response.status_code == 200
        assert response.json()["is_approved"] is True

    def test_delete_review(self, admin_client, buyer, variant):
        review = self._make_review(buyer, variant, rating=2, title="Bad", body="Not good")
        response = admin_client.delete(f"/api/v1/marketplace/admin/reviews/{review.id}/")
        assert response.status_code == 204
        assert Review.objects.filter(id=review.id).count() == 0

    def test_requires_admin(self, buyer_client):
        response = buyer_client.get("/api/v1/marketplace/admin/reviews/")
        assert response.status_code == 403
