from rest_framework import serializers
from bestyy.restaurant_features.order.models import Order
from bestyy.core_features.user.models import CourierProfile


class DeliverySerializer(serializers.ModelSerializer):
    """Serializer for delivery/order data in the courier dashboard"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    delivery_time_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    amount_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_name', 'pickup_address', 'delivery_address',
            'total_amount', 'amount_display', 'status', 'status_display',
            'created_at', 'delivered_at', 'delivery_time_minutes', 'delivery_time_display'
        ]
        read_only_fields = fields
    
    def get_delivery_time_display(self, obj):
        """Format delivery time for display"""
        if obj.delivery_time_minutes:
            return f"{obj.delivery_time_minutes} mins"
        return "Pending"
    
    def get_amount_display(self, obj):
        """Format amount as currency"""
        return f"₦{float(obj.total_amount or 0):,.2f}"


# DailyStatsSerializer removed - stats calculated on-demand
