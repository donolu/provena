# Generated for #141: VAT-inclusive pricing breakdown columns + backfill.

from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations, models

_STANDARD_FRACTION = Decimal("0.20")
_CENTS = Decimal("0.01")
_ZERO = Decimal("0.00")


def _extract_standard_vat(gross: Decimal) -> Decimal:
    """VAT contained within a VAT-inclusive gross at the standard rate."""
    return (gross * _STANDARD_FRACTION / (Decimal("1") + _STANDARD_FRACTION)).quantize(
        _CENTS, rounding=ROUND_HALF_UP
    )


def backfill_pricing(apps, schema_editor):
    """Populate the new breakdown columns for orders that predate them.

    Historically ``total_amount``/``subtotal`` were goods-only with no VAT modelled, so:
    goods_subtotal = the old goods total, discount/shipping = 0, and VAT is extracted at
    the standard rate. Extraction is done per line and aggregated up, so the item, sub-order
    and order VAT totals reconcile exactly (mirroring the live pricing pass).
    """
    Order = apps.get_model("orders", "Order")
    SubOrder = apps.get_model("orders", "SubOrder")
    OrderItem = apps.get_model("orders", "OrderItem")

    for item in OrderItem.objects.all().iterator():
        gross = item.unit_price * item.quantity
        item.vat_rate = "STANDARD"
        item.vat_amount = _extract_standard_vat(gross)
        item.save(update_fields=["vat_rate", "vat_amount"])

    for sub in SubOrder.objects.all().iterator():
        sub_vat = sum(
            (_extract_standard_vat(i.unit_price * i.quantity) for i in sub.items.all()),
            _ZERO,
        )
        sub.goods_subtotal = sub.subtotal
        sub.discount_amount = _ZERO
        sub.shipping_amount = _ZERO
        sub.vat_amount = sub_vat
        sub.save(
            update_fields=["goods_subtotal", "discount_amount", "shipping_amount", "vat_amount"]
        )

    for order in Order.objects.all().iterator():
        subs = list(order.sub_orders.all())
        order.goods_subtotal = order.total_amount
        order.discount_amount = _ZERO
        order.shipping_amount = _ZERO
        order.vat_amount = sum((s.vat_amount for s in subs), _ZERO)
        order.save(
            update_fields=["goods_subtotal", "discount_amount", "shipping_amount", "vat_amount"]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0005_orderreturn_refunding_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="goods_subtotal",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
        migrations.AddField(
            model_name="order",
            name="discount_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
        migrations.AddField(
            model_name="order",
            name="vat_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
        migrations.AddField(
            model_name="suborder",
            name="goods_subtotal",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
        migrations.AddField(
            model_name="suborder",
            name="discount_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
        migrations.AddField(
            model_name="suborder",
            name="shipping_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
        migrations.AddField(
            model_name="suborder",
            name="vat_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="vat_rate",
            field=models.CharField(
                choices=[
                    ("STANDARD", "Standard (20%)"),
                    ("REDUCED", "Reduced (5%)"),
                    ("ZERO", "Zero (0%)"),
                ],
                default="STANDARD",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="vat_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
        migrations.RunPython(backfill_pricing, migrations.RunPython.noop),
    ]
