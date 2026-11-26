from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0009_document_due_time"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
