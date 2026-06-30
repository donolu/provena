from django.urls import path

from . import views

urlpatterns = [
    path("sales/summary/", views.SalesSummaryView.as_view(), name="analytics-sales-summary"),
    path(
        "sales/over-time/", views.RevenueOverTimeView.as_view(), name="analytics-revenue-over-time"
    ),
    path("products/top/", views.TopProductsView.as_view(), name="analytics-top-products"),
    path(
        "suppliers/", views.SupplierPerformanceView.as_view(), name="analytics-supplier-performance"
    ),
    path("inventory/", views.InventoryHealthView.as_view(), name="analytics-inventory-health"),
    path("reviews/", views.ReviewsSummaryView.as_view(), name="analytics-reviews-summary"),
    path("payouts/", views.PayoutsSummaryView.as_view(), name="analytics-payouts-summary"),
    path(
        "me/summary/", views.SupplierOwnSummaryView.as_view(), name="analytics-supplier-own-summary"
    ),
    path(
        "me/payouts/",
        views.SupplierPayoutsSummaryView.as_view(),
        name="analytics-supplier-own-payouts",
    ),
]
