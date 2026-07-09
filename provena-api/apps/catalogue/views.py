from django.db import models
from django.db.models import Avg, Count, FloatField, IntegerField, OuterRef, Q, Subquery
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.pagination import PaginatedListMixin
from apps.suppliers.permissions import IsApprovedSupplier

from . import bulk_upload, services
from .models import (
    Banner,
    Category,
    Product,
    ProductImage,
    ProductStatus,
    ProductVariant,
    VariantImage,
    _unique_product_slug,
)
from .serializers import (
    AdminProductSerializer,
    BulkProductActionSerializer,
    CategorySerializer,
    CategoryWriteSerializer,
    ProductImageSerializer,
    ProductImageWriteSerializer,
    ProductSerializer,
    ProductVariantSerializer,
    ProductVariantWriteSerializer,
    ProductWriteSerializer,
    VariantImageSerializer,
    VariantImageWriteSerializer,
)


def _own_product(request: Request, slug: str) -> Product:
    """Return the product owned by the requesting supplier, or 404."""
    return get_object_or_404(Product, slug=slug, supplier=request.user.supplier)  # type: ignore[union-attr]


def _annotate_ratings(qs: "models.QuerySet[Product]") -> "models.QuerySet[Product]":
    """Annotate average_rating and review_count onto a Product queryset in a single pass."""
    from apps.marketplace.models import Review

    approved_reviews = Review.objects.filter(variant__product=OuterRef("pk"), is_approved=True)
    return qs.annotate(
        average_rating=Subquery(
            approved_reviews.values("variant__product").annotate(v=Avg("rating")).values("v"),
            output_field=FloatField(),
        ),
        review_count=Subquery(
            approved_reviews.values("variant__product").annotate(v=Count("id")).values("v"),
            output_field=IntegerField(),
        ),
    )


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
            .prefetch_related("variants", "variants__images", "images")
        )
        if category_slug := request.query_params.get("category"):
            qs = qs.filter(category__slug=category_slug)
        if supplier_slug := request.query_params.get("supplier"):
            qs = qs.filter(supplier__slug=supplier_slug)
        if search := request.query_params.get("search"):
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(category__name__icontains=search)
                | Q(variants__name__icontains=search)
            ).distinct()
        if request.query_params.get("featured") == "true":
            qs = qs.filter(is_featured=True)
        if min_price := request.query_params.get("min_price"):
            qs = qs.filter(variants__price__gte=min_price).distinct()
        if max_price := request.query_params.get("max_price"):
            qs = qs.filter(variants__price__lte=max_price).distinct()
        return self.paginate(_annotate_ratings(qs), ProductSerializer, request)

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
            supplier=request.user.supplier,  # type: ignore[union-attr]
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
        qs = request.user.supplier.products.select_related("category").prefetch_related(  # type: ignore[union-attr]
            "variants", "variants__images", "images"
        )
        if status_filter := request.query_params.get("status"):
            qs = qs.filter(status=status_filter.upper())
        return self.paginate(_annotate_ratings(qs), ProductSerializer, request)


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
            _annotate_ratings(
                Product.objects.select_related("supplier", "category").prefetch_related(
                    "variants", "variants__images", "images"
                )
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
# Variant images
# ---------------------------------------------------------------------------


class VariantImageListCreateView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        tags=["Catalogue: Variants"],
        summary="Add image to variant",
        description="Registers an image URL for a specific product variant. "
        "Upload to S3 via a presigned URL first, then pass the resulting URL here. "
        "Setting `is_primary: true` clears the primary flag from all other images for this variant.",
        request=VariantImageWriteSerializer,
        responses={
            201: VariantImageSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Product or variant not found or not yours"),
        },
    )
    def post(self, request: Request, slug: str, pk: str) -> Response:
        product = _own_product(request, slug)
        variant = get_object_or_404(ProductVariant, pk=pk, product=product)
        s = VariantImageWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        image = services.add_variant_image(
            variant=variant,
            url=d["url"],
            alt_text=d.get("alt_text", ""),
            position=d.get("position"),
            is_primary=d.get("is_primary", False),
        )
        return Response(VariantImageSerializer(image).data, status=status.HTTP_201_CREATED)


