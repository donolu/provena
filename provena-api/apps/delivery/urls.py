from django.urls import path

from . import views

urlpatterns = [
    path("webhook/", views.CourierWebhookView.as_view(), name="courier-webhook"),
    path(
        "admin/reconciliation/",
        views.AdminCourierReconciliationView.as_view(),
        name="admin-courier-reconciliation",
    ),
]
