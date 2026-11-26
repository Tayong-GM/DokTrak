from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0010_document_completed_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="transfer",
            name="recall_requested_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="transfer",
            name="recall_decided_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="transfer",
            name="recall_approved",
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
