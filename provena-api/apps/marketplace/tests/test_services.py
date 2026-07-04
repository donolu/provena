import pytest
from django.http import Http404

from apps.marketplace import services
from apps.marketplace.models import CartItem, WishlistItem


class TestCart:
    def test_get_or_create_cart(self, buyer):
        cart = services.get_or_create_cart(buyer)
        assert cart.buyer == buyer

    def test_get_or_create_cart_idempotent(self, buyer):
        c1 = services.get_or_create_cart(buyer)
        c2 = services.get_or_create_cart(buyer)
        assert c1.id == c2.id

    def test_add_to_cart(self, buyer, variant):
        item = services.add_to_cart(buyer, variant.id, 3)
        assert item.quantity == 3
        assert item.variant == variant

    def test_add_increments_existing(self, buyer, variant):
        services.add_to_cart(buyer, variant.id, 2)
        services.add_to_cart(buyer, variant.id, 3)
        item = CartItem.objects.get(cart__buyer=buyer, variant=variant)
        assert item.quantity == 5

    def test_add_inactive_variant_raises(self, buyer, variant):
        variant.is_active = False
        variant.save()
        with pytest.raises(Http404):
            services.add_to_cart(buyer, variant.id, 1)

    def test_add_zero_quantity_raises(self, buyer, variant):
        with pytest.raises(ValueError, match="at least 1"):
            services.add_to_cart(buyer, variant.id, 0)

    def test_update_cart_item(self, buyer, variant):
        item = services.add_to_cart(buyer, variant.id, 2)
        updated = services.update_cart_item(buyer, item.id, 10)
        assert updated.quantity == 10

    def test_update_zero_quantity_raises(self, buyer, variant):
        item = services.add_to_cart(buyer, variant.id, 2)
        with pytest.raises(ValueError):
            services.update_cart_item(buyer, item.id, 0)

    def test_update_other_buyer_item_raises(self, buyer, second_buyer, variant):
        item = services.add_to_cart(buyer, variant.id, 2)
        with pytest.raises(Http404):
            services.update_cart_item(second_buyer, item.id, 5)

    def test_remove_from_cart(self, buyer, variant):
        item = services.add_to_cart(buyer, variant.id, 1)
        services.remove_from_cart(buyer, item.id)
        assert CartItem.objects.filter(id=item.id).count() == 0

    def test_remove_other_buyer_item_raises(self, buyer, second_buyer, variant):
        item = services.add_to_cart(buyer, variant.id, 1)
        with pytest.raises(Http404):
            services.remove_from_cart(second_buyer, item.id)

    def test_clear_cart(self, buyer, variant, second_variant):
        services.add_to_cart(buyer, variant.id, 1)
        services.add_to_cart(buyer, second_variant.id, 2)
        services.clear_cart(buyer)
        assert CartItem.objects.filter(cart__buyer=buyer).count() == 0

    def test_clear_does_not_affect_other_buyer(self, buyer, second_buyer, variant):
        services.add_to_cart(buyer, variant.id, 1)
        services.add_to_cart(second_buyer, variant.id, 1)
        services.clear_cart(buyer)
        assert CartItem.objects.filter(cart__buyer=second_buyer).count() == 1


class TestWishlist:
    def test_add_to_wishlist(self, buyer, variant):
        item = services.add_to_wishlist(buyer, variant.id)
        assert item.buyer == buyer
        assert item.variant == variant

    def test_add_idempotent(self, buyer, variant):
        i1 = services.add_to_wishlist(buyer, variant.id)
        i2 = services.add_to_wishlist(buyer, variant.id)
        assert i1.id == i2.id
        assert WishlistItem.objects.filter(buyer=buyer, variant=variant).count() == 1

    def test_add_inactive_variant_raises(self, buyer, variant):
        variant.is_active = False
        variant.save()
        with pytest.raises(Http404):
            services.add_to_wishlist(buyer, variant.id)

    def test_remove_from_wishlist(self, buyer, variant):
        item = services.add_to_wishlist(buyer, variant.id)
        services.remove_from_wishlist(buyer, item.id)
        assert WishlistItem.objects.filter(id=item.id).count() == 0

    def test_remove_other_buyer_wishlist_raises(self, buyer, second_buyer, variant):
        item = services.add_to_wishlist(buyer, variant.id)
        with pytest.raises(Http404):
            services.remove_from_wishlist(second_buyer, item.id)


class TestReviews:
    def test_create_review(self, buyer, variant):
        review = services.create_review(buyer, variant.id, 4, "Great", "Loved it")
        assert review.rating == 4
        assert review.reviewer == buyer
        assert review.is_approved is False
        assert review.is_verified_purchase is False

    def test_verified_purchase_flag(self, buyer, variant, delivered_order):
        review = services.create_review(buyer, variant.id, 5, "Perfect", "Amazing")
        assert review.is_verified_purchase is True

    def test_duplicate_review_raises(self, buyer, variant):
        services.create_review(buyer, variant.id, 3, "OK", "Fine")
        with pytest.raises(ValueError, match="already submitted"):
            services.create_review(buyer, variant.id, 4, "Good", "Better")

    def test_different_buyers_can_review_same_variant(self, buyer, second_buyer, variant):
        services.create_review(buyer, variant.id, 5, "Great", "Love it")
        review2 = services.create_review(second_buyer, variant.id, 3, "OK", "Decent")
        assert review2.reviewer == second_buyer

    def test_approve_review(self, buyer, variant):
        review = services.create_review(buyer, variant.id, 4, "Good", "Nice")
        approved = services.approve_review(review)
        assert approved.is_approved is True
