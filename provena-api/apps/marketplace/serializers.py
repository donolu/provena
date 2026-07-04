from rest_framework import serializers

from .models import Cart, CartItem, CartReservation, Review, WishlistItem


class CartItemSerializer(serializers.ModelSerializer):
    variant_sku = serializers.CharField(source="variant.sku", read_only=True)
    variant_name = serializers.CharField(source="variant.name", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    price = serializers.DecimalField(
        source="variant.price", max_digits=10, decimal_places=2, read_only=True
    )
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    reservation_expires_at = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "variant",
            "variant_sku",
            "variant_name",
            "product_name",
            "price",
            "quantity",
            "subtotal",
            "reservation_expires_at",
            "added_at",
            "updated_at",
        ]
        read_only_fields = ["id", "added_at", "updated_at"]

    def get_reservation_expires_at(self, obj) -> str | None:
        try:
            return obj.reservation.expires_at.isoformat()
        except CartReservation.DoesNotExist:
            return None


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "items", "total", "item_count", "updated_at"]
        read_only_fields = fields


class AddToCartSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class WishlistItemSerializer(serializers.ModelSerializer):
    variant_sku = serializers.CharField(source="variant.sku", read_only=True)
    variant_name = serializers.CharField(source="variant.name", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    price = serializers.DecimalField(
        source="variant.price", max_digits=10, decimal_places=2, read_only=True
    )
    is_active = serializers.BooleanField(source="variant.is_active", read_only=True)

    class Meta:
        model = WishlistItem
        fields = [
            "id",
            "variant",
            "variant_sku",
            "variant_name",
            "product_name",
            "price",
            "is_active",
            "added_at",
        ]
        read_only_fields = fields


class AddToWishlistSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_email = serializers.SerializerMethodField()
    variant_sku = serializers.CharField(source="variant.sku", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "variant",
            "variant_sku",
            "reviewer_email",
            "rating",
            "title",
            "body",
            "is_verified_purchase",
            "is_approved",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_reviewer_email(self, obj) -> str | None:
        return obj.reviewer.email if obj.reviewer else None


class CreateReviewSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    title = serializers.CharField(max_length=200)
    body = serializers.CharField()
