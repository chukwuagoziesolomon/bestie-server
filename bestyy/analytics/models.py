from django.db import models
from django.conf import settings


class Activity(models.Model):
    """
    Stores discrete activities to surface in the admin dashboard.
    """
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=64, blank=True, help_text="Frontend icon key, e.g., 'shopping-cart'")
    color = models.CharField(max_length=16, blank=True, help_text="Hex or named color for UI badges")
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='activities',
    )
    target_type = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.created_at:%Y-%m-%d %H:%M})"

# Create your models here.
