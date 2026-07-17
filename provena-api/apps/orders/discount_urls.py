from django.urls import path

from . import views

urlpatterns = [
    path("validate/", views.ValidateDiscountView.as_view(), name="discount-validate"),
    path(
        "admin/",
        views.AdminDiscountCodeListCreateView.as_view(),
        name="admin-discount-list-create",
    ),
    path(
        "admin/<uuid:pk>/",
        views.AdminDiscountCodeDetailView.as_view(),
        name="admin-discount-detail",
    ),
]
