from django.urls import path

from .views import (
    AdminCategoryDetailView,
    AdminCategoryListCreateView,
    AdminProductFeatureView,
    AdminProductListView,
    CategoryDetailView,
    CategoryListView,
    ProductArchiveView,
    ProductDetailView,
    ProductImageDetailView,
    ProductImageListCreateView,
    ProductListCreateView,
    ProductPublishView,
    ProductVariantDetailView,
    ProductVariantListCreateView,
    SupplierProductListView,
)

urlpatterns = [
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
    path(
        "admin/products/<slug:slug>/feature/",
        AdminProductFeatureView.as_view(),
        name="admin-product-feature",
    ),
    # Products — supplier-specific MUST come before <slug:slug> to prevent "me" matching
    path("products/me/", SupplierProductListView.as_view(), name="supplier-product-list"),
    path("products/", ProductListCreateView.as_view(), name="product-list-create"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
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
]
