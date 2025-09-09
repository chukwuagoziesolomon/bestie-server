from django.db import models
from django.conf import settings
from django.utils import timezone

class Vendor(models.Model):
    """
    Vendor model representing a seller on the platform.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vendor_account'
    )
    business_name = models.CharField(max_length=255)
    business_address = models.TextField()
    phone_number = models.CharField(max_length=20)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.business_name

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'
