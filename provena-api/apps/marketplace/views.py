from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.pagination import PaginatedListMixin

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
# Cart helpers
# ---------------------------------------------------------------------------

_CART_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def _cart_identity(request) -> dict | None:
    """Return identity kwargs for service calls, or None if the request has no cart context."""
    if request.user.is_authenticated:
        return {"user": request.user}
    key = request.COOKIES.get(services.CART_COOKIE)
    if key:
        return {"session_key": key}
    return None


def _cart_identity_or_create(request) -> dict:
    """Like _cart_identity but generates a fresh session key for new anonymous users."""
    if request.user.is_authenticated:
        return {"user": request.user}
    key = request.COOKIES.get(services.CART_COOKIE) or services.new_session_key()
    return {"session_key": key}


def _set_cart_cookie(response: Response, identity: dict) -> None:
    key = identity.get("session_key")
    if key:
        response.set_cookie(
            services.CART_COOKIE,
            key,
            max_age=_CART_COOKIE_MAX_AGE,
            httponly=False,
            samesite="Lax",
            path="/",
            secure=getattr(settings, "CART_COOKIE_SECURE", False),
        )


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------


class CartView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: CartSerializer}, tags=["Marketplace: Cart"], summary="Get cart")
    def get(self, request):
        identity = _cart_identity(request)
        if identity is None:
            return Response({"id": None, "items": [], "total": "0.00", "item_count": 0})
        cart = services.get_or_create_cart(**identity)
        cart_qs = Cart.objects.prefetch_related("items__variant__product").get(pk=cart.pk)
        response = Response(CartSerializer(cart_qs).data)
        _set_cart_cookie(response, identity)
        return response

    @extend_schema(
        responses={204: None},
        tags=["Marketplace: Cart"],
        summary="Clear cart",
    )
    def delete(self, request):
        identity = _cart_identity(request)
        if identity:
            services.clear_cart(**identity)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemCreateView(APIView):
    permission_classes = [AllowAny]

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
        identity = _cart_identity_or_create(request)
        try:
            item = services.add_to_cart(
                **identity,
                variant_id=ser.validated_data["variant_id"],
                quantity=ser.validated_data["quantity"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        response = Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)
        _set_cart_cookie(response, identity)
        return response


class CartItemDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=UpdateCartItemSerializer,
        responses={200: CartItemSerializer},
        tags=["Marketplace: Cart"],
        summary="Update cart item quantity",
    )
    def patch(self, request, pk):
        identity = _cart_identity(request)
        if identity is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ser = UpdateCartItemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            item = services.update_cart_item(
                **identity, item_id=pk, quantity=ser.validated_data["quantity"]
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        response = Response(CartItemSerializer(item).data)
        _set_cart_cookie(response, identity)
        return response

    @extend_schema(
        responses={204: None},
        tags=["Marketplace: Cart"],
        summary="Remove item from cart",
    )
    def delete(self, request, pk):
        identity = _cart_identity(request)
        if identity is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        services.remove_from_cart(**identity, item_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartMergeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Marketplace: Cart"],
        summary="Merge guest cart into user cart",
        description="Reads the `provena_cart` session cookie and merges any guest cart items "
        "into the authenticated user's cart. Idempotent if no guest cart exists.",
        request=None,
        responses={200: None},
    )
    def post(self, request):
        session_key = request.COOKIES.get(services.CART_COOKIE)
        if session_key:
            services.merge_guest_cart(session_key, request.user)
        response = Response({"merged": bool(session_key)})
        response.delete_cookie(services.CART_COOKIE, path="/")
        return response


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------


class WishlistView(PaginatedListMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: WishlistItemSerializer(many=True)},
        tags=["Marketplace: Wishlist"],
        summary="List wishlist items",
    )
    def get(self, request):
        items = WishlistItem.objects.filter(buyer=request.user).select_related("variant__product")
        return self.paginate(items, WishlistItemSerializer, request)

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


class ProductReviewListCreateView(PaginatedListMixin, APIView):
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
        return self.paginate(reviews, ReviewSerializer, request)

    @extend_schema(
        request=CreateReviewSerializer,
        responses={201: ReviewSerializer},
        tags=["Marketplace: Reviews"],
        summary="Submit a review",
        description=(
            "Restricted to buyers who have a delivered order containing this variant. "
            "One review per buyer per variant. "
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
            qs = qs.filter(variant_id=variant_id)  # type: ignore[misc]
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
