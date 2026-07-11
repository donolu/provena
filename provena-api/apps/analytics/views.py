import csv
import io
from datetime import date

from django.http import StreamingHttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.suppliers.permissions import IsApprovedSupplier

from . import services

# Response schemas for the list endpoints (the object endpoints document as a
# generic object; their prose descriptions list the fields).
_REVENUE_POINT = inline_serializer(
    name="RevenuePoint",
    fields={
        "period": serializers.CharField(),
        "revenue": serializers.DecimalField(max_digits=12, decimal_places=2),
        "order_count": serializers.IntegerField(),
    },
    many=True,
)
_TOP_PRODUCT = inline_serializer(
    name="TopProduct",
    fields={
        "variant_sku": serializers.CharField(),
        "product_name": serializers.CharField(),
        "units_sold": serializers.IntegerField(),
        "revenue": serializers.DecimalField(max_digits=12, decimal_places=2),
    },
    many=True,
)
_SUPPLIER_PERFORMANCE = inline_serializer(
    name="SupplierPerformance",
    fields={
        "supplier_name": serializers.CharField(),
        "sub_order_count": serializers.IntegerField(),
        "revenue": serializers.DecimalField(max_digits=12, decimal_places=2),
    },
    many=True,
)


def _parse_dates(request) -> tuple[date | None, date | None]:
    from_raw = request.query_params.get("from_date")
    to_raw = request.query_params.get("to_date")
    try:
        from_date = date.fromisoformat(from_raw) if from_raw else None
        to_date = date.fromisoformat(to_raw) if to_raw else None
    except ValueError:
        return None, None
    return from_date, to_date


_DATE_PARAMS = [
    OpenApiParameter(
        "from_date", description="Start date (YYYY-MM-DD). Default: 30 days ago.", required=False
    ),
    OpenApiParameter(
        "to_date", description="End date (YYYY-MM-DD). Default: today.", required=False
    ),
]


class SalesSummaryView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        parameters=[
            *_DATE_PARAMS,
            OpenApiParameter("supplier_id", description="Filter by supplier UUID.", required=False),
        ],
        tags=["Admin: Analytics"],
        summary="Sales summary",
        description="Aggregated revenue, order count, items sold, cancellations, and refunds for the given period.",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        from_date, to_date = _parse_dates(request)
        supplier_id = request.query_params.get("supplier_id") or None
        return Response(services.sales_summary(from_date, to_date, supplier_id))


class RevenueOverTimeView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        parameters=[
            *_DATE_PARAMS,
            OpenApiParameter(
                "granularity",
                description="Aggregation granularity: day (default), week, or month.",
                required=False,
            ),
        ],
        tags=["Admin: Analytics"],
        summary="Revenue over time",
        description="Per-period revenue and order count. Granularity: day | week | month.",
        responses={200: _REVENUE_POINT},
    )
    def get(self, request):
        from_date, to_date = _parse_dates(request)
        granularity = request.query_params.get("granularity", "day")
        return Response(services.revenue_over_time(from_date, to_date, granularity))


class TopProductsView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        parameters=[
            *_DATE_PARAMS,
            OpenApiParameter("limit", description="Max results (default 10).", required=False),
        ],
        tags=["Admin: Analytics"],
        summary="Top products by revenue",
        responses={200: _TOP_PRODUCT},
    )
    def get(self, request):
        from_date, to_date = _parse_dates(request)
        try:
            limit = int(request.query_params.get("limit", 10))
        except ValueError:
            limit = 10
        return Response(services.top_products(from_date, to_date, limit))


class SupplierPerformanceView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        parameters=_DATE_PARAMS,
        tags=["Admin: Analytics"],
        summary="Supplier performance",
        description="Revenue and sub-order count per supplier, sorted by revenue descending.",
        responses={200: _SUPPLIER_PERFORMANCE},
    )
    def get(self, request):
        from_date, to_date = _parse_dates(request)
        return Response(services.supplier_performance(from_date, to_date))


class InventoryHealthView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin: Analytics"],
        summary="Inventory health",
        description="Variant counts: total, low-stock, and out-of-stock.",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        return Response(services.inventory_health())


class ReviewsSummaryView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        parameters=[
            OpenApiParameter("variant_id", description="Filter by variant UUID.", required=False)
        ],
        tags=["Admin: Analytics"],
        summary="Reviews summary",
        description="Totals for all reviews: approved, pending, verified-purchase, average rating.",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        variant_id = request.query_params.get("variant_id") or None
        return Response(services.reviews_summary(variant_id))


class PayoutsSummaryView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin: Analytics"],
        summary="Payouts summary",
        description="Total net payout amounts grouped by status across all suppliers.",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        return Response(services.payouts_summary())


class SupplierOwnSummaryView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        parameters=_DATE_PARAMS,
        tags=["Analytics (Supplier)"],
        summary="My performance summary",
        description="Revenue, sub-order count, and payout totals for the authenticated supplier.",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        from_date, to_date = _parse_dates(request)
        return Response(services.supplier_own_summary(request.user.supplier, from_date, to_date))


class SupplierPayoutsSummaryView(APIView):
    permission_classes = [IsApprovedSupplier]

    @extend_schema(
        tags=["Analytics (Supplier)"],
        summary="My payouts summary",
        description="Net payout amounts by status for the authenticated supplier.",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        return Response(services.payouts_summary(supplier=request.user.supplier))


class AnalyticsExportView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        parameters=_DATE_PARAMS,
        tags=["Admin: Analytics"],
        summary="Export analytics as CSV",
        description=(
            "Streams a multi-sheet CSV zip containing: revenue_over_time, top_products, "
            "and supplier_performance for the given date range."
        ),
        responses={200: None},
        exclude=False,
    )
    def get(self, request):
        from_date, to_date = _parse_dates(request)

        sections = [
            (
                "revenue_over_time",
                ["period", "revenue", "order_count"],
                services.revenue_over_time(from_date, to_date),
            ),
            (
                "top_products",
                ["variant_sku", "product_name", "units_sold", "revenue"],
                services.top_products(from_date, to_date, limit=100),
            ),
            (
                "supplier_performance",
                ["supplier_name", "sub_order_count", "revenue"],
                services.supplier_performance(from_date, to_date),
            ),
        ]

        def rows():
            for section_name, headers, data in sections:
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
                buf.write(f"# {section_name}\n")
                writer.writeheader()
                for row in data:
                    writer.writerow(row)
                buf.write("\n")
                yield buf.getvalue()

        from_label = from_date.isoformat() if from_date else "all"
        to_label = to_date.isoformat() if to_date else "today"
        filename = f"provena_analytics_{from_label}_to_{to_label}.csv"

        response = StreamingHttpResponse(rows(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
