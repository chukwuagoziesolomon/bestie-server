from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
import json
import logging

from .models import (
    WhatsAppConversation, 
    WhatsAppMessage, 
    AIResponseTemplate, 
    AIProcessingLog,
    WhatsAppWebhookLog
)
from .serializers import (
    WhatsAppConversationSerializer,
    WhatsAppMessageSerializer,
    WhatsAppMessageCreateSerializer,
    AIResponseTemplateSerializer,
    AIProcessingLogSerializer,
    WhatsAppWebhookLogSerializer,
    WhatsAppWebhookSerializer,
    AIResponseRequestSerializer,
    WhatsAppSendMessageSerializer,
    ConversationStatsSerializer
)
from .ai_service import WhatsAppAIService

logger = logging.getLogger(__name__)


class WhatsAppWebhookView(APIView):
    """
    Webhook endpoint for receiving WhatsApp messages
    """
    permission_classes = [permissions.AllowAny]  # WhatsApp webhooks don't use standard auth
    
    def get(self, request):
        """Handle WhatsApp webhook verification"""
        verify_token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        
        # Verify the webhook token (should match your WhatsApp app settings)
        expected_token = getattr(settings, 'WHATSAPP_VERIFY_TOKEN', 'your_verify_token')
        
        if verify_token == expected_token:
            logger.info("WhatsApp webhook verified successfully")
            return Response(challenge, status=status.HTTP_200_OK)
        else:
            logger.warning(f"Invalid webhook verification token: {verify_token}")
            return Response("Forbidden", status=status.HTTP_403_FORBIDDEN)
    
    def post(self, request):
        """Handle incoming WhatsApp messages"""
        try:
            # Log the webhook data
            webhook_log = WhatsAppWebhookLog.objects.create(
                event_type='message',
                webhook_data=request.data,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Process the webhook
            result = self._process_webhook(request.data)
            
            # Update webhook log
            webhook_log.is_processed = True
            webhook_log.processing_time = result.get('processing_time', 0)
            if not result.get('success', False):
                webhook_log.error_message = result.get('error', 'Unknown error')
            webhook_log.save()
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error processing WhatsApp webhook: {str(e)}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip