from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .api_views import (
    ConversationListView,
    ConversationDetailView,
    MessageListView,
    AIResponseTemplateListView,
    AIResponseTemplateDetailView,
    AIProcessingLogListView,
    generate_ai_response,
    send_whatsapp_message,
    conversation_stats,
    available_models,
    test_ai_response
)
from .cors_test_views import cors_test

app_name = 'whatsapp_ai'

urlpatterns = [
    # Webhook endpoint (no authentication required)
    path('webhook/', views.WhatsAppWebhookView.as_view(), name='webhook'),
    
    # Conversation management
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('conversations/<uuid:pk>/', ConversationDetailView.as_view(), name='conversation-detail'),
    
    # Message management
    path('conversations/<uuid:conversation_id>/messages/', MessageListView.as_view(), name='message-list'),
    
    # AI Response Templates (Admin only)
    path('templates/', AIResponseTemplateListView.as_view(), name='template-list'),
    path('templates/<uuid:pk>/', AIResponseTemplateDetailView.as_view(), name='template-detail'),
    
    # AI Processing Logs (Admin only)
    path('logs/', AIProcessingLogListView.as_view(), name='ai-logs'),
    
    # AI Operations
    path('generate-response/', generate_ai_response, name='generate-ai-response'),
    path('send-message/', send_whatsapp_message, name='send-message'),
    
    # Statistics (Admin only)
    path('stats/', conversation_stats, name='conversation-stats'),
    
    # AI Models (Admin only)
    path('models/', available_models, name='available-models'),
    
    # Test AI Response (Admin only)
    path('test/', test_ai_response, name='test-ai-response'),
    
    # CORS Test endpoint
    path('cors-test/', cors_test, name='cors-test'),
]
