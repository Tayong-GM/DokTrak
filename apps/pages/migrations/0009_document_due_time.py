from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0008_document_doc_arch_status_idx_document_doc_inbox_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="due_time",
            field=models.TimeField(blank=True, null=True),
        ),
    ]
