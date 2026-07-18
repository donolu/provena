import logging

import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from stripe import SignatureVerificationError as StripeSignatureError

from apps.accounts.audit import audit_action
from apps.orders.models import Order
from apps.pagination import StandardPagination
from apps.suppliers.permissions import IsApprovedSupplier

from . import services
from .models import Payment, Payout
from .serializers import (
    CreatePaymentIntentSerializer,
    PaymentIntentResponseSerializer,
    PaymentSerializer,
    PayoutSerializer,
    RefundSerializer,
)

logger = logging.getLogger(__name__)


class CreatePaymentIntentView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CreatePaymentIntentSerializer,
        responses={201: PaymentIntentResponseSerializer},
        tags=["Payments (Buyer)"],
        summary="Create Stripe PaymentIntent",
        description=(
            "Creates a Stripe PaymentIntent for a pending order owned by the authenticated buyer. "
            "Returns the `client_secret` needed to confirm payment in the frontend. "
            "Idempotent: returns the existing payment if one already exists for the order."
        ),
    )
    def post(self, request):
        ser = CreatePaymentIntentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        order = get_object_or_404(
            Order,
            reference=ser.validated_data["order_reference"],
            buyer=request.user,
        )
        try:
            payment = services.create_payment_intent(order)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "client_secret": payment.stripe_client_secret,
                "payment_id": str(payment.id),
                "amount": payment.amount,
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(tags=["Payments (Buyer)"], summary="List own payments")
    def get_queryset(self):
        return (
            Payment.objects.filter(order__buyer=self.request.user)  # type: ignore[misc]
            .select_related("order")
            .order_by("-created_at")
        )


class PaymentDetailView(generics.RetrieveAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "order__reference"
    lookup_url_kwarg = "reference"

    @extend_schema(tags=["Payments (Buyer)"], summary="Retrieve payment by order reference")
    def get_queryset(self):
        return Payment.objects.filter(order__buyer=self.request.user).select_related("order")  # type: ignore[misc]


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    permission_classes = []
    authentication_classes = []

    @extend_schema(exclude=True)
    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, StripeSignatureError):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        event_type = event["type"]
        obj = event["data"]["object"]

        try:
            if event_type == "payment_intent.succeeded":
                services.handle_payment_succeeded(obj["id"])
            elif event_type == "payment_intent.payment_failed":
                services.handle_payment_failed(obj["id"])
            elif event_type == "payment_intent.canceled":
                services.handle_payment_cancelled(obj["id"])
            elif event_type == "charge.refunded":
                pi_id = getattr(obj, "payment_intent", None)
                if pi_id:
                    services.handle_refund(
                        pi_id,
                        amount_refunded_pence=getattr(obj, "amount_refunded", None),
                        charge_amount_pence=getattr(obj, "amount", None),
                    )
            elif event_type == "account.updated":
                from apps.suppliers.services import handle_connect_account_updated

                handle_connect_account_updated(obj["id"])
        except Payment.DoesNotExist:
            # Event references a payment we do not have (e.g. from another
            # environment sharing the endpoint); acknowledge and move on.
            logger.debug("Stripe webhook for unknown payment; event %s ignored", event_type)
        except Exception:
            logger.exception("Stripe webhook handler error for event %s", event_type)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"status": "ok"})


class SupplierPayoutListView(generics.ListAPIView):
    serializer_class = PayoutSerializer
    permission_classes = [IsApprovedSupplier]
    pagination_class = StandardPagination

    @extend_schema(
        tags=["Payments (Supplier)"],
        summary="List own payouts",
        description="Returns all payouts for the authenticated supplier. Filter by `?status=PENDING|PROCESSING|PAID|FAILED`.",
    )
    def get_queryset(self):
        qs = (
            Payout.objects.filter(supplier=self.request.user.supplier)  # type: ignore[union-attr]
            .select_related("sub_order__order", "supplier")
            .order_by("-created_at")
        )
        payout_status = self.request.query_params.get("status")
        if payout_status:
            qs = qs.filter(status=payout_status)
        return qs


class AdminPayoutListView(generics.ListAPIView):
    serializer_class = PayoutSerializer
    permission_classes = [IsAdminUser]
    pagination_class = StandardPagination

    @extend_schema(
        tags=["Admin: Payments"],
        summary="List all payouts (admin)",
        description="Returns all payouts. Filter by `?status=` or `?supplier=<slug>`.",
    )
    def get_queryset(self):
        qs = Payout.objects.select_related("sub_order__order", "supplier").order_by("-created_at")
        payout_status = self.request.query_params.get("status")
        if payout_status:
            qs = qs.filter(status=payout_status)
        supplier_slug = self.request.query_params.get("supplier")
        if supplier_slug:
            qs = qs.filter(supplier__slug=supplier_slug)
        return qs


class AdminRefundView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin: Payments"],
        summary="Issue a refund (admin)",
        description="Initiates a full or partial refund via Stripe. Omit `amount` for a full refund. "
        "The payment status is updated when Stripe fires the `charge.refunded` webhook.",
        request=RefundSerializer,
        responses={
            200: PaymentSerializer,
            400: OpenApiResponse(description="Invalid amount or payment not refundable"),
        },
    )
    @audit_action(
        "payment.refunded",
        target_type="Payment",
        get_target_id=lambda req, kw: kw.get("payment_id"),
    )
    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id)
        ser = RefundSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        amount = ser.validated_data.get("amount")
        try:
            payment = services.initiate_refund(payment, amount=amount)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PaymentSerializer(payment).data)


class AdminProcessPayoutView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin: Payments"],
        summary="Process a pending payout",
        request=None,
        responses={200: PayoutSerializer},
    )
    def post(self, request, payout_id):
        payout = get_object_or_404(Payout, id=payout_id)
        try:
            payout = services.process_payout(payout)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PayoutSerializer(payout).data)


class AdminPaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAdminUser]
    pagination_class = StandardPagination

    @extend_schema(
        tags=["Admin: Payments"],
        summary="List all payments (admin)",
        description="Returns all payments. Filter by `?status=`.",
    )
    def get_queryset(self):
        qs = Payment.objects.select_related("order").order_by("-created_at")
        payment_status = self.request.query_params.get("status")
        if payment_status:
            qs = qs.filter(status=payment_status)
        return qs
