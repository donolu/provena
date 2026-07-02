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
from .models import Order, OrderDispute, OrderStatus, SubOrder
from .serializers import (
    DispatchSerializer,
    DisputeCreateSerializer,
    DisputeSerializer,
    OrderSerializer,
    PlaceOrderSerializer,
    ResolveDisputeSerializer,
    SubOrderListSerializer,
    SubOrderSerializer,
)

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
            Order.objects.filter(buyer=request.user)
            .prefetch_related("sub_orders__items", "sub_orders__supplier")
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
            Order.objects.prefetch_related("sub_orders__items", "sub_orders__supplier"),
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
class RaiseDisputeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Raise a dispute on a sub-order",
        request=DisputeCreateSerializer,
        responses={
            201: DisputeSerializer,
            400: OpenApiResponse(description="Sub-order not in disputable state"),
        },
    )
    def post(self, request: Request, reference: str, pk) -> Response:
        order = get_object_or_404(Order, reference=reference, buyer=request.user)
        sub_order = get_object_or_404(SubOrder, id=pk, order=order)
        ser = DisputeCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            dispute = services.raise_dispute(sub_order, request.user, ser.validated_data["reason"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DisputeSerializer(dispute).data, status=status.HTTP_201_CREATED)


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
            SubOrder.objects.filter(supplier=request.user.supplier)
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
            supplier=request.user.supplier,
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
        sub = get_object_or_404(SubOrder, id=pk, supplier=request.user.supplier)
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
        sub = get_object_or_404(SubOrder, id=pk, supplier=request.user.supplier)
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
        sub = get_object_or_404(SubOrder, id=pk, supplier=request.user.supplier)
        try:
            sub = services.deliver_sub_order(sub)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        sub = SubOrder.objects.prefetch_related("items").select_related("supplier").get(pk=sub.pk)
        return Response(SubOrderSerializer(sub).data)


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
        ).select_related("buyer")
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
class AdminDisputeListView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="List all disputes",
        parameters=[
            OpenApiParameter(
                "status",
                description="Filter by dispute status (OPEN/RESOLVED/REJECTED)",
                required=False,
            ),
        ],
        responses={200: DisputeSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = OrderDispute.objects.select_related("raised_by", "sub_order__order")
        if status_filter := request.query_params.get("status"):
            qs = qs.filter(status=status_filter)
        return Response(DisputeSerializer(qs, many=True).data)


@extend_schema(tags=["Admin: Orders"])
class AdminResolveDisputeView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Resolve a dispute",
        request=ResolveDisputeSerializer,
        responses={
            200: DisputeSerializer,
            400: OpenApiResponse(description="Dispute is not open"),
        },
    )
    def post(self, request: Request, pk) -> Response:
        dispute = get_object_or_404(OrderDispute, id=pk)
        ser = ResolveDisputeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            dispute = services.resolve_dispute(dispute, ser.validated_data["resolution"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DisputeSerializer(dispute).data)


@extend_schema(tags=["Admin: Orders"])
class AdminRejectDisputeView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Reject a dispute",
        request=ResolveDisputeSerializer,
        responses={
            200: DisputeSerializer,
            400: OpenApiResponse(description="Dispute is not open"),
        },
    )
    def post(self, request: Request, pk) -> Response:
        dispute = get_object_or_404(OrderDispute, id=pk)
        ser = ResolveDisputeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            dispute = services.reject_dispute(dispute, ser.validated_data["resolution"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DisputeSerializer(dispute).data)
