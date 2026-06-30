from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Cart, Review, WishlistItem
from .serializers import (
    AddToCartSerializer,
    AddToWishlistSerializer,
    CartItemSerializer,
    CartSerializer,
    CreateReviewSerializer,
    ReviewSerializer,
    UpdateCartItemSerializer,
    WishlistItemSerializer,
)

# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: CartSerializer}, tags=["Marketplace: Cart"], summary="Get cart")
    def get(self, request):
        cart = services.get_or_create_cart(request.user)
        cart_qs = Cart.objects.prefetch_related("items__variant__product").get(pk=cart.pk)
        return Response(CartSerializer(cart_qs).data)

    @extend_schema(
        responses={204: None},
        tags=["Marketplace: Cart"],
        summary="Clear cart",
    )
    def delete(self, request):
        services.clear_cart(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=AddToCartSerializer,
        responses={201: CartItemSerializer},
        tags=["Marketplace: Cart"],
        summary="Add item to cart",
        description="Adds a variant to the cart. If the variant is already in the cart, increments quantity.",
    )
    def post(self, request):
        ser = AddToCartSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            item = services.add_to_cart(
                request.user,
                ser.validated_data["variant_id"],
                ser.validated_data["quantity"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=UpdateCartItemSerializer,
        responses={200: CartItemSerializer},
        tags=["Marketplace: Cart"],
        summary="Update cart item quantity",
    )
    def patch(self, request, pk):
        ser = UpdateCartItemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            item = services.update_cart_item(request.user, pk, ser.validated_data["quantity"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CartItemSerializer(item).data)

    @extend_schema(
        responses={204: None},
        tags=["Marketplace: Cart"],
        summary="Remove item from cart",
    )
    def delete(self, request, pk):
        services.remove_from_cart(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------


class WishlistView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: WishlistItemSerializer(many=True)},
        tags=["Marketplace: Wishlist"],
        summary="List wishlist items",
    )
    def get(self, request):
        items = WishlistItem.objects.filter(buyer=request.user).select_related("variant__product")
        return Response(WishlistItemSerializer(items, many=True).data)

    @extend_schema(
        request=AddToWishlistSerializer,
        responses={201: WishlistItemSerializer},
        tags=["Marketplace: Wishlist"],
        summary="Add to wishlist",
        description="Idempotent: returns the existing item if the variant is already wishlisted.",
    )
    def post(self, request):
        ser = AddToWishlistSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        item = services.add_to_wishlist(request.user, ser.validated_data["variant_id"])
        return Response(WishlistItemSerializer(item).data, status=status.HTTP_201_CREATED)


class WishlistItemDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={204: None},
        tags=["Marketplace: Wishlist"],
        summary="Remove from wishlist",
    )
    def delete(self, request, pk):
        services.remove_from_wishlist(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------


class ProductReviewListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        responses={200: ReviewSerializer(many=True)},
        tags=["Marketplace: Reviews"],
        summary="List approved reviews for a variant",
    )
    def get(self, request, variant_id):
        reviews = Review.objects.filter(variant_id=variant_id, is_approved=True).select_related(
            "variant", "reviewer"
        )
        return Response(ReviewSerializer(reviews, many=True).data)

    @extend_schema(
        request=CreateReviewSerializer,
        responses={201: ReviewSerializer},
        tags=["Marketplace: Reviews"],
        summary="Submit a review",
        description=(
            "One review per buyer per variant. "
            "Automatically flagged as verified purchase if the buyer has a delivered order for this variant. "
            "Reviews are not public until approved by an admin."
        ),
    )
    def post(self, request, variant_id):
        ser = CreateReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            review = services.create_review(
                user=request.user,
                variant_id=variant_id,
                **ser.validated_data,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class AdminReviewListView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAdminUser]
    pagination_class = None

    @extend_schema(
        tags=["Admin: Marketplace"],
        summary="List all reviews (admin)",
        description="Returns all reviews. Filter by `?is_approved=true|false` or `?variant=<uuid>`.",
    )
    def get_queryset(self):
        qs = Review.objects.select_related("variant", "reviewer").order_by("-created_at")
        approved = self.request.query_params.get("is_approved")
        if approved is not None:
            qs = qs.filter(is_approved=approved.lower() == "true")
        variant_id = self.request.query_params.get("variant")
        if variant_id:
            qs = qs.filter(variant_id=variant_id)
        return qs


class AdminReviewApproveView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        responses={200: ReviewSerializer},
        tags=["Admin: Marketplace"],
        summary="Approve a review",
    )
    def post(self, request, pk):
        from django.shortcuts import get_object_or_404

        review = get_object_or_404(Review, pk=pk)
        review = services.approve_review(review)
        return Response(ReviewSerializer(review).data)


class AdminReviewDeleteView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        responses={204: None},
        tags=["Admin: Marketplace"],
        summary="Delete a review (reject)",
    )
    def delete(self, request, pk):
        from django.shortcuts import get_object_or_404

        review = get_object_or_404(Review, pk=pk)
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
