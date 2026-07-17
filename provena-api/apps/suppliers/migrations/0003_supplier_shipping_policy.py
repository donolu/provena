# Generated for #140: per-supplier shipping policy.

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("suppliers", "0002_supplier_vat_number_supplier_vat_registered"),
    ]

    operations = [
        migrations.AddField(
            model_name="supplier",
            name="shipping_policy",
            field=models.CharField(
                choices=[
                    ("FLAT", "Flat rate"),
                    ("FREE_OVER_THRESHOLD", "Free over threshold"),
                    ("PER_ITEM", "Per item"),
                ],
                default="FLAT",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="supplier",
            name="shipping_flat_rate",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=8),
        ),
        migrations.AddField(
            model_name="supplier",
            name="shipping_per_item_rate",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=8),
        ),
        migrations.AddField(
            model_name="supplier",
            name="free_shipping_threshold",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
