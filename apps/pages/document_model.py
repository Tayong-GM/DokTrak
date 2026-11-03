import os

from django.conf import settings
from django.db import models
from django.utils import timezone

# Workflow statuses shown on the Recent Files page (edit freely; no migration needed).
STATUS_CHOICES = [
    ("pending", "Pending"),
    ("in_progress", "In progress"),
    ("completed", "Completed"),
    ("returned", "Returned"),
]


class Document(models.Model):
    """A tracked file created from the Create File page.

    doc_type and priority are plain text on purpose: their allowed values live in
    create_file_config.py, so changing those options never needs a migration.
    """
    reference_no = models.CharField(max_length=30, unique=True)
    title = models.CharField(max_length=150)
    doc_type = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)
    from_office = models.CharField(max_length=100, blank=True)
    to_office = models.CharField(max_length=100, blank=True)
    priority = models.CharField(max_length=20, default="normal")
    due_date = models.DateField(null=True, blank=True)
    confidential = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default="pending")
    attachment = models.FileField(upload_to="documents/%Y/%m/", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference_no} - {self.title}"

    @property
    def is_overdue(self):
        return bool(self.due_date and self.due_date < timezone.localdate() and self.status != "completed")

    @property
    def attachment_name(self):
        return os.path.basename(self.attachment.name) if self.attachment else ""
