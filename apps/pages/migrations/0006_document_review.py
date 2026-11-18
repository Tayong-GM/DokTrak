from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("pages", "0005_document_archive"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="review_status",
            field=models.CharField(blank=True, choices=[("approved", "Approved"), ("rejected", "Rejected"), ("checked", "Checked")], max_length=20),
        ),
        migrations.AddField(
            model_name="document",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="document",
            name="reviewed_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_documents", to=settings.AUTH_USER_MODEL),
        ),
    ]
