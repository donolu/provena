from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

api_v1 = [
    path("auth/", include("apps.accounts.urls")),
    path("suppliers/", include("apps.suppliers.urls")),
    path("catalogue/", include("apps.catalogue.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("orders/", include("apps.orders.urls")),
    path("payments/", include("apps.payments.urls")),
    path("marketplace/", include("apps.marketplace.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("analytics/", include("apps.analytics.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"
    ),
    path("schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
]
