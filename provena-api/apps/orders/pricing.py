"""Deterministic order pricing.

A single pass computes the money breakdown for an order at checkout; the result is
snapshotted onto the order so nothing is recomputed later from live config (see ADR-012).

For #141 this covers **VAT only**. Prices are VAT-inclusive, so VAT is *extracted* from the
gross line total rather than added on top: the charged total is unchanged and payouts are
untouched. Discounts (#142) and shipping (#140) slot into this same pass later, which is why
their columns are carried here as zeros.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from apps.catalogue.models import VAT_RATE_FRACTIONS, ProductVariant, VatRate
from apps.suppliers.models import Supplier

if TYPE_CHECKING:
    from apps.orders.models import DiscountCode

_CENTS = Decimal("0.01")
_ZERO = Decimal("0.00")


def _quantise(amount: Decimal) -> Decimal:
    """Round a money value to whole pence, half-up, at a stored boundary."""
    return amount.quantize(_CENTS, rounding=ROUND_HALF_UP)


def allocate_largest_remainder(total: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """Split ``total`` across buckets in proportion to ``weights``.

    Works in integer pence and hands the leftover pence to the largest fractional
    remainders, so the parts sum to ``total`` exactly — no lost or invented pennies
    (ADR-012 §5).
    """
    n = len(weights)
    total_weight = sum(weights, _ZERO)
    if n == 0 or total == _ZERO or total_weight == _ZERO:
        return [_ZERO] * n

    total_pence = int((total * 100).to_integral_value(rounding=ROUND_HALF_UP))
    exact = [total_pence * w / total_weight for w in weights]
    floors = [int(x) for x in exact]  # Decimal -> int truncates toward zero (values are >= 0)
    leftover = total_pence - sum(floors)
    order = sorted(range(n), key=lambda i: exact[i] - floors[i], reverse=True)
    for i in range(leftover):
        floors[order[i]] += 1
    return [Decimal(p) / 100 for p in floors]


def extract_vat(gross: Decimal, vat_rate: str) -> Decimal:
    """VAT contained within a VAT-inclusive gross amount: gross * r / (1 + r)."""
    fraction = VAT_RATE_FRACTIONS[vat_rate]
    if fraction == _ZERO:
        return _ZERO
    return _quantise(gross * fraction / (Decimal("1") + fraction))


@dataclass
class LinePricing:
    variant: ProductVariant
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    vat_rate: str
    vat_amount: Decimal
    discount_amount: Decimal = _ZERO


@dataclass
class SubOrderPricing:
    supplier: Supplier
    lines: list[LinePricing]
    goods_subtotal: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    vat_amount: Decimal
    total: Decimal
    fulfilment_mode: str = ""


@dataclass
class OrderPricing:
    sub_orders: list[SubOrderPricing] = field(default_factory=list)
    goods_subtotal: Decimal = _ZERO
    discount_amount: Decimal = _ZERO
    shipping_amount: Decimal = _ZERO
    vat_amount: Decimal = _ZERO
    total_amount: Decimal = _ZERO


def compute_order_pricing(
    supplier_groups: dict,
    *,
    discount_code: "DiscountCode | None" = None,
    courier_quotes: dict | None = None,
) -> OrderPricing:
    """Compute the full money breakdown for an order.

    ``supplier_groups`` maps supplier id -> {"supplier": Supplier, "items": [
        {"variant": ProductVariant, "quantity": int, "line_total": Decimal}, ...]}
    as assembled by ``orders.services.place_order``.

    Per sub-order (one supplier), in ADR-012 order:
      goods_subtotal -> discount (allocated pro rata) -> shipping
      -> total = goods - discount + shipping -> VAT extracted from the POST-discount goods.

    An order-level ``discount_code`` reduces the goods subtotal; it is allocated across
    sub-orders by their goods value, then within a sub-order across its lines, both by
    largest remainder. VAT is then extracted per line on the post-discount value, so mixed
    VAT rates in one sub-order stay correct.
    """
    order = OrderPricing()
    groups = list(supplier_groups.values())
    group_goods = [sum((i["line_total"] for i in g["items"]), _ZERO) for g in groups]
    order_goods = sum(group_goods, _ZERO)

    total_discount = (
        discount_code.compute_discount(order_goods) if discount_code is not None else _ZERO
    )
    group_discounts = allocate_largest_remainder(total_discount, group_goods)

    for group, goods_subtotal, group_discount in zip(
        groups, group_goods, group_discounts, strict=True
    ):
        supplier = group["supplier"]
        items = group["items"]
        line_totals = [i["line_total"] for i in items]
        line_discounts = allocate_largest_remainder(group_discount, line_totals)

        lines: list[LinePricing] = []
        total_quantity = 0
        sub_vat = _ZERO

        for item, line_discount in zip(items, line_discounts, strict=True):
            variant: ProductVariant = item["variant"]
            quantity: int = item["quantity"]
            line_total: Decimal = item["line_total"]
            vat_rate = getattr(variant.product, "vat_rate", VatRate.STANDARD)
            # VAT is extracted from the post-discount line value (ADR-012 §1).
            line_vat = extract_vat(line_total - line_discount, vat_rate)

            lines.append(
                LinePricing(
                    variant=variant,
                    quantity=quantity,
                    unit_price=variant.price,
                    line_total=line_total,
                    vat_rate=vat_rate,
                    vat_amount=line_vat,
                    discount_amount=line_discount,
                )
            )
            total_quantity += quantity
            sub_vat += line_vat

        # Platform-brokered delivery (ADR-013): a live courier quote overrides the supplier's
        # shipping policy / flat platform fee when one is supplied for this checkout.
        quote = (courier_quotes or {}).get(getattr(supplier, "pk", None))
        if quote is not None:
            shipping_amount = _quantise(quote.fee)
        else:
            # Free-shipping thresholds are evaluated on the pre-discount goods value (ADR-012 §4).
            shipping_amount = _quantise(supplier.compute_shipping(goods_subtotal, total_quantity))
        # Shipping is VAT-inclusive at the standard rate; extract it into the sub-order VAT.
        sub_vat += extract_vat(shipping_amount, VatRate.STANDARD)
        total = goods_subtotal - group_discount + shipping_amount

        sub = SubOrderPricing(
            supplier=supplier,
            lines=lines,
            goods_subtotal=_quantise(goods_subtotal),
            discount_amount=group_discount,
            shipping_amount=shipping_amount,
            # Per-line and shipping VAT are each quantised, so the sub-order VAT reconciles exactly.
            vat_amount=sub_vat,
            total=_quantise(total),
            fulfilment_mode=supplier.fulfilment_mode,
        )
        order.sub_orders.append(sub)
        order.goods_subtotal += sub.goods_subtotal
        order.discount_amount += sub.discount_amount
        order.shipping_amount += sub.shipping_amount
        order.vat_amount += sub.vat_amount
        order.total_amount += sub.total

    return order
