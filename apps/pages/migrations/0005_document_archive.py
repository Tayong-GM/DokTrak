from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pages", "0004_departmentprofile")]

    operations = [
        migrations.AddField(
            model_name="document",
            name="is_archived",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="document",
            name="archived_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