class VariantImageDetailView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        tags=["Catalogue: Variants"],
        summary="Update variant image",
        description="Update URL, alt text, position, or primary status. "
        "Setting `is_primary: true` automatically clears the primary flag from other images for this variant.",
        request=VariantImageWriteSerializer,
        responses={
            200: VariantImageSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Not found or not yours"),
        },
    )
    def patch(self, request: Request, slug: str, pk: str, img_pk: str) -> Response:
        product = _own_product(request, slug)
        variant = get_object_or_404(ProductVariant, pk=pk, product=product)
        image = get_object_or_404(VariantImage, pk=img_pk, variant=variant)
        s = VariantImageWriteSerializer(image, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        image = services.update_variant_image(image, **s.validated_data)
        return Response(VariantImageSerializer(image).data)

    @extend_schema(
        tags=["Catalogue: Variants"],
        summary="Delete variant image",
        responses={
            204: OpenApiResponse(description="Deleted"),
            404: OpenApiResponse(description="Not found or not yours"),
        },
    )
    def delete(self, request: Request, slug: str, pk: str, img_pk: str) -> Response:
        product = _own_product(request, slug)
        variant = get_object_or_404(ProductVariant, pk=pk, product=product)
        image = get_object_or_404(VariantImage, pk=img_pk, variant=variant)
        services.remove_variant_image(image)
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
            "variants", "variants__images", "images"
        )
        if status_filter := request.query_params.get("status"):
            qs = qs.filter(status=status_filter.upper())
        if supplier_slug := request.query_params.get("supplier"):
            qs = qs.filter(supplier__slug=supplier_slug)
        return Response(AdminProductSerializer(_annotate_ratings(qs), many=True).data)


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
            product = services.unfeature_product(product, request.user)  # type: ignore[arg-type]
        else:
            product = services.feature_product(product, request.user)  # type: ignore[arg-type]
        return Response(AdminProductSerializer(product).data)


class AdminProductBulkActionView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin: Products"],
        summary="Bulk product actions",
        description=(
            "Apply an action to multiple products at once. "
            "Actions: `set_status` (requires `status`), "
            "`set_category` (requires `category` slug or null to clear), "
            "`set_featured` (requires `is_featured` bool). "
            "Returns the count of updated products."
        ),
        request=BulkProductActionSerializer,
        responses={
            200: None,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request: Request) -> Response:
        s = BulkProductActionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        updated = services.bulk_update_products(
            slugs=d["slugs"],
            action=d["action"],
            status=d.get("status"),
            category=d.get("category"),
            is_featured=d.get("is_featured"),
        )
        return Response({"updated": updated})


class BannerListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Catalogue"],
        summary="List active banners",
        description="Returns all active homepage banners ordered by position.",
    )
    def get(self, request: Request) -> Response:
        from .serializers import BannerSerializer

        qs = Banner.objects.filter(is_active=True)
        return Response(BannerSerializer(qs, many=True).data)


class AdminBannerListCreateView(PaginatedListMixin, APIView):
    permission_classes = [IsAdmin]

    @extend_schema(tags=["Admin: Banners"], summary="List all banners")
    def get(self, request: Request) -> Response:
        from .serializers import BannerSerializer

        return self.paginate(Banner.objects.all(), BannerSerializer, request)

    @extend_schema(
        tags=["Admin: Banners"],
        summary="Create a banner",
        responses={201: None},
    )
    def post(self, request: Request) -> Response:
        from .serializers import BannerSerializer, BannerWriteSerializer

        s = BannerWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        banner = Banner.objects.create(**s.validated_data)
        return Response(BannerSerializer(banner).data, status=status.HTTP_201_CREATED)


