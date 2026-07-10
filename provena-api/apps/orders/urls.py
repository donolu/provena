from django.urls import path

from . import views

urlpatterns = [
    path("ws-ticket/", views.WSTicketView.as_view(), name="ws-ticket"),
    # Supplier (must be before <str:reference>)
    path("supplier/", views.SupplierSubOrderListView.as_view(), name="supplier-suborder-list"),
    path("supplier/returns/", views.SupplierReturnListView.as_view(), name="supplier-return-list"),
    path(
        "supplier/returns/<uuid:pk>/approve/",
        views.SupplierApproveReturnView.as_view(),
        name="supplier-approve-return",
    ),
    path(
        "supplier/returns/<uuid:pk>/reject/",
        views.SupplierRejectReturnView.as_view(),
        name="supplier-reject-return",
    ),
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
    # Admin returns
    path("admin/returns/", views.AdminReturnListView.as_view(), name="admin-return-list"),
    path(
        "admin/returns/<uuid:pk>/refund/",
        views.AdminProcessReturnRefundView.as_view(),
        name="admin-process-return-refund",
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
        "<str:reference>/sub-orders/<uuid:pk>/return/",
        views.RequestReturnView.as_view(),
        name="request-return",
    ),
    path("<str:reference>/", views.OrderDetailView.as_view(), name="order-detail"),
]
