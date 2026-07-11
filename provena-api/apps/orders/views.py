import secrets

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalogue.models import ProductVariant
from apps.pagination import PaginatedListMixin
from apps.suppliers.permissions import IsApprovedSupplier

from . import services
from .models import Order, OrderReturn, OrderStatus, SubOrder
from .serializers import (
    DispatchSerializer,
    OrderReturnSerializer,
    OrderSerializer,
    PlaceOrderSerializer,
    ReturnActionSerializer,
    ReturnCreateSerializer,
    ReturnRefundSerializer,
    SubOrderListSerializer,
    SubOrderSerializer,
)

WS_TICKET_PREFIX = "ws:ticket:"
WS_TICKET_TTL = 30  # seconds

# ---------------------------------------------------------------------------
# WebSocket ticket
# ---------------------------------------------------------------------------


class WSTicketView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Orders (Buyer)"],
        summary="Issue a short-lived WebSocket ticket",
        description=(
            "Returns a one-time token valid for 30 seconds. "
            "Pass it as `?ticket=<token>` on the WebSocket handshake to avoid "
            "placing the JWT access token in the URL."
        ),
        request=None,
        responses={200: {"type": "object", "properties": {"ticket": {"type": "string"}}}},
    )
    def post(self, request):
        ticket = secrets.token_urlsafe(32)
        cache.set(f"{WS_TICKET_PREFIX}{ticket}", str(request.user.pk), timeout=WS_TICKET_TTL)
        return Response({"ticket": ticket})


# ---------------------------------------------------------------------------
# Buyer views
# ---------------------------------------------------------------------------


