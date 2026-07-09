from decimal import Decimal

from apps.marketplace import services
from apps.marketplace.models import Cart, CartItem, Review, WishlistItem


class TestCartModel:
    def test_str(self, buyer):
        cart = services.get_or_create_cart(user=buyer)
        assert "buyer@example.com" in str(cart)

    def test_str_guest(self, db):
        cart = services.get_or_create_cart(session_key="abc12345xyz")
        assert "guest:abc12345" in str(cart)

    def test_total_empty(self, buyer):
        cart = services.get_or_create_cart(user=buyer)
        assert cart.total == Decimal("0.00")

    def test_total_with_items(self, buyer, variant, second_variant):
        services.add_to_cart(user=buyer, variant_id=variant.id, quantity=2)
        services.add_to_cart(user=buyer, variant_id=second_variant.id, quantity=1)
        cart = Cart.objects.prefetch_related("items__variant").get(buyer=buyer)
        assert cart.total == Decimal("2.50") * 2 + Decimal("4.50") * 1

    def test_item_count(self, buyer, variant, second_variant):
        services.add_to_cart(user=buyer, variant_id=variant.id, quantity=1)
        services.add_to_cart(user=buyer, variant_id=second_variant.id, quantity=1)
        cart = Cart.objects.get(buyer=buyer)
        assert cart.item_count == 2


class TestCartItemModel:
    def test_str(self, buyer, variant):
        services.add_to_cart(user=buyer, variant_id=variant.id, quantity=3)
        item = CartItem.objects.get(cart__buyer=buyer, variant=variant)
        assert "CARR-1KG" in str(item)
        assert "3" in str(item)

    def test_subtotal(self, buyer, variant):
        services.add_to_cart(user=buyer, variant_id=variant.id, quantity=4)
        item = CartItem.objects.get(cart__buyer=buyer, variant=variant)
        assert item.subtotal == Decimal("2.50") * 4


class TestWishlistItemModel:
    def test_str(self, buyer, variant):
        services.add_to_wishlist(buyer, variant.id)
        item = WishlistItem.objects.get(buyer=buyer, variant=variant)
        assert "buyer@example.com" in str(item)
        assert "CARR-1KG" in str(item)


class TestReviewModel:
    def test_str(self, buyer, variant):
        review = Review.objects.create(
            variant=variant, reviewer=buyer, rating=4, title="Great", body="Loved it"
        )
        assert "4/5" in str(review)
        assert "CARR-1KG" in str(review)

    def test_default_not_approved(self, buyer, variant):
        review = Review.objects.create(
            variant=variant, reviewer=buyer, rating=5, title="Excellent", body="Perfect"
        )
        assert review.is_approved is False

    def test_default_not_verified(self, buyer, variant):
        review = Review.objects.create(
            variant=variant, reviewer=buyer, rating=3, title="OK", body="Fine"
        )
        assert review.is_verified_purchase is False
