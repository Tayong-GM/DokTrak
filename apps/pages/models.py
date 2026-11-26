from django.conf import settings
from django.db import models
from .document_model import Document, Transfer  # noqa: F401  (imported so Django registers these models)


class DepartmentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="department_profile")
    department = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return f"{self.user} — {self.department or 'No department'}"