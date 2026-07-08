from django.urls import path

from .views import (
    AdminDisputeListView,
    AdminDisputeRefundView,
    DisputeAttachmentView,
    DisputeCloseView,
    DisputeDetailView,
    DisputeEscalateView,
    DisputeListCreateView,
    DisputeMessageView,
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
    path("<uuid:pk>/messages/", DisputeMessageView.as_view(), name="dispute-messages"),
    path("<uuid:pk>/attachments/", DisputeAttachmentView.as_view(), name="dispute-attachments"),
    # Admin
    path("admin/", AdminDisputeListView.as_view(), name="admin-dispute-list"),
    path("admin/<uuid:pk>/refund/", AdminDisputeRefundView.as_view(), name="admin-dispute-refund"),
]
