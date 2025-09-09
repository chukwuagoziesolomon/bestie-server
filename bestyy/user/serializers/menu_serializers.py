"""
Menu-related serializers for vendor menu management.
"""
from rest_framework import serializers
from django.conf import settings
from ..models import MenuItem, VendorProfile
from ..utils.cloudinary_menu_utils import generate_menu_image_urls


class MenuItemSerializer(serializers.ModelSerializer):
    """
    Serializer for menu items with full CRUD operations.
    """
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    image_url = serializers.SerializerMethodField()
    image_urls = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuItem
        fields = [
            'id', 'vendor', 'vendor_name', 'dish_name', 'item_description', 
            'price', 'category', 'image', 'image_url', 'image_urls', 'available_now', 
            'quantity', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'vendor', 'created_at', 'updated_at')
    
    def get_image_url(self, obj):
        """Get the full URL for the menu item image."""
        if obj.image:
            # If using Cloudinary, the URL is already absolute
            if hasattr(settings, 'DEFAULT_FILE_STORAGE') and 'cloudinary' in settings.DEFAULT_FILE_STORAGE:
                return obj.image.url
            else:
                # For local storage, build absolute URI
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.image.url)
                return obj.image.url
        return None
    
    def get_image_urls(self, obj):
        """Get multiple image URLs for different sizes (Cloudinary only)."""
        if obj.image and hasattr(settings, 'DEFAULT_FILE_STORAGE') and 'cloudinary' in settings.DEFAULT_FILE_STORAGE:
            try:
                # Extract public_id from Cloudinary URL
                # Cloudinary URLs look like: https://res.cloudinary.com/cloud_name/image/upload/v1234567890/folder/image.jpg
                public_id = obj.image.name  # This should be the public_id for Cloudinary
                return generate_menu_image_urls(public_id)
            except Exception:
                # Fallback to single URL if transformation fails
                return {
                    'thumbnail': obj.image.url,
                    'medium': obj.image.url,
                    'large': obj.image.url,
                    'original': obj.image.url
                }
        return None
    
    def create(self, validated_data):
        """Create a new menu item for the authenticated vendor."""
        # Get the vendor from the request context
        request = self.context.get('request')
        if request and hasattr(request.user, 'vendor_profile'):
            validated_data['vendor'] = request.user.vendor_profile
        else:
            raise serializers.ValidationError("User must have a vendor profile to create menu items.")
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update menu item, ensuring vendor can only update their own items."""
        # Remove vendor from validated_data if present (shouldn't be changeable)
        validated_data.pop('vendor', None)
        return super().update(instance, validated_data)


class MenuItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer specifically for creating menu items.
    """
    class Meta:
        model = MenuItem
        fields = [
            'dish_name', 'item_description', 'price', 'category', 
            'image', 'available_now', 'quantity'
        ]
    
    def validate_price(self, value):
        """Validate that price is positive."""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value
    
    def validate_quantity(self, value):
        """Validate that quantity is not negative."""
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative.")
        return value
    
    def validate_dish_name(self, value):
        """Validate dish name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Dish name is required.")
        return value.strip()


class MenuItemUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer specifically for updating menu items.
    """
    class Meta:
        model = MenuItem
        fields = [
            'dish_name', 'item_description', 'price', 'category', 
            'image', 'available_now', 'quantity'
        ]
    
    def validate_price(self, value):
        """Validate that price is positive."""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value
    
    def validate_quantity(self, value):
        """Validate that quantity is not negative."""
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative.")
        return value


class MenuItemListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing menu items.
    """
    image_url = serializers.SerializerMethodField()
    image_urls = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuItem
        fields = [
            'id', 'dish_name', 'price', 'category', 'image_url', 'image_urls',
            'available_now', 'quantity'
        ]
    
    def get_image_url(self, obj):
        """Get the full URL for the menu item image."""
        if obj.image:
            # If using Cloudinary, the URL is already absolute
            if hasattr(settings, 'DEFAULT_FILE_STORAGE') and 'cloudinary' in settings.DEFAULT_FILE_STORAGE:
                return obj.image.url
            else:
                # For local storage, build absolute URI
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.image.url)
                return obj.image.url
        return None
    
    def get_image_urls(self, obj):
        """Get multiple image URLs for different sizes (Cloudinary only)."""
        if obj.image and hasattr(settings, 'DEFAULT_FILE_STORAGE') and 'cloudinary' in settings.DEFAULT_FILE_STORAGE:
            try:
                # Extract public_id from Cloudinary URL
                public_id = obj.image.name  # This should be the public_id for Cloudinary
                return generate_menu_image_urls(public_id)
            except Exception:
                # Fallback to single URL if transformation fails
                return {
                    'thumbnail': obj.image.url,
                    'medium': obj.image.url,
                    'large': obj.image.url,
                    'original': obj.image.url
                }
        return None


class MenuCategorySerializer(serializers.Serializer):
    """
    Serializer for menu categories.
    """
    category = serializers.CharField()
    count = serializers.IntegerField()
    items = MenuItemListSerializer(many=True, read_only=True)