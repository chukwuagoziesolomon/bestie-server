"""
Admin API views for support escalation management
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from ..models import SupportEscalation, User
from ..permissions import IsAdminUser

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_support_escalations(request):
    """
    Get list of support escalations for admin dashboard
    Query params:
    - status: filter by resolution status
    - severity: filter by severity level
    - page: pagination
    - limit: items per page
    """
    try:
        # Get query parameters
        status_filter = request.GET.get('status')
        severity_filter = request.GET.get('severity')
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))
        
        # Build query
        escalations = SupportEscalation.objects.all()
        
        if status_filter:
            escalations = escalations.filter(resolution_status=status_filter)
        
        if severity_filter:
            escalations = escalations.filter(severity_level=severity_filter)
        
        # Get total count
        total_count = escalations.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        escalations = escalations[offset:offset + limit]
        
        # Serialize escalation data
        escalation_data = []
        for escalation in escalations:
            data = {
                'id': escalation.id,
                'customer_phone': escalation.customer_phone,
                'customer_name': escalation.customer_name,
                'trigger_type': escalation.get_trigger_type_display(),
                'description': escalation.description,
                'severity_level': escalation.severity_level,
                'severity_display': escalation.get_priority_display(),
                'resolution_status': escalation.resolution_status,
                'status_display': escalation.get_resolution_status_display(),
                'assigned_agent': {
                    'id': escalation.assigned_agent.id,
                    'name': f"{escalation.assigned_agent.first_name} {escalation.assigned_agent.last_name}".strip(),
                    'email': escalation.assigned_agent.email
                } if escalation.assigned_agent else None,
                'contact_attempts': escalation.contact_attempts,
                'last_contact_attempt': escalation.last_contact_attempt.isoformat() if escalation.last_contact_attempt else None,
                'contact_successful': escalation.contact_successful,
                'should_contact': escalation.should_contact_customer(),
                'contact_info': escalation.get_customer_contact_info(),
                'escalation_reason': escalation.escalation_reason,
                'context_data': escalation.context_data,
                'created_at': escalation.created_at.isoformat(),
                'updated_at': escalation.updated_at.isoformat(),
                'resolved_at': escalation.resolved_at.isoformat() if escalation.resolved_at else None,
                'resolved_by': {
                    'id': escalation.resolved_by.id,
                    'name': f"{escalation.resolved_by.first_name} {escalation.resolved_by.last_name}".strip(),
                    'email': escalation.resolved_by.email
                } if escalation.resolved_by else None,
                'resolution_notes': escalation.resolution_notes
            }
            escalation_data.append(data)
        
        # Get summary statistics
        stats = SupportEscalation.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(resolution_status='pending')),
            in_progress=Count('id', filter=Q(resolution_status='in_progress')),
            urgent=Count('id', filter=Q(severity_level='urgent')),
            high=Count('id', filter=Q(severity_level='high')),
            requires_contact=Count('id', filter=Q(
                severity_level__in=['high', 'urgent'],
                resolution_status__in=['pending', 'in_progress'],
                contact_attempts__lt=3
            ))
        )
        
        return Response({
            'success': True,
            'escalations': escalation_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            },
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting support escalations: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to retrieve support escalations'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def assign_escalation_agent(request, escalation_id):
    """
    Assign a support agent to an escalation
    """
    try:
        escalation = get_object_or_404(SupportEscalation, id=escalation_id)
        agent_id = request.data.get('agent_id')
        
        if not agent_id:
            return Response({
                'success': False,
                'error': 'Agent ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        agent = get_object_or_404(User, id=agent_id)
        
        # Use the escalation service to assign the agent
        from ..services.support_escalation_service import SupportEscalationService
        escalation_service = SupportEscalationService()
        
        success = escalation_service.assign_agent(escalation, agent)
        
        if success:
            return Response({
                'success': True,
                'message': f'Escalation assigned to {agent.email}',
                'escalation': {
                    'id': escalation.id,
                    'assigned_agent': {
                        'id': agent.id,
                        'name': f"{agent.first_name} {agent.last_name}".strip(),
                        'email': agent.email
                    }
                }
            })
        else:
            return Response({
                'success': False,
                'error': 'Failed to assign agent'
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error assigning escalation agent: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to assign agent'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def schedule_customer_contact(request, escalation_id):
    """
    Schedule customer contact for an escalation
    """
    try:
        escalation = get_object_or_404(SupportEscalation, id=escalation_id)
        contact_method = request.data.get('contact_method', 'whatsapp')
        
        # Use the escalation service to schedule contact
        from ..services.support_escalation_service import SupportEscalationService
        escalation_service = SupportEscalationService()
        
        success = escalation_service.schedule_customer_contact(escalation_id, contact_method)
        
        if success:
            return Response({
                'success': True,
                'message': f'Customer contact scheduled via {contact_method}',
                'escalation': {
                    'id': escalation.id,
                    'resolution_status': escalation.resolution_status,
                    'contact_info': escalation.get_customer_contact_info()
                }
            })
        else:
            return Response({
                'success': False,
                'error': 'Failed to schedule contact'
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error scheduling customer contact: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to schedule customer contact'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def record_contact_attempt(request, escalation_id):
    """
    Record a customer contact attempt
    """
    try:
        escalation = get_object_or_404(SupportEscalation, id=escalation_id)
        success = request.data.get('success', False)
        notes = request.data.get('notes', '')
        
        # Use the escalation service to record contact
        from ..services.support_escalation_service import SupportEscalationService
        escalation_service = SupportEscalationService()
        
        recorded = escalation_service.record_contact_attempt(escalation_id, success, notes)
        
        if recorded:
            # Refresh escalation from database
            escalation.refresh_from_db()
            
            return Response({
                'success': True,
                'message': 'Contact attempt recorded successfully',
                'escalation': {
                    'id': escalation.id,
                    'contact_attempts': escalation.contact_attempts,
                    'last_contact_attempt': escalation.last_contact_attempt.isoformat() if escalation.last_contact_attempt else None,
                    'contact_successful': escalation.contact_successful,
                    'resolution_status': escalation.resolution_status
                }
            })
        else:
            return Response({
                'success': False,
                'error': 'Failed to record contact attempt'
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error recording contact attempt: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to record contact attempt'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def resolve_escalation(request, escalation_id):
    """
    Mark an escalation as resolved
    """
    try:
        escalation = get_object_or_404(SupportEscalation, id=escalation_id)
        resolution_notes = request.data.get('resolution_notes', '')
        
        if not resolution_notes:
            return Response({
                'success': False,
                'error': 'Resolution notes are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Use the escalation service to resolve
        from ..services.support_escalation_service import SupportEscalationService
        escalation_service = SupportEscalationService()
        
        resolved = escalation_service.resolve_escalation(
            escalation, 
            resolution_notes, 
            request.user
        )
        
        if resolved:
            return Response({
                'success': True,
                'message': 'Escalation resolved successfully',
                'escalation': {
                    'id': escalation.id,
                    'resolution_status': escalation.resolution_status,
                    'resolved_at': escalation.resolved_at.isoformat() if escalation.resolved_at else None,
                    'resolved_by': {
                        'id': request.user.id,
                        'name': f"{request.user.first_name} {request.user.last_name}".strip(),
                        'email': request.user.email
                    },
                    'resolution_notes': escalation.resolution_notes
                }
            })
        else:
            return Response({
                'success': False,
                'error': 'Failed to resolve escalation'
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error resolving escalation: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to resolve escalation'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_escalation_details(request, escalation_id):
    """
    Get detailed information about a specific escalation
    """
    try:
        escalation = get_object_or_404(SupportEscalation, id=escalation_id)
        
        # Get conversation history if available
        conversation_history = []
        if escalation.conversation:
            from bestyy.communication.whatsapp.models import WhatsAppMessage
            messages = WhatsAppMessage.objects.filter(
                conversation=escalation.conversation
            ).order_by('timestamp')[:10]  # Last 10 messages
            
            for msg in messages:
                conversation_history.append({
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat(),
                    'message_type': msg.message_type,
                    'direction': 'incoming' if msg.from_user else 'outgoing'
                })
        
        escalation_detail = {
            'id': escalation.id,
            'customer_phone': escalation.customer_phone,
            'customer_name': escalation.customer_name,
            'trigger_type': escalation.get_trigger_type_display(),
            'description': escalation.description,
            'severity_level': escalation.severity_level,
            'severity_display': escalation.get_priority_display(),
            'resolution_status': escalation.resolution_status,
            'status_display': escalation.get_resolution_status_display(),
            'assigned_agent': {
                'id': escalation.assigned_agent.id,
                'name': f"{escalation.assigned_agent.first_name} {escalation.assigned_agent.last_name}".strip(),
                'email': escalation.assigned_agent.email
            } if escalation.assigned_agent else None,
            'contact_attempts': escalation.contact_attempts,
            'last_contact_attempt': escalation.last_contact_attempt.isoformat() if escalation.last_contact_attempt else None,
            'contact_successful': escalation.contact_successful,
            'should_contact': escalation.should_contact_customer(),
            'contact_info': escalation.get_customer_contact_info(),
            'escalation_reason': escalation.escalation_reason,
            'context_data': escalation.context_data,
            'created_at': escalation.created_at.isoformat(),
            'updated_at': escalation.updated_at.isoformat(),
            'resolved_at': escalation.resolved_at.isoformat() if escalation.resolved_at else None,
            'resolved_by': {
                'id': escalation.resolved_by.id,
                'name': f"{escalation.resolved_by.first_name} {escalation.resolved_by.last_name}".strip(),
                'email': escalation.resolved_by.email
            } if escalation.resolved_by else None,
            'resolution_notes': escalation.resolution_notes,
            'conversation_history': conversation_history
        }
        
        return Response({
            'success': True,
            'escalation': escalation_detail
        })
        
    except Exception as e:
        logger.error(f"Error getting escalation details: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to retrieve escalation details'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_support_agents(request):
    """
    Get list of available support agents
    """
    try:
        from ..services.support_escalation_service import SupportEscalationService
        escalation_service = SupportEscalationService()
        
        agents = escalation_service.get_available_agents()
        
        agent_data = []
        for agent in agents:
            workload = escalation_service.get_agent_workload(agent)
            agent_data.append({
                'id': agent.id,
                'name': f"{agent.first_name} {agent.last_name}".strip(),
                'email': agent.email,
                'workload': workload
            })
        
        return Response({
            'success': True,
            'agents': agent_data
        })
        
    except Exception as e:
        logger.error(f"Error getting support agents: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to retrieve support agents'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)