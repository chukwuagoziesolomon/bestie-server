"""
Serializers for webhook request/response handling
"""
from rest_framework import serializers
from datetime import datetime


class VerificationWebhookSerializer(serializers.Serializer):
    """Serializer for verification webhook data"""
    event_type = serializers.ChoiceField(choices=[
        'verification.approved',
        'verification.rejected',
        'verification.pending'
    ])
    user_type = serializers.ChoiceField(choices=['vendor', 'courier'])
    user_id = serializers.IntegerField()
    data = serializers.DictField(required=False, default=dict)
    timestamp = serializers.DateTimeField(required=False, default=datetime.now)
    
    def validate_data(self, value):
        """Validate event-specific data"""
        event_type = self.initial_data.get('event_type')
        
        if event_type == 'verification.rejected':
            if 'reason' not in value:
                raise serializers.ValidationError("Reason is required for rejection")
        
        return value


class OrderWebhookSerializer(serializers.Serializer):
    """Serializer for order webhook data"""
    event_type = serializers.ChoiceField(choices=[
        'order.updated',
        'order.assigned',
        'order.cancelled',
        'order.completed'
    ])
    user_type = serializers.ChoiceField(choices=['vendor', 'courier', 'customer'])
    user_id = serializers.IntegerField()
    data = serializers.DictField()
    timestamp = serializers.DateTimeField(required=False, default=datetime.now)
    
    def validate_data(self, value):
        """Validate order-specific data"""
        event_type = self.initial_data.get('event_type')
        
        if event_type in ['order.updated', 'order.assigned', 'order.cancelled', 'order.completed']:
            if 'order_id' not in value:
                raise serializers.ValidationError("order_id is required")
        
        if event_type == 'order.assigned':
            if 'courier_id' not in value:
                raise serializers.ValidationError("courier_id is required for assignment")
        
        if event_type == 'order.updated':
            if 'status' not in value:
                raise serializers.ValidationError("status is required for order update")
        
        return value


class PaymentWebhookSerializer(serializers.Serializer):
    """Serializer for payment webhook data"""
    event_type = serializers.ChoiceField(choices=[
        'payment.completed',
        'payment.failed',
        'payment.refunded'
    ])
    user_type = serializers.ChoiceField(choices=['vendor', 'courier', 'customer'])
    user_id = serializers.IntegerField()
    data = serializers.DictField()
    timestamp = serializers.DateTimeField(required=False, default=datetime.now)
    
    def validate_data(self, value):
        """Validate payment-specific data"""
        event_type = self.initial_data.get('event_type')
        
        if event_type in ['payment.completed', 'payment.failed', 'payment.refunded']:
            if 'order_id' not in value:
                raise serializers.ValidationError("order_id is required")
            if 'amount' not in value:
                raise serializers.ValidationError("amount is required")
        
        return value


class DeliveryWebhookSerializer(serializers.Serializer):
    """Serializer for delivery webhook data"""
    event_type = serializers.ChoiceField(choices=[
        'delivery.assigned',
        'delivery.started',
        'delivery.completed',
        'delivery.failed'
    ])
    user_type = serializers.ChoiceField(choices=['vendor', 'courier', 'customer'])
    user_id = serializers.IntegerField()
    data = serializers.DictField()
    timestamp = serializers.DateTimeField(required=False, default=datetime.now)
    
    def validate_data(self, value):
        """Validate delivery-specific data"""
        event_type = self.initial_data.get('event_type')
        
        if event_type in ['delivery.assigned', 'delivery.started', 'delivery.completed', 'delivery.failed']:
            if 'order_id' not in value:
                raise serializers.ValidationError("order_id is required")
        
        if event_type == 'delivery.assigned':
            if 'courier_id' not in value:
                raise serializers.ValidationError("courier_id is required for assignment")
        
        return value


class WebhookResponseSerializer(serializers.Serializer):
    """Serializer for webhook response"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    timestamp = serializers.DateTimeField()
    data = serializers.DictField(required=False, default=dict)
    error = serializers.CharField(required=False)


class UnifiedWebhookSerializer(serializers.Serializer):
    """Unified serializer for all webhook types"""
    event_type = serializers.ChoiceField(choices=[
        # Verification events
        'verification.approved',
        'verification.rejected',
        'verification.pending',
        # Order events
        'order.updated',
        'order.assigned',
        'order.cancelled',
        'order.completed',
        # Payment events
        'payment.completed',
        'payment.failed',
        'payment.refunded',
        # Delivery events
        'delivery.assigned',
        'delivery.started',
        'delivery.completed',
        'delivery.failed'
    ])
    user_type = serializers.ChoiceField(choices=['vendor', 'courier', 'customer'])
    user_id = serializers.IntegerField()
    data = serializers.DictField(required=False, default=dict)
    timestamp = serializers.DateTimeField(required=False, default=datetime.now)
    
    def validate(self, attrs):
        """Validate the entire webhook payload"""
        event_type = attrs.get('event_type')
        data = attrs.get('data', {})
        
        # Validate based on event type
        if event_type.startswith('verification.'):
            if event_type == 'verification.rejected' and 'reason' not in data:
                raise serializers.ValidationError("Reason is required for verification rejection")
        
        elif event_type.startswith('order.'):
            if 'order_id' not in data:
                raise serializers.ValidationError("order_id is required for order events")
            
            if event_type == 'order.assigned' and 'courier_id' not in data:
                raise serializers.ValidationError("courier_id is required for order assignment")
            
            if event_type == 'order.updated' and 'status' not in data:
                raise serializers.ValidationError("status is required for order update")
        
        elif event_type.startswith('payment.'):
            if 'order_id' not in data:
                raise serializers.ValidationError("order_id is required for payment events")
            if 'amount' not in data:
                raise serializers.ValidationError("amount is required for payment events")
        
        elif event_type.startswith('delivery.'):
            if 'order_id' not in data:
                raise serializers.ValidationError("order_id is required for delivery events")
            
            if event_type == 'delivery.assigned' and 'courier_id' not in data:
                raise serializers.ValidationError("courier_id is required for delivery assignment")
        
        return attrs
