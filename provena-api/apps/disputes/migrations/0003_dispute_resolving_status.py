from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("disputes", "0002_alter_disputeevent_event_type_disputeattachment_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dispute",
            name="status",
            field=models.CharField(
                choices=[
                    ("OPEN", "Open"),
                    ("RESPONDENT_REPLIED", "Respondent replied"),
                    ("ESCALATED", "Escalated to admin"),
                    ("RESOLVING", "Resolving"),
                    ("RESOLVED", "Resolved"),
                    ("CLOSED", "Closed"),
                ],
                default="OPEN",
                max_length=20,
            ),
        ),
    ]
