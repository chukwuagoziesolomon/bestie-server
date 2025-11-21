from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class WhatsAppConversation(models.Model):
    """Model to store WhatsApp conversations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, unique=True, help_text="WhatsApp phone number")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                            help_text="Associated user if linked to account")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    # Conversation metadata
    language = models.CharField(max_length=10, default='en', help_text="Preferred language")
    timezone = models.CharField(max_length=50, default='UTC')
    
    onboarding_state = models.CharField(max_length=32, null=True, blank=True, help_text="Current onboarding state (FSM)")
    pending_email = models.CharField(max_length=128, null=True, blank=True, help_text="Pending user email during onboarding")
    pending_link_action = models.CharField(max_length=64, null=True, blank=True, help_text="Type of pending account link (e.g. email)")
    pending_verification_action = models.CharField(max_length=64, null=True, blank=True, help_text="Pending verification action (e.g. expired_code)")
    awaiting_address = models.BooleanField(default=False, help_text="Whether we're currently awaiting a delivery address from the user")
    context_data = models.JSONField(default=dict, blank=True, help_text="Additional context data for order tracking, etc.")
    
    class Meta:
        db_table = 'whatsapp_conversations'
        ordering = ['-last_message_at', '-created_at']
    
    def __str__(self):
        return f"WhatsApp: {self.phone_number}"


class WhatsAppMessage(models.Model):
    """Model to store individual WhatsApp messages"""
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('location', 'Location'),
        ('contact', 'Contact'),
        ('sticker', 'Sticker'),
    ]
    
    DIRECTION_CHOICES = [
        ('inbound', 'Inbound (from user)'),
        ('outbound', 'Outbound (to user)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(WhatsAppConversation, on_delete=models.CASCADE, 
                                   related_name='messages')
    message_id = models.CharField(max_length=255, unique=True, 
                                help_text="WhatsApp message ID")
    
    # Message content
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    content = models.TextField(help_text="Message content/text")
    media_url = models.URLField(blank=True, null=True, help_text="URL to media file if applicable")
    
    # Message metadata
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    
    # AI processing
    is_ai_processed = models.BooleanField(default=False)
    ai_response = models.TextField(blank=True, null=True, help_text="AI generated response")
    ai_confidence = models.FloatField(null=True, blank=True, help_text="AI confidence score")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'whatsapp_messages'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp']),
            models.Index(fields=['message_id']),
            models.Index(fields=['is_ai_processed']),
        ]
    
    def __str__(self):
        return f"{self.direction}: {self.content[:50]}..."


class AIResponseTemplate(models.Model):
    """Model to store AI response templates for different scenarios"""
    CATEGORY_CHOICES = [
        ('greeting', 'Greeting'),
        ('new_user_greeting', 'New User Greeting'),
        ('returning_user_greeting', 'Returning User Greeting'),
        ('food_recommendation', 'Food Recommendation'),
        ('specific_food_request', 'Specific Food Request'),
        ('order_inquiry', 'Order Inquiry'),
        ('menu_request', 'Menu Request'),
        ('delivery_status', 'Delivery Status'),
        ('payment_help', 'Payment Help'),
        ('complaint', 'Complaint'),
        ('general_info', 'General Information'),
        ('fallback', 'Fallback Response'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    language = models.CharField(max_length=10, default='en')
    
    # Template content
    template_text = models.TextField(help_text="Template text with placeholders")
    variables = models.JSONField(default=list, help_text="List of variable names used in template")
    
    # AI settings
    ai_model = models.CharField(max_length=100, default='mistralai/mistral-7b-instruct')
    temperature = models.FloatField(default=0.7)
    max_tokens = models.IntegerField(default=150)
    
    # Usage tracking
    is_active = models.BooleanField(default=True)
    usage_count = models.PositiveIntegerField(default=0)
    success_rate = models.FloatField(default=0.0, help_text="Success rate of this template")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ai_response_templates'
        unique_together = ['category', 'language']
        ordering = ['category', 'language']
    
    def __str__(self):
        return f"{self.get_category_display()} ({self.language})"


class AIProcessingLog(models.Model):
    """Model to log AI processing activities"""
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('error', 'Error'),
        ('timeout', 'Timeout'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(WhatsAppMessage, on_delete=models.CASCADE, 
                              related_name='ai_logs')
    template = models.ForeignKey(AIResponseTemplate, on_delete=models.SET_NULL, 
                               null=True, blank=True)
    
    # Processing details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    processing_time = models.FloatField(help_text="Processing time in seconds")
    tokens_used = models.IntegerField(null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    
    # Error details
    error_message = models.TextField(blank=True, null=True)
    error_code = models.CharField(max_length=50, blank=True, null=True)
    
    # AI response details
    ai_model_used = models.CharField(max_length=100)
    prompt_tokens = models.IntegerField(null=True, blank=True)
    completion_tokens = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ai_processing_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"AI Log: {self.message.message_id} - {self.status}"


class WhatsAppWebhookLog(models.Model):
    """Model to log WhatsApp webhook events"""
    EVENT_TYPES = [
        ('message', 'Message'),
        ('status', 'Status Update'),
        ('error', 'Error'),
        ('verification', 'Verification'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    webhook_data = models.JSONField(help_text="Raw webhook payload")
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    processing_time = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Request metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'whatsapp_webhook_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type']),
            models.Index(fields=['is_processed']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Webhook: {self.event_type} - {self.created_at}"