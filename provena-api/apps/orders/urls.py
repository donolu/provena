from django.urls import path

from . import views

urlpatterns = [
    # Supplier (must be before <str:reference>)
    path("supplier/", views.SupplierSubOrderListView.as_view(), name="supplier-suborder-list"),
    path(
        "supplier/<uuid:pk>/",
        views.SupplierSubOrderDetailView.as_view(),
        name="supplier-suborder-detail",
    ),
    path(
        "supplier/<uuid:pk>/confirm/",
        views.SupplierConfirmView.as_view(),
        name="supplier-confirm",
    ),
    path(
        "supplier/<uuid:pk>/dispatch/",
        views.SupplierDispatchView.as_view(),
        name="supplier-dispatch",
    ),
    path(
        "supplier/<uuid:pk>/deliver/",
        views.SupplierDeliverView.as_view(),
        name="supplier-deliver",
    ),
    # Admin disputes (must be before admin/<str:reference>)
    path("admin/disputes/", views.AdminDisputeListView.as_view(), name="admin-dispute-list"),
    path(
        "admin/disputes/<uuid:pk>/resolve/",
        views.AdminResolveDisputeView.as_view(),
        name="admin-resolve-dispute",
    ),
    path(
        "admin/disputes/<uuid:pk>/reject/",
        views.AdminRejectDisputeView.as_view(),
        name="admin-reject-dispute",
    ),
    # Admin orders (must be before <str:reference>)
    path("admin/", views.AdminOrderListView.as_view(), name="admin-order-list"),
    path(
        "admin/<str:reference>/",
        views.AdminOrderDetailView.as_view(),
        name="admin-order-detail",
    ),
    # Buyer — specific patterns before the catch-all detail
    path("", views.OrderListCreateView.as_view(), name="order-list-create"),
    path(
        "<str:reference>/cancel/",
        views.OrderCancelView.as_view(),
        name="order-cancel",
    ),
    path(
        "<str:reference>/sub-orders/<uuid:pk>/dispute/",
        views.RaiseDisputeView.as_view(),
        name="raise-dispute",
    ),
    path("<str:reference>/", views.OrderDetailView.as_view(), name="order-detail"),
]
