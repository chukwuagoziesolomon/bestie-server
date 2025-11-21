from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Avg
from django.utils import timezone
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
    AIResponseTemplateSerializer,
    AIProcessingLogSerializer,
    WhatsAppWebhookLogSerializer,
    AIResponseRequestSerializer,
    WhatsAppSendMessageSerializer,
    ConversationStatsSerializer
)
from .ai_service import WhatsAppAIService

logger = logging.getLogger(__name__)


class ConversationListView(generics.ListCreateAPIView):
    """
    List and create WhatsApp conversations
    """
    queryset = WhatsAppConversation.objects.all()
    serializer_class = WhatsAppConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter conversations based on user permissions"""
        queryset = super().get_queryset()
        
        # If user is not admin, only show their own conversations
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        # Add search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(phone_number__icontains=search) |
                Q(user__email__icontains=search)
            )
        
        return queryset


class ConversationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a WhatsApp conversation
    """
    queryset = WhatsAppConversation.objects.all()
    serializer_class = WhatsAppConversationSerializer
    permission_classes = [permissions.IsAuthenticated]


class MessageListView(generics.ListCreateAPIView):
    """
    List and create WhatsApp messages
    """
    serializer_class = WhatsAppMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter messages by conversation"""
        conversation_id = self.kwargs.get('conversation_id')
        return WhatsAppMessage.objects.filter(conversation_id=conversation_id)
    
    def perform_create(self, serializer):
        """Create message with conversation context"""
        conversation_id = self.kwargs.get('conversation_id')
        conversation = get_object_or_404(WhatsAppConversation, id=conversation_id)
        serializer.save(conversation=conversation)


class AIResponseTemplateListView(generics.ListCreateAPIView):
    """
    List and create AI response templates
    """
    queryset = AIResponseTemplate.objects.all()
    serializer_class = AIResponseTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]


class AIResponseTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete an AI response template
    """
    queryset = AIResponseTemplate.objects.all()
    serializer_class = AIResponseTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]


class AIProcessingLogListView(generics.ListAPIView):
    """
    List AI processing logs
    """
    queryset = AIProcessingLog.objects.all()
    serializer_class = AIProcessingLogSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    
    def get_queryset(self):
        """Filter logs based on query parameters"""
        queryset = super().get_queryset()
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        return queryset


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_ai_response(request):
    """
    Generate AI response for a specific message
    """
    serializer = AIResponseRequestSerializer(data=request.data)
    
    if serializer.is_valid():
        message_id = serializer.validated_data['message_id']
        context = serializer.validated_data.get('context', {})
        
        try:
            message = WhatsAppMessage.objects.get(id=message_id)
            ai_service = WhatsAppAIService()
            
            # Add conversation context
            conversation_context = ai_service.get_conversation_context(
                str(message.conversation.id)
            )
            context.update(conversation_context)
            
            result = ai_service.process_message(message, context)
            
            return Response(result, status=status.HTTP_200_OK)
            
        except WhatsAppMessage.DoesNotExist:
            return Response(
                {"error": "Message not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_whatsapp_message(request):
    """
    Send a WhatsApp message
    """
    serializer = WhatsAppSendMessageSerializer(data=request.data)
    
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        message = serializer.validated_data['message']
        message_type = serializer.validated_data['message_type']
        media_url = serializer.validated_data.get('media_url')
        
        try:
            ai_service = WhatsAppAIService()
            result = ai_service.send_whatsapp_message(
                phone_number, message, message_type
            )
            
            if result.get('success', False):
                # Get or create conversation
                conversation, created = WhatsAppConversation.objects.get_or_create(
                    phone_number=phone_number,
                    defaults={'language': 'en', 'timezone': 'UTC'}
                )
                
                # Create message record
                WhatsAppMessage.objects.create(
                    conversation=conversation,
                    message_id=result['message_id'],
                    message_type=message_type,
                    content=message,
                    media_url=media_url,
                    direction='outbound',
                    timestamp=timezone.now()
                )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def available_models(request):
    """
    Get available AI models from OpenRouter
    """
    try:
        ai_service = WhatsAppAIService()
        models = ai_service.get_available_models()
        recommended = ai_service.get_recommended_models()
        
        return Response({
            'available_models': models,
            'recommended_models': recommended
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def test_ai_response(request):
    """
    Test AI response generation with OpenRouter
    """
    try:
        message_text = request.data.get('message', 'Hello, how are you?')
        model = request.data.get('model', 'mistralai/mistral-7b-instruct')
        
        ai_service = WhatsAppAIService()
        
        # Create a test message object
        from .models import WhatsAppConversation, WhatsAppMessage
        
        # Get or create a test conversation
        test_conversation, created = WhatsAppConversation.objects.get_or_create(
            phone_number='+1234567890',
            defaults={'language': 'en', 'timezone': 'UTC'}
        )
        
        # Create a test message
        test_message = WhatsAppMessage.objects.create(
            conversation=test_conversation,
            message_id=f"test_{int(time.time())}",
            message_type='text',
            content=message_text,
            direction='inbound',
            timestamp=timezone.now()
        )
        
        # Create a test template
        from .models import AIResponseTemplate
        test_template, created = AIResponseTemplate.objects.get_or_create(
            category='general_info',
            language='en',
            defaults={
                'template_text': 'User message: {user_message}\n\nPlease respond to this message in a helpful and friendly manner.',
                'variables': ['user_message'],
                'ai_model': model,
                'temperature': 0.7,
                'max_tokens': 150
            }
        )
        
        # Process the message
        result = ai_service.process_message(test_message)
        
        # Clean up test data
        test_message.delete()
        if created:
            test_template.delete()
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def conversation_stats(request):
    """
    Get conversation statistics
    """
    try:
        # Calculate stats
        total_conversations = WhatsAppConversation.objects.count()
        active_conversations = WhatsAppConversation.objects.filter(is_active=True).count()
        total_messages = WhatsAppMessage.objects.count()
        
        # Messages today
        today = timezone.now().date()
        messages_today = WhatsAppMessage.objects.filter(
            created_at__date=today
        ).count()
        
        # AI processed messages
        ai_processed_messages = WhatsAppMessage.objects.filter(
            is_ai_processed=True
        ).count()
        
        # AI success rate
        total_ai_logs = AIProcessingLog.objects.count()
        successful_ai_logs = AIProcessingLog.objects.filter(status='success').count()
        ai_success_rate = (successful_ai_logs / total_ai_logs * 100) if total_ai_logs > 0 else 0
        
        # Average response time
        avg_response_time = AIProcessingLog.objects.filter(
            status='success'
        ).aggregate(avg_time=Avg('processing_time'))['avg_time'] or 0
        
        # Top categories
        top_categories = AIProcessingLog.objects.filter(
            status='success',
            template__isnull=False
        ).values('template__category').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        stats_data = {
            'total_conversations': total_conversations,
            'active_conversations': active_conversations,
            'total_messages': total_messages,
            'messages_today': messages_today,
            'ai_processed_messages': ai_processed_messages,
            'ai_success_rate': round(ai_success_rate, 2),
            'avg_response_time': round(avg_response_time, 2),
            'top_categories': list(top_categories)
        }
        
        serializer = ConversationStatsSerializer(stats_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
