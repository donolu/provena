from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek

from apps.inventory.models import StockLevel
from apps.marketplace.models import Review
from apps.orders.models import Order, OrderItem, OrderStatus, SubOrder
from apps.payments.models import Payment, PaymentStatus, Payout, PayoutStatus


def _default_range() -> tuple[date, date]:
    today = date.today()
    return today - timedelta(days=30), today


def sales_summary(
    from_date: date | None = None, to_date: date | None = None, supplier_id=None
) -> dict:
    if not from_date or not to_date:
        from_date, to_date = _default_range()

    orders = Order.objects.filter(created_at__date__gte=from_date, created_at__date__lte=to_date)
    if supplier_id:
        orders = orders.filter(sub_orders__supplier_id=supplier_id).distinct()

    placed = orders.exclude(status=OrderStatus.CANCELLED)
    totals = placed.aggregate(total_revenue=Sum("total_amount"), total_orders=Count("id"))
    revenue = totals["total_revenue"] or Decimal("0.00")
    order_count = totals["total_orders"] or 0

    items_qs = OrderItem.objects.filter(sub_order__order__in=placed)
    if supplier_id:
        items_qs = items_qs.filter(sub_order__supplier_id=supplier_id)
    items_sold = items_qs.aggregate(total=Sum("quantity"))["total"] or 0

    refunded = Payment.objects.filter(
        order__in=placed,
        status=PaymentStatus.REFUNDED,
        updated_at__date__gte=from_date,
        updated_at__date__lte=to_date,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    avg_order = (
        (revenue / order_count).quantize(Decimal("0.01")) if order_count else Decimal("0.00")
    )

    return {
        "from_date": str(from_date),
        "to_date": str(to_date),
        "total_revenue": str(revenue),
        "total_orders": order_count,
        "total_items_sold": items_sold,
        "avg_order_value": str(avg_order),
        "cancelled_orders": orders.filter(status=OrderStatus.CANCELLED).count(),
        "refunded_amount": str(refunded),
    }


def revenue_over_time(
    from_date: date | None = None, to_date: date | None = None, granularity: str = "day"
) -> list:
    if not from_date or not to_date:
        from_date, to_date = _default_range()

    trunc_fn = {"day": TruncDay, "week": TruncWeek, "month": TruncMonth}.get(granularity, TruncDay)

    rows = (
        Order.objects.filter(created_at__date__gte=from_date, created_at__date__lte=to_date)
        .exclude(status=OrderStatus.CANCELLED)
        .annotate(period=trunc_fn("created_at"))
        .values("period")
        .annotate(revenue=Sum("total_amount"), order_count=Count("id"))
        .order_by("period")
    )
    return [
        {
            "period": row["period"].date().isoformat(),
            "revenue": str(row["revenue"] or Decimal("0.00")),
            "order_count": row["order_count"],
        }
        for row in rows
    ]


def top_products(
    from_date: date | None = None, to_date: date | None = None, limit: int = 10
) -> list:
    if not from_date or not to_date:
        from_date, to_date = _default_range()

    rows = (
        OrderItem.objects.filter(
            sub_order__order__created_at__date__gte=from_date,
            sub_order__order__created_at__date__lte=to_date,
        )
        .exclude(sub_order__order__status=OrderStatus.CANCELLED)
        .values("variant__id", "variant__sku", "variant__product__name")
        .annotate(
            units_sold=Sum("quantity"),
            revenue=Sum(
                ExpressionWrapper(
                    F("unit_price") * F("quantity"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
        )
        .order_by("-revenue")[:limit]
    )
    return [
        {
            "variant_id": str(row["variant__id"]),
            "variant_sku": row["variant__sku"],
            "product_name": row["variant__product__name"],
            "units_sold": row["units_sold"],
            "revenue": str(row["revenue"] or Decimal("0.00")),
        }
        for row in rows
    ]


def supplier_performance(from_date: date | None = None, to_date: date | None = None) -> list:
    if not from_date or not to_date:
        from_date, to_date = _default_range()

    rows = (
        SubOrder.objects.filter(created_at__date__gte=from_date, created_at__date__lte=to_date)
        .exclude(order__status=OrderStatus.CANCELLED)
        .values("supplier__id", "supplier__business_name")
        .annotate(total_revenue=Sum("subtotal"), sub_order_count=Count("id"))
        .order_by("-total_revenue")
    )

    supplier_ids = [row["supplier__id"] for row in rows]
    pending_map = {
        row["sub_order__supplier_id"]: row["pending"]
        for row in Payout.objects.filter(
            sub_order__supplier_id__in=supplier_ids, status=PayoutStatus.PENDING
        )
        .values("sub_order__supplier_id")
        .annotate(pending=Sum("net_amount"))
    }

    return [
        {
            "supplier_id": str(row["supplier__id"]),
            "supplier_name": row["supplier__business_name"],
            "total_revenue": str(row["total_revenue"] or Decimal("0.00")),
            "sub_order_count": row["sub_order_count"],
            "pending_payout": str(
                pending_map.get(row["supplier__id"], Decimal("0.00")) or Decimal("0.00")
            ),
        }
        for row in rows
    ]


def supplier_own_summary(
    supplier, from_date: date | None = None, to_date: date | None = None
) -> dict:
    if not from_date or not to_date:
        from_date, to_date = _default_range()

    sub_orders = SubOrder.objects.filter(
        supplier=supplier,
        created_at__date__gte=from_date,
        created_at__date__lte=to_date,
    ).exclude(order__status=OrderStatus.CANCELLED)

    totals = sub_orders.aggregate(total_revenue=Sum("subtotal"), sub_order_count=Count("id"))

    payout_totals = Payout.objects.filter(supplier=supplier).aggregate(
        pending=Sum("net_amount", filter=Q(status=PayoutStatus.PENDING)),
        paid=Sum("net_amount", filter=Q(status=PayoutStatus.PAID)),
    )

    return {
        "from_date": str(from_date),
        "to_date": str(to_date),
        "total_revenue": str(totals["total_revenue"] or Decimal("0.00")),
        "sub_order_count": totals["sub_order_count"] or 0,
        "pending_payout": str(payout_totals["pending"] or Decimal("0.00")),
        "paid_payout": str(payout_totals["paid"] or Decimal("0.00")),
    }


def inventory_health() -> dict:
    levels = StockLevel.objects.select_related("variant")
    total = levels.count()
    low_stock = sum(1 for level in levels if level.is_low_stock)
    out_of_stock = levels.filter(quantity_available=0).count()
    return {
        "total_variants": total,
        "low_stock_count": low_stock,
        "out_of_stock_count": out_of_stock,
    }


def reviews_summary(variant_id=None) -> dict:
    qs = Review.objects.all()
    if variant_id:
        qs = qs.filter(variant_id=variant_id)

    totals = qs.aggregate(
        total=Count("id"),
        approved=Count("id", filter=Q(is_approved=True)),
        verified=Count("id", filter=Q(is_verified_purchase=True)),
        avg_rating=Avg("rating", filter=Q(is_approved=True)),
    )

    avg = round(float(totals["avg_rating"]), 2) if totals["avg_rating"] else None

    return {
        "total_reviews": totals["total"] or 0,
        "approved_reviews": totals["approved"] or 0,
        "pending_reviews": (totals["total"] or 0) - (totals["approved"] or 0),
        "verified_purchase_count": totals["verified"] or 0,
        "avg_rating": avg,
    }


def payouts_summary(supplier=None) -> dict:
    qs = Payout.objects.all()
    if supplier:
        qs = qs.filter(supplier=supplier)

    totals = qs.aggregate(
        pending=Sum("net_amount", filter=Q(status=PayoutStatus.PENDING)),
        processing=Sum("net_amount", filter=Q(status=PayoutStatus.PROCESSING)),
        paid=Sum("net_amount", filter=Q(status=PayoutStatus.PAID)),
        failed=Sum("net_amount", filter=Q(status=PayoutStatus.FAILED)),
    )

    return {
        "pending": str(totals["pending"] or Decimal("0.00")),
        "processing": str(totals["processing"] or Decimal("0.00")),
        "paid": str(totals["paid"] or Decimal("0.00")),
        "failed": str(totals["failed"] or Decimal("0.00")),
    }
