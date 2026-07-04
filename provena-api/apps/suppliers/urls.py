from django.urls import path

from . import views

urlpatterns = [
    # Public
    path("", views.SupplierListView.as_view(), name="supplier-list"),
    path("register/", views.SupplierRegistrationView.as_view(), name="supplier-register"),
    # Supplier self-service — must come before <slug> to avoid "me" matching as slug
    path("me/", views.SupplierProfileView.as_view(), name="supplier-me"),
    path("me/documents/", views.SupplierDocumentListView.as_view(), name="supplier-documents"),
    path("me/performance/", views.SupplierPerformanceView.as_view(), name="supplier-performance"),
    path("me/stripe-connect/", views.StripeConnectView.as_view(), name="supplier-stripe-connect"),
    # Admin
    path("admin/", views.AdminSupplierListView.as_view(), name="admin-supplier-list"),
    path("admin/documents/", views.AdminDocumentListView.as_view(), name="admin-document-list"),
    path(
        "admin/documents/<uuid:pk>/review/",
        views.AdminDocumentReviewView.as_view(),
        name="admin-document-review",
    ),
    path("admin/<uuid:pk>/", views.AdminSupplierDetailView.as_view(), name="admin-supplier-detail"),
    path(
        "admin/<uuid:pk>/approve/",
        views.AdminSupplierApproveView.as_view(),
        name="admin-supplier-approve",
    ),
    path(
        "admin/<uuid:pk>/suspend/",
        views.AdminSupplierSuspendView.as_view(),
        name="admin-supplier-suspend",
    ),
    path(
        "admin/<uuid:pk>/reject/",
        views.AdminSupplierRejectView.as_view(),
        name="admin-supplier-reject",
    ),
    # Public supplier profile — must be last
    path("<slug:slug>/", views.SupplierPublicDetailView.as_view(), name="supplier-detail"),
]
