from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    WhatsAppConversation,
    WhatsAppMessage,
    AIResponseTemplate,
    AIProcessingLog,
    WhatsAppWebhookLog
)


@admin.register(WhatsAppConversation)
class WhatsAppConversationAdmin(admin.ModelAdmin):
    list_display = [
        'phone_number', 'user_link', 'is_active', 'language', 
        'message_count', 'last_message_at', 'created_at'
    ]
    list_filter = ['is_active', 'language', 'created_at', 'last_message_at']
    search_fields = ['phone_number', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'message_count_display']
    ordering = ['-last_message_at', '-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'phone_number', 'user', 'is_active')
        }),
        ('Settings', {
            'fields': ('language', 'timezone')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_message_at'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('message_count_display',),
            'classes': ('collapse',)
        }),
    )
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:user_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return '-'
    user_link.short_description = 'User'
    
    def message_count_display(self, obj):
        return obj.messages.count()
    message_count_display.short_description = 'Total Messages'
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = [
        'conversation_phone', 'direction', 'message_type', 'content_preview',
        'is_ai_processed', 'ai_confidence', 'timestamp'
    ]
    list_filter = [
        'direction', 'message_type', 'is_ai_processed', 'timestamp', 'created_at'
    ]
    search_fields = ['content', 'conversation__phone_number', 'message_id']
    readonly_fields = ['id', 'created_at', 'ai_processing_logs']
    ordering = ['-timestamp']
    
    fieldsets = (
        ('Message Information', {
            'fields': ('id', 'conversation', 'message_id', 'message_type', 'direction')
        }),
        ('Content', {
            'fields': ('content', 'media_url')
        }),
        ('AI Processing', {
            'fields': ('is_ai_processed', 'ai_response', 'ai_confidence', 'ai_processing_logs'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('timestamp', 'is_read', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def conversation_phone(self, obj):
        return obj.conversation.phone_number
    conversation_phone.short_description = 'Phone Number'
    
    def content_preview(self, obj):
        preview = obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
        return preview
    content_preview.short_description = 'Content'
    
    def ai_processing_logs(self, obj):
        logs = obj.ai_logs.all()[:5]  # Show last 5 logs
        if logs:
            log_list = []
            for log in logs:
                status_color = 'green' if log.status == 'success' else 'red'
                log_list.append(
                    f'<span style="color: {status_color};">{log.status}</span> - '
                    f'{log.processing_time:.2f}s - {log.created_at.strftime("%H:%M:%S")}'
                )
            return mark_safe('<br>'.join(log_list))
        return 'No logs'
    ai_processing_logs.short_description = 'AI Processing Logs'


@admin.register(AIResponseTemplate)
class AIResponseTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'category', 'language', 'is_active', 'usage_count', 
        'success_rate', 'ai_model', 'updated_at'
    ]
    list_filter = ['category', 'language', 'is_active', 'ai_model', 'created_at']
    search_fields = ['template_text', 'category']
    readonly_fields = ['id', 'usage_count', 'success_rate', 'created_at', 'updated_at']
    ordering = ['category', 'language']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('id', 'category', 'language', 'is_active')
        }),
        ('Content', {
            'fields': ('template_text', 'variables')
        }),
        ('AI Settings', {
            'fields': ('ai_model', 'temperature', 'max_tokens')
        }),
        ('Statistics', {
            'fields': ('usage_count', 'success_rate', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


@admin.register(AIProcessingLog)
class AIProcessingLogAdmin(admin.ModelAdmin):
    list_display = [
        'message_preview', 'template_category', 'status', 'processing_time',
        'tokens_used', 'ai_model_used', 'created_at'
    ]
    list_filter = [
        'status', 'ai_model_used', 'created_at', 'template__category'
    ]
    search_fields = ['message__content', 'error_message', 'ai_model_used']
    readonly_fields = ['id', 'created_at', 'message_details']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Processing Information', {
            'fields': ('id', 'message', 'template', 'status', 'processing_time')
        }),
        ('AI Details', {
            'fields': ('ai_model_used', 'tokens_used', 'prompt_tokens', 'completion_tokens', 'cost')
        }),
        ('Error Information', {
            'fields': ('error_message', 'error_code'),
            'classes': ('collapse',)
        }),
        ('Message Details', {
            'fields': ('message_details',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def message_preview(self, obj):
        preview = obj.message.content[:30] + '...' if len(obj.message.content) > 30 else obj.message.content
        return preview
    message_preview.short_description = 'Message'
    
    def template_category(self, obj):
        return obj.template.get_category_display() if obj.template else '-'
    template_category.short_description = 'Template Category'
    
    def message_details(self, obj):
        return f"""
        <strong>Content:</strong> {obj.message.content}<br>
        <strong>Type:</strong> {obj.message.message_type}<br>
        <strong>Direction:</strong> {obj.message.direction}<br>
        <strong>Phone:</strong> {obj.message.conversation.phone_number}
        """
    message_details.short_description = 'Message Details'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('message', 'template', 'message__conversation')


@admin.register(WhatsAppWebhookLog)
class WhatsAppWebhookLogAdmin(admin.ModelAdmin):
    list_display = [
        'event_type', 'is_processed', 'processing_time', 'ip_address', 'created_at'
    ]
    list_filter = ['event_type', 'is_processed', 'created_at']
    search_fields = ['error_message', 'ip_address']
    readonly_fields = ['id', 'created_at', 'webhook_data_display']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Webhook Information', {
            'fields': ('id', 'event_type', 'is_processed', 'processing_time')
        }),
        ('Request Details', {
            'fields': ('ip_address', 'user_agent', 'created_at')
        }),
        ('Webhook Data', {
            'fields': ('webhook_data_display',),
            'classes': ('collapse',)
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )
    
    def webhook_data_display(self, obj):
        import json
        formatted_data = json.dumps(obj.webhook_data, indent=2)
        return format_html('<pre>{}</pre>', formatted_data)
    webhook_data_display.short_description = 'Webhook Data'


# Customize admin site header
admin.site.site_header = "WhatsApp AI Administration"
admin.site.site_title = "WhatsApp AI Admin"
admin.site.index_title = "Welcome to WhatsApp AI Administration"