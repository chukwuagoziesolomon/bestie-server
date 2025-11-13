"""
Order-related serializers.
"""
from rest_framework import serializers
from bestyy.restaurant_features.order.models import Order
from .user_serializers import UserSerializer
from .vendor_serializers import VendorProfileSerializer


class OrderSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    vendor = VendorProfileSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'customer', 'vendor', 'total_amount', 'order_number', 'delivery_address', 'status', 'created_at']


class UserOrderSerializer(serializers.ModelSerializer):
    """
    Serializer for user orders with additional useful fields
    """
    vendor = VendorProfileSerializer(read_only=True)
    items_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_price_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_name', 'vendor', 'items_count', 
            'total_amount', 'total_price_display', 'delivery_address', 
            'status', 'status_display', 'created_at', 'delivered_at',
            'payment_confirmed', 'user_receipt_confirmed'
        ]
        read_only_fields = fields
    
    def get_items_count(self, obj):
        """Get the number of items in the order"""
        return getattr(obj, 'items', []).count() if hasattr(obj, 'items') else 0
    
    def get_total_price_display(self, obj):
        """Format total price as currency"""
        return f"₦{float(obj.total_amount or 0):,.2f}"


class VendorOrderTrackingSerializer(serializers.ModelSerializer):
    dish_name = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    item = serializers.SerializerMethodField()
    total = serializers.DecimalField(source='total_price', max_digits=10, decimal_places=2)
    status = serializers.CharField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'username', 'dish_name', 'address', 'item', 'total', 'status']

    def get_dish_name(self, obj):
        # Assuming one item per order for simplicity
        return obj.items.first().dish_name if hasattr(obj, 'items') and obj.items.exists() else None

    def get_address(self, obj):
        return obj.delivery_address

    def get_item(self, obj):
        # List all dish names in the order
        return [item.dish_name for item in obj.items.all()] if hasattr(obj, 'items') else []

    def get_username(self, obj):
        return obj.user.get_full_name() or obj.user.username




