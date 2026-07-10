from decimal import Decimal

from rest_framework.test import APIClient

from apps.marketplace import services
from apps.marketplace.models import CartItem


class TestCartView:
    def test_get_empty_cart(self, buyer_client, buyer):
        response = buyer_client.get("/api/v1/marketplace/cart/")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert Decimal(data["total"]) == Decimal("0.00")
        assert data["item_count"] == 0

    def test_get_cart_with_items(self, buyer_client, buyer, variant):
        services.add_to_cart(user=buyer, variant_id=variant.id, quantity=2)
        response = buyer_client.get("/api/v1/marketplace/cart/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2

    def test_clear_cart(self, buyer_client, buyer, variant):
        services.add_to_cart(user=buyer, variant_id=variant.id, quantity=3)
        response = buyer_client.delete("/api/v1/marketplace/cart/")
        assert response.status_code == 204
        assert CartItem.objects.filter(cart__buyer=buyer).count() == 0

    def test_unauthenticated_returns_empty_cart(self):
        response = APIClient().get("/api/v1/marketplace/cart/")
        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_guest_add_sets_cookie(self, variant):
        client = APIClient()
        response = client.post(
            "/api/v1/marketplace/cart/items/",
            {"variant_id": str(variant.id), "quantity": 1},
            format="json",
        )
        assert response.status_code == 201
        assert "provena_cart" in response.cookies

    def test_guest_cart_persists_via_cookie(self, variant):
        client = APIClient()
        add_resp = client.post(
            "/api/v1/marketplace/cart/items/",
            {"variant_id": str(variant.id), "quantity": 2},
            format="json",
        )
        cart_cookie = add_resp.cookies.get("provena_cart")
        assert cart_cookie is not None
        client.cookies["provena_cart"] = cart_cookie.value
        get_resp = client.get("/api/v1/marketplace/cart/")
        assert get_resp.json()["item_count"] == 1
        assert get_resp.json()["items"][0]["quantity"] == 2


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
        services.add_to_cart(user=buyer, variant_id=variant.id, quantity=2)
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

    def test_unauthenticated_add_creates_guest_cart(self, variant):
        response = APIClient().post(
            "/api/v1/marketplace/cart/items/",
            {"variant_id": str(variant.id), "quantity": 1},
            format="json",
        )
        assert response.status_code == 201


class TestCartItemDetailView:
    def test_update_quantity(self, buyer_client, buyer, variant):
        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=2)
        response = buyer_client.patch(
            f"/api/v1/marketplace/cart/items/{item.id}/",
            {"quantity": 7},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["quantity"] == 7

    def test_update_zero_returns_400(self, buyer_client, buyer, variant):
        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=2)
        response = buyer_client.patch(
            f"/api/v1/marketplace/cart/items/{item.id}/",
            {"quantity": 0},
            format="json",
        )
        assert response.status_code == 400

    def test_update_other_buyers_item_returns_404(self, second_buyer_client, buyer, variant):
        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=2)
        response = second_buyer_client.patch(
            f"/api/v1/marketplace/cart/items/{item.id}/",
            {"quantity": 5},
            format="json",
        )
        assert response.status_code == 404

    def test_delete_item(self, buyer_client, buyer, variant):
        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=1)
        response = buyer_client.delete(f"/api/v1/marketplace/cart/items/{item.id}/")
        assert response.status_code == 204
        assert CartItem.objects.filter(id=item.id).count() == 0

    def test_delete_other_buyers_item_returns_404(self, second_buyer_client, buyer, variant):
        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=1)
        response = second_buyer_client.delete(f"/api/v1/marketplace/cart/items/{item.id}/")
        assert response.status_code == 404


class TestCartMergeView:
    def test_merge_requires_auth(self):
        response = APIClient().post("/api/v1/marketplace/cart/merge/")
        assert response.status_code == 401

    def test_merge_noop_when_no_cookie(self, buyer_client):
        response = buyer_client.post("/api/v1/marketplace/cart/merge/")
        assert response.status_code == 200
        assert response.json()["merged"] is False

    def test_merge_transfers_guest_items(self, buyer_client, buyer, variant):
        key = services.new_session_key()
        services.add_to_cart(session_key=key, variant_id=variant.id, quantity=3)
        buyer_client.cookies["provena_cart"] = key
        response = buyer_client.post("/api/v1/marketplace/cart/merge/")
        assert response.status_code == 200
        assert response.json()["merged"] is True
        assert CartItem.objects.filter(cart__buyer=buyer, variant=variant).get().quantity == 3

    def test_merge_clears_cookie(self, buyer_client, buyer, variant):
        key = services.new_session_key()
        services.add_to_cart(session_key=key, variant_id=variant.id, quantity=1)
        buyer_client.cookies["provena_cart"] = key
        response = buyer_client.post("/api/v1/marketplace/cart/merge/")
        assert response.cookies.get("provena_cart").value == ""


class TestWishlistView:
    def test_list_empty(self, buyer_client):
        response = buyer_client.get("/api/v1/marketplace/wishlist/")
        assert response.status_code == 200
        assert response.json()["results"] == []
