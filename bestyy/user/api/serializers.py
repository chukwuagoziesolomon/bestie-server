from rest_framework import serializers
from user.models import Order, DailyStats, CourierProfile


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
            'total_price', 'amount_display', 'status', 'status_display',
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
        return f"₦{float(obj.total_price or 0):,.2f}"


class DailyStatsSerializer(serializers.ModelSerializer):
    """Serializer for daily statistics data"""
    date_display = serializers.SerializerMethodField()
    earnings_display = serializers.SerializerMethodField()
    
    class Meta:
        model = DailyStats
        fields = [
            'date', 'date_display', 'total_deliveries', 
            'total_earnings', 'earnings_display', 'avg_delivery_time'
        ]
        read_only_fields = fields
    
    def get_date_display(self, obj):
        """Format date for display"""
        return obj.date.strftime('%B %d, %Y')
    
    def get_earnings_display(self, obj):
        """Format earnings as currency"""
        return f"₦{float(obj.total_earnings or 0):,.0f}"
