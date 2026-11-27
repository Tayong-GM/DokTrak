import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("pages", "0011_transfer_recall_permission"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="final_office",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="document",
            name="final_recipient",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="final_documents", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="documented_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="documented_files", to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]