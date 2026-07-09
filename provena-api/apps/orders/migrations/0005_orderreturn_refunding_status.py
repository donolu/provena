from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0004_remove_orderdispute"),
    ]

    operations = [
        migrations.AlterField(
            model_name="orderreturn",
            name="status",
            field=models.CharField(
                choices=[
                    ("REQUESTED", "Requested"),
                    ("APPROVED", "Approved"),
                    ("REFUNDING", "Refunding"),
                    ("REJECTED", "Rejected"),
                    ("REFUNDED", "Refunded"),
                ],
                default="REQUESTED",
                max_length=12,
            ),
        ),
    ]
