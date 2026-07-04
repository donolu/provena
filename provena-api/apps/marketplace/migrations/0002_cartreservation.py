import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0001_initial"),
        ("catalogue", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CartReservation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("quantity", models.PositiveIntegerField()),
                ("reserved_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                (
                    "cart_item",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reservation",
                        to="marketplace.cartitem",
                    ),
                ),
                (
                    "variant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cart_reservations",
                        to="catalogue.productvariant",
                    ),
                ),
            ],
            options={"ordering": ["expires_at"]},
        ),
    ]
