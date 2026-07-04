from django.urls import path

from . import views

urlpatterns = [
    path("admin/", views.AdminInventoryListView.as_view(), name="admin-inventory-list"),
    path("", views.InventoryListView.as_view(), name="inventory-list"),
    path("<uuid:variant_id>/", views.InventoryDetailView.as_view(), name="inventory-detail"),
    path("<uuid:variant_id>/receive/", views.ReceiveStockView.as_view(), name="inventory-receive"),
    path("<uuid:variant_id>/adjust/", views.AdjustStockView.as_view(), name="inventory-adjust"),
    path(
        "<uuid:variant_id>/movements/",
        views.StockMovementListView.as_view(),
        name="inventory-movements",
    ),
    path("<uuid:variant_id>/lots/", views.StockLotListView.as_view(), name="inventory-lots"),
]
