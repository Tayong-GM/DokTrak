from django.conf import settings
from django.db import models
from .document_model import Document  # noqa
# Create your models here.

class Product(models.Model):
    id    = models.AutoField(primary_key=True)
    name  = models.CharField(max_length = 100) 
    info  = models.CharField(max_length = 100, default = '')
    price = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.name


class DepartmentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="department_profile")
    department = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return f"{self.user} — {self.department or 'No department'}"

