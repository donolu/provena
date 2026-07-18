from django.contrib import admin
from django.urls import include, path
from django_prometheus.exports import ExportToDjangoView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from .health import health_check

api_v1 = [
    path("health/", health_check, name="health"),
    path("auth/", include("apps.accounts.urls")),
    path("suppliers/", include("apps.suppliers.urls")),
    path("catalogue/", include("apps.catalogue.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("orders/", include("apps.orders.urls")),
    path("discounts/", include("apps.orders.discount_urls")),
    path("payments/", include("apps.payments.urls")),
    path("delivery/", include("apps.delivery.urls")),
    path("marketplace/", include("apps.marketplace.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("analytics/", include("apps.analytics.urls")),
    path("disputes/", include("apps.disputes.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"
    ),
    path("schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    # Prometheus scrape target. Mounted at root so it is reached internally
    # (api:8000/metrics); public traffic through Nginx never routes here.
    path("metrics", ExportToDjangoView, name="prometheus-metrics"),
]
