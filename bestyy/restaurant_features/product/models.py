from django.db import models
from django.conf import settings
from django.utils import timezone

class Category(models.Model):
    """
    Category model for product categorization.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Categories'


class Product(models.Model):
    """
    Product model representing items that can be sold on the platform.
    """
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    vendor = models.ForeignKey(
        'user.VendorProfile',
        on_delete=models.CASCADE,
        related_name='products'
    )
    image = models.URLField(null=True, blank=True, help_text="Cloudinary image URL")
    video = models.URLField(null=True, blank=True, help_text="Cloudinary video URL")
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.vendor.business_name}"

    class Meta:
        ordering = ['-created_at']


class ProductVariant(models.Model):
    """
    Variant groups for a product (e.g., Size, Extras)
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100, help_text='e.g. Size, Extra')
    required = models.BooleanField(default=False)
    min_select = models.PositiveIntegerField(default=0)
    max_select = models.PositiveIntegerField(default=1)
    sort_order = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.name}"


class ProductVariantOption(models.Model):
    """
    Option for a ProductVariant (e.g., Small, Medium, Large)
    """
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=100)
    price_modifier = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.variant.name}: {self.name} (+{self.price_modifier})"
