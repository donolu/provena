from django.urls import path

from . import views

urlpatterns = [
    path("cart/", views.CartView.as_view(), name="cart"),
    path("cart/merge/", views.CartMergeView.as_view(), name="cart-merge"),
    path("cart/items/", views.CartItemCreateView.as_view(), name="cart-item-create"),
    path("cart/items/<uuid:pk>/", views.CartItemDetailView.as_view(), name="cart-item-detail"),
    path("wishlist/", views.WishlistView.as_view(), name="wishlist"),
    path(
        "wishlist/<uuid:pk>/", views.WishlistItemDeleteView.as_view(), name="wishlist-item-delete"
    ),
    path(
        "products/<uuid:variant_id>/reviews/",
        views.ProductReviewListCreateView.as_view(),
        name="product-reviews",
    ),
    path("admin/reviews/", views.AdminReviewListView.as_view(), name="admin-review-list"),
    path(
        "admin/reviews/<uuid:pk>/approve/",
        views.AdminReviewApproveView.as_view(),
        name="admin-review-approve",
    ),
    path(
        "admin/reviews/<uuid:pk>/",
        views.AdminReviewDeleteView.as_view(),
        name="admin-review-delete",
    ),
]
