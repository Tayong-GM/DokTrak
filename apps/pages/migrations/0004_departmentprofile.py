from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("pages", "0003_document_assigned_to_transfer"),
    ]

    operations = [
        migrations.CreateModel(
            name="DepartmentProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("department", models.CharField(blank=True, max_length=120)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="department_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
