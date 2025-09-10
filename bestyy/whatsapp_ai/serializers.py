from rest_framework import serializers
from .models import (
    WhatsAppConversation, 
    WhatsAppMessage, 
    AIResponseTemplate, 
    AIProcessingLog,
    WhatsAppWebhookLog
)


class WhatsAppConversationSerializer(serializers.ModelSerializer):
    """Serializer for WhatsApp conversations"""
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    
    class Meta:
        model = WhatsAppConversation
        fields = [
            'id', 'phone_number', 'user', 'user_email', 'is_active',
            'created_at', 'updated_at', 'last_message_at', 'language',
            'timezone', 'message_count', 'last_message'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'message_count', 'last_message']
    
    def get_message_count(self, obj):
        return obj.messages.count()
    
    def get_last_message(self, obj):
        last_msg = obj.messages.first()
        if last_msg:
            return {
                'content': last_msg.content[:100] + '...' if len(last_msg.content) > 100 else last_msg.content,
                'timestamp': last_msg.timestamp,
                'direction': last_msg.direction
            }
        return None
    
    def get_user_email(self, obj):
        return obj.user.email if obj.user else None


class WhatsAppMessageSerializer(serializers.ModelSerializer):
    """Serializer for WhatsApp messages"""
    conversation_phone = serializers.SerializerMethodField()
    
    class Meta:
        model = WhatsAppMessage
        fields = [
            'id', 'conversation', 'conversation_phone', 'message_id',
            'message_type', 'content', 'media_url', 'direction',
            'timestamp', 'is_read', 'is_ai_processed', 'ai_response',
            'ai_confidence', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'conversation_phone']
    
    def get_conversation_phone(self, obj):
        return obj.conversation.phone_number


class WhatsAppMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating WhatsApp messages"""
    
    class Meta:
        model = WhatsAppMessage
        fields = [
            'conversation', 'message_id', 'message_type', 'content',
            'media_url', 'direction', 'timestamp'
        ]


class AIResponseTemplateSerializer(serializers.ModelSerializer):
    """Serializer for AI response templates"""
    
    class Meta:
        model = AIResponseTemplate
        fields = [
            'id', 'category', 'language', 'template_text', 'variables',
            'ai_model', 'temperature', 'max_tokens', 'is_active',
            'usage_count', 'success_rate', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'success_rate', 'created_at', 'updated_at']


class AIProcessingLogSerializer(serializers.ModelSerializer):
    """Serializer for AI processing logs"""
    message_content = serializers.SerializerMethodField()
    template_category = serializers.SerializerMethodField()
    
    class Meta:
        model = AIProcessingLog
        fields = [
            'id', 'message', 'message_content', 'template', 'template_category',
            'status', 'processing_time', 'tokens_used', 'cost', 'error_message',
            'error_code', 'ai_model_used', 'prompt_tokens', 'completion_tokens',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'message_content', 'template_category']
    
    def get_message_content(self, obj):
        return obj.message.content[:100] + '...' if len(obj.message.content) > 100 else obj.message.content
    
    def get_template_category(self, obj):
        return obj.template.get_category_display() if obj.template else None


class WhatsAppWebhookLogSerializer(serializers.ModelSerializer):
    """Serializer for WhatsApp webhook logs"""
    
    class Meta:
        model = WhatsAppWebhookLog
        fields = [
            'id', 'event_type', 'webhook_data', 'is_processed',
            'processing_time', 'error_message', 'ip_address',
            'user_agent', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WhatsAppWebhookSerializer(serializers.Serializer):
    """Serializer for incoming WhatsApp webhook data"""
    object = serializers.CharField()
    entry = serializers.ListField()
    
    def validate(self, data):
        """Validate webhook structure"""
        if data.get('object') != 'whatsapp_business_account':
            raise serializers.ValidationError("Invalid webhook object type")
        
        if not data.get('entry'):
            raise serializers.ValidationError("No entry data found")
        
        return data


class AIResponseRequestSerializer(serializers.Serializer):
    """Serializer for AI response generation requests"""
    message_id = serializers.UUIDField()
    context = serializers.JSONField(required=False, default=dict)
    language = serializers.CharField(max_length=10, default='en')
    category = serializers.CharField(max_length=50, required=False)
    
    def validate_message_id(self, value):
        """Validate that message exists"""
        try:
            WhatsAppMessage.objects.get(id=value)
        except WhatsAppMessage.DoesNotExist:
            raise serializers.ValidationError("Message not found")
        return value


class WhatsAppSendMessageSerializer(serializers.Serializer):
    """Serializer for sending WhatsApp messages"""
    phone_number = serializers.CharField(max_length=20)
    message = serializers.CharField()
    message_type = serializers.ChoiceField(
        choices=['text', 'image', 'audio', 'video', 'document'],
        default='text'
    )
    media_url = serializers.URLField(required=False, allow_blank=True)
    
    def validate_phone_number(self, value):
        """Validate phone number format"""
        # Remove any non-digit characters except +
        cleaned = ''.join(c for c in value if c.isdigit() or c == '+')
        if not cleaned or len(cleaned) < 10:
            raise serializers.ValidationError("Invalid phone number format")
        return cleaned


class ConversationStatsSerializer(serializers.Serializer):
    """Serializer for conversation statistics"""
    total_conversations = serializers.IntegerField()
    active_conversations = serializers.IntegerField()
    total_messages = serializers.IntegerField()
    messages_today = serializers.IntegerField()
    ai_processed_messages = serializers.IntegerField()
    ai_success_rate = serializers.FloatField()
    avg_response_time = serializers.FloatField()
    top_categories = serializers.ListField(child=serializers.DictField())
