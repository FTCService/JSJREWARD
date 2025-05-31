from django.db import models
from django.utils import timezone
import uuid
from django.contrib.postgres.fields import JSONField  # For PostgreSQL

class SurveySubmission(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    coupon_code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    questions = models.JSONField(default=dict)  # Stores all answers
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.phone} - {self.created_at.strftime('%Y-%m-%d')}"