class AdminBannerDetailView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(tags=["Admin: Banners"], summary="Update a banner")
    def patch(self, request: Request, pk: str) -> Response:
        from .serializers import BannerSerializer, BannerWriteSerializer

        banner = get_object_or_404(Banner, pk=pk)
        s = BannerWriteSerializer(banner, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(BannerSerializer(banner).data)

    @extend_schema(tags=["Admin: Banners"], summary="Delete a banner")
    def delete(self, request: Request, pk: str) -> Response:
        banner = get_object_or_404(Banner, pk=pk)
        banner.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Supplier: bulk product upload
# ---------------------------------------------------------------------------

_TEMPLATE_HEADER = (
    "product_name,variant_name,sku,price,description,"
    "category,compare_at_price,weight_grams,image_url\r\n"
)
_TEMPLATE_EXAMPLE = (
    "Organic Carrots,1kg bag,CARR-1KG,3.99,Fresh organic carrots.,"
    "Fresh Produce,,1000,https://example.com/carrots.jpg\r\n"
    "Organic Carrots,500g bag,CARR-500G,2.19,,,,,\r\n"
)


class ProductUploadTemplateView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        tags=["Supplier: Products"],
        summary="Download CSV upload template",
        responses={200: OpenApiResponse(description="CSV file download")},
    )
    def get(self, request: Request) -> HttpResponse:
        body = _TEMPLATE_HEADER + _TEMPLATE_EXAMPLE
        response = HttpResponse(body, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="provena_products_template.csv"'
        return response


class ProductUploadPreviewView(APIView):
    permission_classes = [IsApprovedSupplier]
    parser_classes = [MultiPartParser]

    @extend_schema(
        tags=["Supplier: Products"],
        summary="Preview a product upload file",
        description=(
            "Parses and validates a CSV, XLSX, or XLS file. "
            "Format is detected by magic bytes, not file extension. "
            "Nothing is written to the database. Max 500 rows, 5 MB."
        ),
        responses={
            200: OpenApiResponse(
                description="Parsed products (valid=true) or validation errors (valid=false)"
            ),
            400: OpenApiResponse(description="File missing, too large, or unreadable"),
        },
    )
    def post(self, request: Request) -> Response:
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        content = file_obj.read()
        if len(content) > bulk_upload.MAX_SIZE_BYTES:
            return Response(
                {"detail": "File exceeds 5 MB limit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rows = bulk_upload.parse_upload(content)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if not rows:
            return Response({"detail": "File is empty."}, status=status.HTTP_400_BAD_REQUEST)

        if len(rows) > bulk_upload.MAX_ROWS:
            return Response(
                {"detail": f"File contains {len(rows)} rows; maximum is {bulk_upload.MAX_ROWS}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_skus = set(ProductVariant.objects.values_list("sku", flat=True))
        products, errors = bulk_upload.validate_and_group(rows, existing_skus)

        if errors:
            return Response({"valid": False, "errors": errors})

        return Response(
            {
                "valid": True,
                "products": products,
                "row_count": len(rows),
                "product_count": len(products),
            }
        )


class ProductUploadConfirmView(APIView):
    permission_classes = [IsApprovedSupplier]
    parser_classes = [MultiPartParser]

    @extend_schema(
        tags=["Supplier: Products"],
        summary="Confirm and commit a product upload",
        description=(
            "Accepts the same file as the preview endpoint. "
            "Runs full validation again before writing. "
            "All created products are in DRAFT status."
        ),
        responses={
            201: OpenApiResponse(description="Products created"),
            400: OpenApiResponse(description="File missing, too large, or unreadable"),
            422: OpenApiResponse(
                description="Validation errors — file has changed or new conflicts exist"
            ),
        },
    )
    def post(self, request: Request) -> Response:
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        content = file_obj.read()
        if len(content) > bulk_upload.MAX_SIZE_BYTES:
            return Response(
                {"detail": "File exceeds 5 MB limit."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            rows = bulk_upload.parse_upload(content)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if not rows:
            return Response({"detail": "File is empty."}, status=status.HTTP_400_BAD_REQUEST)

        if len(rows) > bulk_upload.MAX_ROWS:
            return Response(
                {"detail": f"File contains {len(rows)} rows; maximum is {bulk_upload.MAX_ROWS}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_skus = set(ProductVariant.objects.values_list("sku", flat=True))
        products, errors = bulk_upload.validate_and_group(rows, existing_skus)

        if errors:
            return Response(
                {"valid": False, "errors": errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        supplier = request.user.supplier  # type: ignore[union-attr]
        category_map = {c.name.lower(): c for c in Category.objects.filter(is_active=True)}

        created_products = []
        for product_data in products:
            category = category_map.get((product_data["category"] or "").lower())
            product = Product.objects.create(
                supplier=supplier,
                name=product_data["name"],
                slug=_unique_product_slug(product_data["name"]),
                description=product_data["description"],
                category=category,
                status=ProductStatus.DRAFT,
            )
            if product_data["image_url"]:
                ProductImage.objects.create(
                    product=product,
                    url=product_data["image_url"],
                    is_primary=True,
                )
            for v in product_data["variants"]:
                ProductVariant.objects.create(
                    product=product,
                    name=v["name"],
                    sku=v["sku"],
                    price=v["price"],
                    compare_at_price=v["compare_at_price"],
                    weight_grams=v["weight_grams"],
                )
            created_products.append(product_data)

        return Response(
            {"created": len(created_products), "products": created_products},
            status=status.HTTP_201_CREATED,
        )
