"""
Serializers for the Order app.
"""
from rest_framework import serializers
from bestyy.restaurant_features.order.models import Order, OrderItem, OrderStatus
from user.models import VendorProfile, User


class AddressSerializer(serializers.Serializer):
    """Serializer for address information."""
    street = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    postal_code = serializers.CharField()
    country = serializers.CharField()


class OrderItemAdminSerializer(serializers.ModelSerializer):
    """Serializer for order items in admin views."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_id = serializers.UUIDField(source='product.id', read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product_id',
            'product_name',
            'quantity',
            'price',
            'total_price',
            'created_at'
        ]
        read_only_fields = fields
    
    def get_total_price(self, obj):
        """Calculate total price for the order item."""
        return obj.quantity * obj.price


class OrderAdminListSerializer(serializers.ModelSerializer):
    """Serializer for listing orders in admin view."""
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.EmailField(source='customer.email')
    vendor_name = serializers.CharField(source='vendor.business_name')
    vendor_id = serializers.UUIDField(source='vendor.id')
    items_count = serializers.SerializerMethodField()
    delivery_address = serializers.SerializerMethodField()
    order_date = serializers.DateTimeField(source='created_at')
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'order_date',
            'status',
            'total_amount',
            'customer_name',
            'customer_email',
            'vendor_name',
            'vendor_id',
            'delivery_address',
            'items_count',
            'payment_status',
            'payment_method',
            'created_at',
        ]
        read_only_fields = fields
    
    def get_customer_name(self, obj):
        """Return full name of the customer."""
        if obj.customer:
            return f"{obj.customer.first_name} {obj.customer.last_name}"
        return ""
    
    def get_items_count(self, obj):
        """Return count of items in the order."""
        return obj.items.count()
    
    def get_delivery_address(self, obj):
        """Return delivery address as a dictionary."""
        if hasattr(obj, 'delivery_address') and obj.delivery_address:
            # Return the plain text address since it's stored as TextField
            return {'full_address': obj.delivery_address}
        return {}


class OrderDetailAdminSerializer(OrderAdminListSerializer):
    """Detailed order serializer for admin view."""
    items = OrderItemAdminSerializer(many=True, read_only=True)
    billing_address = serializers.SerializerMethodField()
    
    class Meta(OrderAdminListSerializer.Meta):
        fields = OrderAdminListSerializer.Meta.fields + [
            'items',
            'billing_address',
            'delivery_notes',
            'notes',
            'updated_at'
        ]
        read_only_fields = fields
    
    def get_billing_address(self, obj):
        """Return billing address as a dictionary if available."""
        if hasattr(obj, 'billing_address') and obj.billing_address:
            return {
                'street': obj.billing_address.street,
                'city': obj.billing_address.city,
                'state': obj.billing_address.state,
                'postal_code': obj.billing_address.postal_code,
                'country': obj.billing_address.country
            }
        return None


class OrderStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating order status."""
    status = serializers.ChoiceField(choices=OrderStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_status(self, value):
        """Validate that the status is a valid choice."""
        if value not in dict(OrderStatus.choices):
            raise serializers.ValidationError("Invalid status")
        return value


# For backward compatibility and easier imports
OrderAdminSerializer = OrderAdminListSerializer
