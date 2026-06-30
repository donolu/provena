from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalogue.models import ProductVariant
from apps.suppliers.permissions import IsApprovedSupplier

from . import services
from .models import StockLevel, StockLot, StockMovement
from .serializers import (
    AdjustStockSerializer,
    ReceiveStockSerializer,
    SetThresholdSerializer,
    StockLevelSerializer,
    StockLotSerializer,
    StockMovementSerializer,
)


def _own_variant(request: Request, variant_id) -> ProductVariant:
    return get_object_or_404(
        ProductVariant,
        id=variant_id,
        product__supplier=request.user.supplier,
    )


@extend_schema(tags=["Inventory (Supplier)"])
class InventoryListView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        summary="List stock levels for own variants",
        parameters=[
            OpenApiParameter(
                "low_stock",
                description='Pass "true" to show only variants at or below threshold',
                required=False,
            ),
        ],
        responses={200: StockLevelSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = (
            StockLevel.objects.filter(variant__product__supplier=request.user.supplier)
            .select_related("variant__product")
            .order_by("variant__sku")
        )
        if request.query_params.get("low_stock") == "true":
            qs = [s for s in qs if s.is_low_stock]
        return Response(StockLevelSerializer(qs, many=True).data)


@extend_schema(tags=["Inventory (Supplier)"])
class InventoryDetailView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        summary="Stock level for a variant",
        responses={200: StockLevelSerializer},
    )
    def get(self, request: Request, variant_id) -> Response:
        variant = _own_variant(request, variant_id)
        level = services.get_or_create_stock_level(variant)
        return Response(StockLevelSerializer(level).data)

    @extend_schema(
        summary="Set low-stock alert threshold",
        request=SetThresholdSerializer,
        responses={200: StockLevelSerializer, 400: OpenApiResponse(description="Validation error")},
    )
    def patch(self, request: Request, variant_id) -> Response:
        variant = _own_variant(request, variant_id)
        ser = SetThresholdSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        level = services.set_low_stock_threshold(variant, ser.validated_data["low_stock_threshold"])
        return Response(StockLevelSerializer(level).data)


@extend_schema(tags=["Inventory (Supplier)"])
class ReceiveStockView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        summary="Receive a stock lot (inbound)",
        request=ReceiveStockSerializer,
        responses={201: StockLevelSerializer, 400: OpenApiResponse(description="Validation error")},
    )
    def post(self, request: Request, variant_id) -> Response:
        variant = _own_variant(request, variant_id)
        ser = ReceiveStockSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        level, _, _ = services.receive_stock(
            variant,
            d["quantity"],
            lot_number=d.get("lot_number", ""),
            expires_at=d.get("expires_at"),
            notes=d.get("notes", ""),
            performed_by=request.user,
        )
        return Response(StockLevelSerializer(level).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Inventory (Supplier)"])
class AdjustStockView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        summary="Manual stock adjustment",
        request=AdjustStockSerializer,
        responses={
            200: StockLevelSerializer,
            400: OpenApiResponse(description="Invalid delta or result would be negative"),
        },
    )
    def post(self, request: Request, variant_id) -> Response:
        variant = _own_variant(request, variant_id)
        ser = AdjustStockSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            level, _ = services.adjust_stock(
                variant,
                ser.validated_data["delta"],
                notes=ser.validated_data["notes"],
                performed_by=request.user,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StockLevelSerializer(level).data)


@extend_schema(tags=["Inventory (Supplier)"])
class StockMovementListView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        summary="Audit log for a variant",
        responses={200: StockMovementSerializer(many=True)},
    )
    def get(self, request: Request, variant_id) -> Response:
        variant = _own_variant(request, variant_id)
        movements = StockMovement.objects.filter(variant=variant).select_related("performed_by")
        return Response(StockMovementSerializer(movements, many=True).data)


@extend_schema(tags=["Inventory (Supplier)"])
class StockLotListView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        summary="Stock lots for a variant",
        responses={200: StockLotSerializer(many=True)},
    )
    def get(self, request: Request, variant_id) -> Response:
        variant = _own_variant(request, variant_id)
        lots = StockLot.objects.filter(variant=variant)
        return Response(StockLotSerializer(lots, many=True).data)


@extend_schema(tags=["Admin: Inventory"])
class AdminInventoryListView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="All stock levels across all suppliers",
        parameters=[
            OpenApiParameter(
                "low_stock",
                description='Pass "true" to show only low-stock variants',
                required=False,
            ),
            OpenApiParameter(
                "supplier",
                description="Filter by supplier slug",
                required=False,
            ),
        ],
        responses={200: StockLevelSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = StockLevel.objects.select_related("variant__product__supplier").order_by(
            "variant__sku"
        )
        if supplier_slug := request.query_params.get("supplier"):
            qs = qs.filter(variant__product__supplier__slug=supplier_slug)
        if request.query_params.get("low_stock") == "true":
            qs = [s for s in qs if s.is_low_stock]
        return Response(StockLevelSerializer(qs, many=True).data)
