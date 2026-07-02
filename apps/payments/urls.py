from django.urls import path

from . import views

urlpatterns = [
    path("webhook/", views.StripeWebhookView.as_view(), name="stripe-webhook"),
    path("create-intent/", views.CreatePaymentIntentView.as_view(), name="payment-create-intent"),
    path("payouts/", views.SupplierPayoutListView.as_view(), name="payout-list"),
    path("admin/payouts/", views.AdminPayoutListView.as_view(), name="admin-payout-list"),
    path(
        "admin/payouts/<uuid:payout_id>/process/",
        views.AdminProcessPayoutView.as_view(),
        name="admin-payout-process",
    ),
    path("admin/", views.AdminPaymentListView.as_view(), name="admin-payment-list"),
    path("", views.PaymentListView.as_view(), name="payment-list"),
    path("<str:reference>/", views.PaymentDetailView.as_view(), name="payment-detail"),
]
