"""
Menu-related serializers for vendor menu management.
"""
from rest_framework import serializers
from django.conf import settings
from bestyy.restaurant_features.product.models import Product
from ..models import VendorProfile
from ..utils.cloudinary_menu_utils import generate_menu_image_urls


class MenuItemSerializer(serializers.ModelSerializer):
    """
    Serializer for menu items (products).
    """
    image = serializers.SerializerMethodField()
    video = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()

    def get_image(self, obj):
        """Get image URL for the menu item."""
        return generate_menu_image_urls(obj.image if hasattr(obj, 'image') and obj.image else None)

    def get_video(self, obj):
        """Get video URL for the menu item."""
        return generate_menu_image_urls(obj.video if hasattr(obj, 'video') and obj.video else None)

    def get_category_name(self, obj):
        """Get category name instead of ID."""
        return obj.category.name if obj.category else None

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'stock_quantity',
            'is_available', 'created_at', 'updated_at', 'category',
            'image', 'video', 'category_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MenuCategorySerializer(serializers.Serializer):
    """
    Serializer for menu categories.
    """
    category = serializers.CharField()
    count = serializers.IntegerField()
    items = serializers.SerializerMethodField()

    def get_items(self, obj):
        """
        Get the list of menu items for a category.
        This method is not directly related to the MenuItem model,
        but it's included here to make the serializer work.
        """
        # This part of the logic would typically involve querying MenuItem
        # based on the category. Since MenuItem is not defined,
        # we'll return an empty list or raise an error.
        # For now, we'll return an empty list as a placeholder.
        return []