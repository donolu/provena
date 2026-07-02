from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.pagination import PaginatedListMixin
from apps.suppliers.permissions import IsApprovedSupplier

from . import services
from .models import Category, Product, ProductImage, ProductStatus, ProductVariant
from .serializers import (
    AdminProductSerializer,
    CategorySerializer,
    CategoryWriteSerializer,
    ProductImageSerializer,
    ProductImageWriteSerializer,
    ProductSerializer,
    ProductVariantSerializer,
    ProductVariantWriteSerializer,
    ProductWriteSerializer,
)


def _own_product(request: Request, slug: str) -> Product:
    """Return the product owned by the requesting supplier, or 404."""
    return get_object_or_404(Product, slug=slug, supplier=request.user.supplier)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


class CategoryListView(APIView):
    def get_permissions(self):
        return [AllowAny()]

    @extend_schema(
        tags=["Catalogue: Categories"],
        summary="List root categories",
        description="Returns all active root categories (no parent) with their active children nested. "
        "Pass `?all=true` to include inactive categories (admin use).",
        parameters=[
            OpenApiParameter(
                name="all",
                description="Include inactive categories",
                required=False,
                type=bool,
            )
        ],
        responses={200: CategorySerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = Category.objects.filter(parent__isnull=True)
        if request.query_params.get("all") != "true":
            qs = qs.filter(is_active=True)
        return Response(CategorySerializer(qs, many=True).data)


class CategoryDetailView(APIView):
    def get_permissions(self):
        return [AllowAny()]

    @extend_schema(
        tags=["Catalogue: Categories"],
        summary="Get category detail",
        description="Returns the category with its children nested. "
        "Returns 404 for inactive categories unless the requester is admin.",
        responses={
            200: CategorySerializer,
            404: OpenApiResponse(description="Not found"),
        },
    )
    def get(self, request: Request, slug: str) -> Response:
        category = get_object_or_404(Category, slug=slug)
        return Response(CategorySerializer(category).data)


# ---------------------------------------------------------------------------
# Admin: Categories
# ---------------------------------------------------------------------------


class AdminCategoryListCreateView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin: Categories"],
        summary="List all categories (admin)",
        description="Returns all categories including inactive ones.",
        responses={200: CategorySerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = Category.objects.all()
        return Response(CategorySerializer(qs, many=True).data)

    @extend_schema(
        tags=["Admin: Categories"],
        summary="Create category",
        description="Pass `parent` as a category slug to create a subcategory.",
        request=CategoryWriteSerializer,
        responses={
            201: CategorySerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request: Request) -> Response:
        s = CategoryWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        category = services.create_category(
            name=d["name"],
            parent=d.get("parent"),
            description=d.get("description", ""),
            image_url=d.get("image_url", ""),
            position=d.get("position", 0),
        )
        return Response(CategorySerializer(category).data, status=status.HTTP_201_CREATED)


class AdminCategoryDetailView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin: Categories"],
        summary="Update category",
        request=CategoryWriteSerializer,
        responses={
            200: CategorySerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    def patch(self, request: Request, slug: str) -> Response:
        category = get_object_or_404(Category, slug=slug)
        s = CategoryWriteSerializer(category, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        category = services.update_category(category, **s.validated_data)
        return Response(CategorySerializer(category).data)

    @extend_schema(
        tags=["Admin: Categories"],
        summary="Delete category",
        description="Deletes the category. Products in this category will have their "
        "category set to null.",
        responses={
            204: OpenApiResponse(description="Deleted"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    def delete(self, request: Request, slug: str) -> Response:
        category = get_object_or_404(Category, slug=slug)
        services.delete_category(category)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Products (public list + supplier create)
# ---------------------------------------------------------------------------


class ProductListCreateView(PaginatedListMixin, APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsApprovedSupplier()]
        return [AllowAny()]

    @extend_schema(
        tags=["Catalogue: Products"],
        summary="List active products",
        description="Returns all ACTIVE products. Supports filtering by category, supplier, "
        "and free-text search across name and description.",
        parameters=[
            OpenApiParameter(
                name="category", description="Filter by category slug", required=False
            ),
            OpenApiParameter(
                name="supplier", description="Filter by supplier slug", required=False
            ),
            OpenApiParameter(
                name="search", description="Search name and description", required=False
            ),
            OpenApiParameter(
                name="featured", description="Set to `true` for featured only", required=False
            ),
        ],
        responses={200: ProductSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = (
            Product.objects.filter(status=ProductStatus.ACTIVE)
            .select_related("supplier", "category")
            .prefetch_related("variants", "images")
        )
        if category_slug := request.query_params.get("category"):
            qs = qs.filter(category__slug=category_slug)
        if supplier_slug := request.query_params.get("supplier"):
            qs = qs.filter(supplier__slug=supplier_slug)
        if search := request.query_params.get("search"):
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        if request.query_params.get("featured") == "true":
            qs = qs.filter(is_featured=True)
        return self.paginate(qs, ProductSerializer, request)

    @extend_schema(
        tags=["Catalogue: Products"],
        summary="Create product",
        description="Creates a product in DRAFT status for the authenticated approved supplier. "
        "Publish via `POST /api/v1/catalogue/products/<slug>/publish/` when ready.",
        request=ProductWriteSerializer,
        responses={
            201: ProductSerializer,
            400: OpenApiResponse(description="Validation error"),
            403: OpenApiResponse(description="Not an approved supplier"),
        },
    )
    def post(self, request: Request) -> Response:
        s = ProductWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        product = services.create_product(
            supplier=request.user.supplier,
            name=d["name"],
            description=d.get("description", ""),
            category=d.get("category"),
        )
        return Response(
            ProductSerializer(product).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Supplier: own product list
# ---------------------------------------------------------------------------


class SupplierProductListView(PaginatedListMixin, APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        tags=["Catalogue: Products"],
        summary="List own products",
        description="Returns all products (any status) for the authenticated supplier.",
        parameters=[
            OpenApiParameter(
                name="status",
                description="Filter by status",
                required=False,
                enum=["DRAFT", "ACTIVE", "ARCHIVED"],
            )
        ],
        responses={200: ProductSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = request.user.supplier.products.select_related("category").prefetch_related(
            "variants", "images"
        )
        if status_filter := request.query_params.get("status"):
            qs = qs.filter(status=status_filter.upper())
        return self.paginate(qs, ProductSerializer, request)


# ---------------------------------------------------------------------------
# Product detail (public) + update (supplier)
# ---------------------------------------------------------------------------


class ProductDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ("PATCH", "DELETE"):
            return [IsApprovedSupplier()]
        return [AllowAny()]

    @extend_schema(
        tags=["Catalogue: Products"],
        summary="Get product detail",
        description="Returns a product with all variants and images. "
        "Only ACTIVE products are visible publicly. Suppliers see their own DRAFT products too "
        "via `GET /api/v1/catalogue/products/me/`.",
        responses={
            200: ProductSerializer,
            404: OpenApiResponse(description="Not found or not active"),
        },
    )
    def get(self, request: Request, slug: str) -> Response:
        product = get_object_or_404(
            Product.objects.select_related("supplier", "category").prefetch_related(
                "variants", "images"
            ),
            slug=slug,
            status=ProductStatus.ACTIVE,
        )
        return Response(ProductSerializer(product).data)

    @extend_schema(
        tags=["Catalogue: Products"],
        summary="Update own product",
        description="Partial update of name, description, or category. "
        "Status transitions use the dedicated publish/archive endpoints.",
        request=ProductWriteSerializer,
        responses={
            200: ProductSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Not found or not yours"),
        },
    )
    def patch(self, request: Request, slug: str) -> Response:
        product = _own_product(request, slug)
        s = ProductWriteSerializer(product, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        product = services.update_product(product, **s.validated_data)
        return Response(ProductSerializer(product).data)


# ---------------------------------------------------------------------------
# Publish / archive
# ---------------------------------------------------------------------------


class ProductPublishView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        tags=["Catalogue: Products"],
        summary="Publish product",
        description="Transitions a DRAFT product to ACTIVE, making it publicly visible. "
        "Returns 400 if the product is already ARCHIVED.",
        request=None,
        responses={
            200: ProductSerializer,
            400: OpenApiResponse(description="Cannot publish an archived product"),
            404: OpenApiResponse(description="Not found or not yours"),
        },
    )
    def post(self, request: Request, slug: str) -> Response:
        product = _own_product(request, slug)
        try:
            product = services.publish_product(product)
        except ValueError as exc:
            return Response(
                {"error": {"code": "INVALID_TRANSITION", "message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(ProductSerializer(product).data)


class ProductArchiveView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        tags=["Catalogue: Products"],
        summary="Archive product",
        description="Soft-deletes the product by setting status to ARCHIVED. "
        "Archived products are hidden from the public listing.",
        request=None,
        responses={
            200: ProductSerializer,
            404: OpenApiResponse(description="Not found or not yours"),
        },
    )
    def post(self, request: Request, slug: str) -> Response:
        product = _own_product(request, slug)
        product = services.archive_product(product)
        return Response(ProductSerializer(product).data)


# ---------------------------------------------------------------------------
# Variants
# ---------------------------------------------------------------------------


class ProductVariantListCreateView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        tags=["Catalogue: Variants"],
        summary="Add variant to product",
        description="Adds a purchasable variant (SKU) to the product. "
        "Each variant has its own price and weight. "
        "SKUs must be unique across all products.",
        request=ProductVariantWriteSerializer,
        responses={
            201: ProductVariantSerializer,
            400: OpenApiResponse(description="Validation error or duplicate SKU"),
            404: OpenApiResponse(description="Not found or not yours"),
        },
    )
    def post(self, request: Request, slug: str) -> Response:
        product = _own_product(request, slug)
        s = ProductVariantWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            variant = services.add_variant(
                product=product,
                name=d["name"],
                sku=d["sku"],
                price=d["price"],
                compare_at_price=d.get("compare_at_price"),
                weight_grams=d.get("weight_grams", 0),
            )
        except ValueError as exc:
            return Response(
                {"error": {"code": "DUPLICATE_SKU", "message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(ProductVariantSerializer(variant).data, status=status.HTTP_201_CREATED)


class ProductVariantDetailView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        tags=["Catalogue: Variants"],
        summary="Update variant",
        request=ProductVariantWriteSerializer,
        responses={
            200: ProductVariantSerializer,
            400: OpenApiResponse(description="Validation error or duplicate SKU"),
            404: OpenApiResponse(description="Not found or not yours"),
        },
    )
    def patch(self, request: Request, slug: str, pk: str) -> Response:
        product = _own_product(request, slug)
        variant = get_object_or_404(ProductVariant, pk=pk, product=product)
        s = ProductVariantWriteSerializer(variant, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        try:
            variant = services.update_variant(variant, **s.validated_data)
        except ValueError as exc:
            return Response(
                {"error": {"code": "DUPLICATE_SKU", "message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(ProductVariantSerializer(variant).data)

    @extend_schema(
        tags=["Catalogue: Variants"],
        summary="Delete variant",
        responses={
            204: OpenApiResponse(description="Deleted"),
            404: OpenApiResponse(description="Not found or not yours"),
        },
    )
    def delete(self, request: Request, slug: str, pk: str) -> Response:
        product = _own_product(request, slug)
        variant = get_object_or_404(ProductVariant, pk=pk, product=product)
        services.remove_variant(variant)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------


class ProductImageListCreateView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        tags=["Catalogue: Images"],
        summary="Add image to product",
        description="Registers an image URL for the product. Upload the file to S3 via a presigned "
        "URL first, then pass the resulting URL here. The first image added with "
        "`is_primary: true` becomes the primary product image.",
        request=ProductImageWriteSerializer,
        responses={
            201: ProductImageSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Product not found or not yours"),
        },
    )
    def post(self, request: Request, slug: str) -> Response:
        product = _own_product(request, slug)
        s = ProductImageWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        image = services.add_image(
            product=product,
            url=d["url"],
            alt_text=d.get("alt_text", ""),
            position=d.get("position"),
            is_primary=d.get("is_primary", False),
        )
        return Response(ProductImageSerializer(image).data, status=status.HTTP_201_CREATED)


class ProductImageDetailView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        tags=["Catalogue: Images"],
        summary="Update image",
        description="Update URL, alt text, position, or primary status. "
        "Setting `is_primary: true` automatically clears the primary flag from all other images.",
        request=ProductImageWriteSerializer,
        responses={
            200: ProductImageSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Not found or not yours"),
        },
    )
    def patch(self, request: Request, slug: str, pk: str) -> Response:
        product = _own_product(request, slug)
        image = get_object_or_404(ProductImage, pk=pk, product=product)
        s = ProductImageWriteSerializer(image, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        image = services.update_image(image, **s.validated_data)
        return Response(ProductImageSerializer(image).data)

    @extend_schema(
        tags=["Catalogue: Images"],
        summary="Delete image",
        responses={
            204: OpenApiResponse(description="Deleted"),
            404: OpenApiResponse(description="Not found or not yours"),
        },
    )
    def delete(self, request: Request, slug: str, pk: str) -> Response:
        product = _own_product(request, slug)
        image = get_object_or_404(ProductImage, pk=pk, product=product)
        services.remove_image(image)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Admin: products
# ---------------------------------------------------------------------------


class AdminProductListView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin: Products"],
        summary="List all products (admin)",
        description="Returns all products regardless of status. "
        "Filter by `?status=DRAFT|ACTIVE|ARCHIVED` or `?supplier=<slug>`.",
        parameters=[
            OpenApiParameter(
                name="status",
                description="Filter by status",
                required=False,
                enum=["DRAFT", "ACTIVE", "ARCHIVED"],
            ),
            OpenApiParameter(
                name="supplier", description="Filter by supplier slug", required=False
            ),
        ],
        responses={200: AdminProductSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = Product.objects.select_related("supplier", "category").prefetch_related(
            "variants", "images"
        )
        if status_filter := request.query_params.get("status"):
            qs = qs.filter(status=status_filter.upper())
        if supplier_slug := request.query_params.get("supplier"):
            qs = qs.filter(supplier__slug=supplier_slug)
        return Response(AdminProductSerializer(qs, many=True).data)


class AdminProductFeatureView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin: Products"],
        summary="Toggle product featured status",
        description="Toggles `is_featured` on the product. "
        "Featured products appear in the `?featured=true` filter on the public listing.",
        request=None,
        responses={
            200: AdminProductSerializer,
            404: OpenApiResponse(description="Not found"),
        },
    )
    def post(self, request: Request, slug: str) -> Response:
        product = get_object_or_404(Product, slug=slug)
        if product.is_featured:
            product = services.unfeature_product(product, request.user)
        else:
            product = services.feature_product(product, request.user)
        return Response(AdminProductSerializer(product).data)
