from django.urls import path

from .views import (
    AdminBannerDetailView,
    AdminBannerListCreateView,
    AdminCategoryDetailView,
    AdminCategoryListCreateView,
    AdminProductBulkActionView,
    AdminProductFeatureView,
    AdminProductListView,
    BannerListView,
    CategoryDetailView,
    CategoryListView,
    ProductArchiveView,
    ProductDetailView,
    ProductImageDetailView,
    ProductImageListCreateView,
    ProductListCreateView,
    ProductPublishView,
    ProductUploadConfirmView,
    ProductUploadPreviewView,
    ProductUploadTemplateView,
    ProductVariantDetailView,
    ProductVariantListCreateView,
    RelatedProductsView,
    SupplierProductListView,
    VariantImageDetailView,
    VariantImageListCreateView,
)

urlpatterns = [
    # Banners (public)
    path("banners/", BannerListView.as_view(), name="banner-list"),
    # Admin: banners
    path("admin/banners/", AdminBannerListCreateView.as_view(), name="admin-banner-list"),
    path("admin/banners/<uuid:pk>/", AdminBannerDetailView.as_view(), name="admin-banner-detail"),
    # Categories (public)
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("categories/<slug:slug>/", CategoryDetailView.as_view(), name="category-detail"),
    # Admin: categories
    path("admin/categories/", AdminCategoryListCreateView.as_view(), name="admin-category-list"),
    path(
        "admin/categories/<slug:slug>/",
        AdminCategoryDetailView.as_view(),
        name="admin-category-detail",
    ),
    # Admin: products
    path("admin/products/", AdminProductListView.as_view(), name="admin-product-list"),
    path("admin/products/bulk/", AdminProductBulkActionView.as_view(), name="admin-product-bulk"),
    path(
        "admin/products/<slug:slug>/feature/",
        AdminProductFeatureView.as_view(),
        name="admin-product-feature",
    ),
    # Products — supplier upload (must come before <slug:slug> routes)
    path(
        "products/upload/template/",
        ProductUploadTemplateView.as_view(),
        name="product-upload-template",
    ),
    path(
        "products/upload/preview/",
        ProductUploadPreviewView.as_view(),
        name="product-upload-preview",
    ),
    path(
        "products/upload/confirm/",
        ProductUploadConfirmView.as_view(),
        name="product-upload-confirm",
    ),
    # Products — supplier-specific MUST come before <slug:slug> to prevent "me" matching
    path("products/me/", SupplierProductListView.as_view(), name="supplier-product-list"),
    path("products/", ProductListCreateView.as_view(), name="product-list-create"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
    path(
        "products/<slug:slug>/related/",
        RelatedProductsView.as_view(),
        name="product-related",
    ),
    path("products/<slug:slug>/publish/", ProductPublishView.as_view(), name="product-publish"),
    path("products/<slug:slug>/archive/", ProductArchiveView.as_view(), name="product-archive"),
    path(
        "products/<slug:slug>/variants/",
        ProductVariantListCreateView.as_view(),
        name="variant-list-create",
    ),
    path(
        "products/<slug:slug>/variants/<uuid:pk>/",
        ProductVariantDetailView.as_view(),
        name="variant-detail",
    ),
    path(
        "products/<slug:slug>/images/",
        ProductImageListCreateView.as_view(),
        name="image-list-create",
    ),
    path(
        "products/<slug:slug>/images/<uuid:pk>/",
        ProductImageDetailView.as_view(),
        name="image-detail",
    ),
    path(
        "products/<slug:slug>/variants/<uuid:pk>/images/",
        VariantImageListCreateView.as_view(),
        name="variant-image-list-create",
    ),
    path(
        "products/<slug:slug>/variants/<uuid:pk>/images/<uuid:img_pk>/",
        VariantImageDetailView.as_view(),
        name="variant-image-detail",
    ),
]
