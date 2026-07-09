from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0002_add_refunded_amount_partial_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="pending_refund_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]