@extend_schema(tags=["Orders (Buyer)"])
class OrderListCreateView(PaginatedListMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List own orders",
        parameters=[
            OpenApiParameter("status", description="Filter by order status", required=False),
        ],
        responses={200: OrderSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = (
            Order.objects.filter(buyer=request.user)  # type: ignore[misc]
            .prefetch_related("sub_orders__items", "sub_orders__supplier")
            .select_related("payment")
            .order_by("-created_at")
        )
        if status_filter := request.query_params.get("status"):
            qs = qs.filter(status=status_filter)
        return self.paginate(qs, OrderSerializer, request)

    @extend_schema(
        summary="Place an order",
        request=PlaceOrderSerializer,
        responses={
            201: OrderSerializer,
            400: OpenApiResponse(description="Validation error or insufficient stock"),
        },
    )
    def post(self, request: Request) -> Response:
        ser = PlaceOrderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        variant_ids = [item["variant_id"] for item in d["items"]]
        variants = {
            v.id: v
            for v in ProductVariant.objects.filter(
                id__in=variant_ids, is_active=True
            ).select_related("product__supplier")
        }
        items = []
        for item_data in d["items"]:
            variant = variants.get(item_data["variant_id"])
            if not variant:
                return Response(
                    {"detail": f"Variant {item_data['variant_id']} not found or inactive."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            items.append({"variant": variant, "quantity": item_data["quantity"]})

        shipping = {
            "name": d["shipping_name"],
            "line1": d["shipping_line1"],
            "line2": d.get("shipping_line2", ""),
            "city": d["shipping_city"],
            "postcode": d["shipping_postcode"],
            "country": d["shipping_country"],
            "notes": d.get("notes", ""),
        }
        try:
            order = services.place_order(request.user, items, shipping)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.prefetch_related("sub_orders__items", "sub_orders__supplier").get(
            pk=order.pk
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Orders (Buyer)"])
class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Order detail",
        responses={200: OrderSerializer},
    )
    def get(self, request: Request, reference: str) -> Response:
        order = get_object_or_404(
            Order.objects.prefetch_related(
                "sub_orders__items", "sub_orders__supplier"
            ).select_related("payment"),
            reference=reference,
            buyer=request.user,
        )
        return Response(OrderSerializer(order).data)


@extend_schema(tags=["Orders (Buyer)"])
class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Cancel an order",
        request=None,
        responses={
            200: OrderSerializer,
            400: OpenApiResponse(description="Order cannot be cancelled"),
        },
    )
    def post(self, request: Request, reference: str) -> Response:
        order = get_object_or_404(Order, reference=reference, buyer=request.user)
        if order.status == OrderStatus.DELIVERED:
            return Response(
                {"detail": "Cannot cancel a delivered order."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if order.status == OrderStatus.DISPATCHED:
            return Response(
                {"detail": "Order has already been dispatched. Please raise a dispute instead."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            order = services.cancel_order(order)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        order = Order.objects.prefetch_related("sub_orders__items", "sub_orders__supplier").get(
            pk=order.pk
        )
        return Response(OrderSerializer(order).data)


@extend_schema(tags=["Orders (Buyer)"])
class RequestReturnView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Request a return on a sub-order",
        request=ReturnCreateSerializer,
        responses={
            201: OrderReturnSerializer,
            400: OpenApiResponse(description="Sub-order not delivered or outside return window"),
        },
    )
    def post(self, request: Request, reference: str, pk) -> Response:
        order = get_object_or_404(Order, reference=reference, buyer=request.user)
        sub_order = get_object_or_404(SubOrder, id=pk, order=order)
        ser = ReturnCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            ret = services.request_return(sub_order, request.user, ser.validated_data["reason"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderReturnSerializer(ret).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Supplier views
# ---------------------------------------------------------------------------


@extend_schema(tags=["Orders (Supplier)"])
class SupplierSubOrderListView(PaginatedListMixin, APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        summary="List own sub-orders",
        parameters=[
            OpenApiParameter("status", description="Filter by sub-order status", required=False),
        ],
        responses={200: SubOrderListSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = (
            SubOrder.objects.filter(supplier=request.user.supplier)  # type: ignore[union-attr]
            .select_related("order__buyer", "supplier")
            .order_by("-created_at")
        )
        if status_filter := request.query_params.get("status"):
            qs = qs.filter(status=status_filter)
        return self.paginate(qs, SubOrderListSerializer, request)


@extend_schema(tags=["Orders (Supplier)"])
class SupplierSubOrderDetailView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        summary="Sub-order detail",
        responses={200: SubOrderSerializer},
    )
    def get(self, request: Request, pk) -> Response:
        sub = get_object_or_404(
            SubOrder.objects.prefetch_related("items").select_related("order__buyer", "supplier"),
            id=pk,
            supplier=request.user.supplier,  # type: ignore[union-attr]
        )
        return Response(SubOrderSerializer(sub).data)


@extend_schema(tags=["Orders (Supplier)"])
class SupplierConfirmView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        summary="Confirm a sub-order",
        request=None,
        responses={
            200: SubOrderSerializer,
            400: OpenApiResponse(description="Sub-order not in PENDING state"),
        },
    )
    def post(self, request: Request, pk) -> Response:
        sub = get_object_or_404(SubOrder, id=pk, supplier=request.user.supplier)  # type: ignore[union-attr]
        try:
            sub = services.confirm_sub_order(sub)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        sub = SubOrder.objects.prefetch_related("items").select_related("supplier").get(pk=sub.pk)
        return Response(SubOrderSerializer(sub).data)


@extend_schema(tags=["Orders (Supplier)"])
class SupplierDispatchView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        summary="Dispatch a sub-order",
        request=DispatchSerializer,
        responses={
            200: SubOrderSerializer,
            400: OpenApiResponse(description="Sub-order not in dispatchable state"),
        },
    )
    def post(self, request: Request, pk) -> Response:
        sub = get_object_or_404(SubOrder, id=pk, supplier=request.user.supplier)  # type: ignore[union-attr]
        ser = DispatchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            sub = services.dispatch_sub_order(sub, ser.validated_data.get("tracking_number", ""))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        sub = SubOrder.objects.prefetch_related("items").select_related("supplier").get(pk=sub.pk)
        return Response(SubOrderSerializer(sub).data)


@extend_schema(tags=["Orders (Supplier)"])
class SupplierDeliverView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        summary="Mark a sub-order as delivered",
        request=None,
        responses={
            200: SubOrderSerializer,
            400: OpenApiResponse(description="Sub-order not in DISPATCHED state"),
        },
    )
    def post(self, request: Request, pk) -> Response:
        sub = get_object_or_404(SubOrder, id=pk, supplier=request.user.supplier)  # type: ignore[union-attr]
        try:
            sub = services.deliver_sub_order(sub)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        sub = SubOrder.objects.prefetch_related("items").select_related("supplier").get(pk=sub.pk)
        return Response(SubOrderSerializer(sub).data)


@extend_schema(tags=["Orders (Supplier)"])
class SupplierReturnListView(PaginatedListMixin, APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        summary="List return requests for own sub-orders",
        parameters=[
            OpenApiParameter(
                "status",
                description="Filter by return status (REQUESTED/APPROVED/REJECTED/REFUNDED)",
                required=False,
            ),
        ],
        responses={200: OrderReturnSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = (
            OrderReturn.objects.filter(sub_order__supplier=request.user.supplier)  # type: ignore[union-attr]
            .select_related("raised_by", "sub_order__order", "sub_order__supplier")
            .order_by("-created_at")
        )
        if status_filter := request.query_params.get("status"):
            qs = qs.filter(status=status_filter)
        return self.paginate(qs, OrderReturnSerializer, request)


@extend_schema(tags=["Orders (Supplier)"])
class SupplierApproveReturnView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        summary="Approve a return request",
        request=ReturnActionSerializer,
        responses={
            200: OrderReturnSerializer,
            400: OpenApiResponse(description="Return not in REQUESTED state"),
        },
    )
    def post(self, request: Request, pk) -> Response:
        ret = get_object_or_404(OrderReturn, id=pk, sub_order__supplier=request.user.supplier)  # type: ignore[union-attr]
        ser = ReturnActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            ret = services.approve_return(ret, notes=ser.validated_data.get("notes", ""))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderReturnSerializer(ret).data)


@extend_schema(tags=["Orders (Supplier)"])
class SupplierRejectReturnView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        summary="Reject a return request",
        request=ReturnActionSerializer,
        responses={
            200: OrderReturnSerializer,
            400: OpenApiResponse(description="Return not in REQUESTED state"),
        },
    )
    def post(self, request: Request, pk) -> Response:
        ret = get_object_or_404(OrderReturn, id=pk, sub_order__supplier=request.user.supplier)  # type: ignore[union-attr]
        ser = ReturnActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            ret = services.reject_return(ret, notes=ser.validated_data.get("notes", ""))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderReturnSerializer(ret).data)


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------


@extend_schema(tags=["Admin: Orders"])
class AdminOrderListView(PaginatedListMixin, APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="All orders",
        parameters=[
            OpenApiParameter("status", description="Filter by order status", required=False),
            OpenApiParameter("buyer", description="Filter by buyer email", required=False),
        ],
        responses={200: OrderSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = Order.objects.prefetch_related(
            "sub_orders__items", "sub_orders__supplier"
        ).select_related("buyer", "payment")
        if status_filter := request.query_params.get("status"):
            qs = qs.filter(status=status_filter)
        if buyer_email := request.query_params.get("buyer"):
            qs = qs.filter(buyer__email__icontains=buyer_email)
        return self.paginate(qs, OrderSerializer, request)


@extend_schema(tags=["Admin: Orders"])
class AdminOrderDetailView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Order detail (admin)",
        responses={200: OrderSerializer},
    )
    def get(self, request: Request, reference: str) -> Response:
        order = get_object_or_404(
            Order.objects.prefetch_related(
                "sub_orders__items", "sub_orders__supplier"
            ).select_related("buyer"),
            reference=reference,
        )
        return Response(OrderSerializer(order).data)


@extend_schema(tags=["Admin: Orders"])
class AdminReturnListView(PaginatedListMixin, APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="List all return requests",
        parameters=[
            OpenApiParameter(
                "status",
                description="Filter by return status (REQUESTED/APPROVED/REJECTED/REFUNDED)",
                required=False,
            ),
        ],
        responses={200: OrderReturnSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = OrderReturn.objects.select_related(
            "raised_by", "sub_order__order", "sub_order__supplier"
        )
        if status_filter := request.query_params.get("status"):
            qs = qs.filter(status=status_filter)
        return self.paginate(qs, OrderReturnSerializer, request)


@extend_schema(tags=["Admin: Orders"])
class AdminProcessReturnRefundView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Process refund for an approved return",
        request=ReturnRefundSerializer,
        responses={
            200: OrderReturnSerializer,
            400: OpenApiResponse(description="Return not approved or refund invalid"),
        },
    )
    def post(self, request: Request, pk) -> Response:
        ret = get_object_or_404(OrderReturn, id=pk)
        ser = ReturnRefundSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            ret = services.process_return_refund(
                ret, refund_amount=ser.validated_data.get("amount")
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderReturnSerializer(ret).data)
