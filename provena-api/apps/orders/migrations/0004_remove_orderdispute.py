from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0003_orderreturn"),
    ]

    operations = [
        migrations.DeleteModel(
            name="OrderDispute",
        ),
    ]
