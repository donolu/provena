from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("orders", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="suborder",
            name="delivered_at",
            field=models.DateTimeField(blank=True, null=True),
        )
    ]
