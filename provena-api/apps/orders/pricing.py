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

from apps.catalogue.models import VAT_RATE_FRACTIONS, ProductVariant, VatRate
from apps.suppliers.models import Supplier

_CENTS = Decimal("0.01")
_ZERO = Decimal("0.00")


def _quantise(amount: Decimal) -> Decimal:
    """Round a money value to whole pence, half-up, at a stored boundary."""
    return amount.quantize(_CENTS, rounding=ROUND_HALF_UP)


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


@dataclass
class SubOrderPricing:
    supplier: Supplier
    lines: list[LinePricing]
    goods_subtotal: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    vat_amount: Decimal
    total: Decimal


@dataclass
class OrderPricing:
    sub_orders: list[SubOrderPricing] = field(default_factory=list)
    goods_subtotal: Decimal = _ZERO
    discount_amount: Decimal = _ZERO
    shipping_amount: Decimal = _ZERO
    vat_amount: Decimal = _ZERO
    total_amount: Decimal = _ZERO


def compute_order_pricing(supplier_groups: dict) -> OrderPricing:
    """Compute the full money breakdown for an order.

    ``supplier_groups`` maps supplier id -> {"supplier": Supplier, "items": [
        {"variant": ProductVariant, "quantity": int, "line_total": Decimal}, ...]}
    as assembled by ``orders.services.place_order``.

    Per sub-order (one supplier), in ADR-012 order:
      goods_subtotal -> discount (0 for #141) -> shipping (0 for #141)
      -> total = goods - discount + shipping -> VAT extracted from the gross.
    """
    order = OrderPricing()

    for group in supplier_groups.values():
        supplier = group["supplier"]
        lines: list[LinePricing] = []
        goods_subtotal = _ZERO
        total_quantity = 0
        sub_vat = _ZERO

        for item in group["items"]:
            variant: ProductVariant = item["variant"]
            quantity: int = item["quantity"]
            line_total: Decimal = item["line_total"]
            vat_rate = getattr(variant.product, "vat_rate", VatRate.STANDARD)
            line_vat = extract_vat(line_total, vat_rate)

            lines.append(
                LinePricing(
                    variant=variant,
                    quantity=quantity,
                    unit_price=variant.price,
                    line_total=line_total,
                    vat_rate=vat_rate,
                    vat_amount=line_vat,
                )
            )
            goods_subtotal += line_total
            total_quantity += quantity
            sub_vat += line_vat

        discount_amount = _ZERO
        # Free-shipping thresholds are evaluated on the pre-discount goods value (ADR-012 §4).
        shipping_amount = _quantise(
            supplier.compute_shipping(goods_subtotal - discount_amount, total_quantity)
        )
        # Shipping is VAT-inclusive at the standard rate; extract it into the sub-order VAT.
        sub_vat += extract_vat(shipping_amount, VatRate.STANDARD)
        total = goods_subtotal - discount_amount + shipping_amount

        sub = SubOrderPricing(
            supplier=supplier,
            lines=lines,
            goods_subtotal=_quantise(goods_subtotal),
            discount_amount=discount_amount,
            shipping_amount=shipping_amount,
            # Per-line and shipping VAT are each quantised, so the sub-order VAT reconciles exactly.
            vat_amount=sub_vat,
            total=_quantise(total),
        )
        order.sub_orders.append(sub)
        order.goods_subtotal += sub.goods_subtotal
        order.discount_amount += sub.discount_amount
        order.shipping_amount += sub.shipping_amount
        order.vat_amount += sub.vat_amount
        order.total_amount += sub.total

    return order
