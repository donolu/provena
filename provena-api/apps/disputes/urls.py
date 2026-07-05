from django.urls import path

from .views import (
    AdminDisputeListView,
    AdminDisputeRefundView,
    DisputeCloseView,
    DisputeDetailView,
    DisputeEscalateView,
    DisputeListCreateView,
    DisputeResolveView,
    DisputeRespondView,
)

urlpatterns = [
    # Buyer / supplier
    path("", DisputeListCreateView.as_view(), name="dispute-list-create"),
    path("<uuid:pk>/", DisputeDetailView.as_view(), name="dispute-detail"),
    path("<uuid:pk>/respond/", DisputeRespondView.as_view(), name="dispute-respond"),
    path("<uuid:pk>/escalate/", DisputeEscalateView.as_view(), name="dispute-escalate"),
    path("<uuid:pk>/resolve/", DisputeResolveView.as_view(), name="dispute-resolve"),
    path("<uuid:pk>/close/", DisputeCloseView.as_view(), name="dispute-close"),
    # Admin
    path("admin/", AdminDisputeListView.as_view(), name="admin-dispute-list"),
    path("admin/<uuid:pk>/refund/", AdminDisputeRefundView.as_view(), name="admin-dispute-refund"),
]
