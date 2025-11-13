"""
Support escalation service for handling complex issues and human intervention
"""
import logging
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from django.contrib.auth import get_user_model
from ..models import SupportEscalation, WhatsAppConversation

logger = logging.getLogger(__name__)
User = get_user_model()


class SupportEscalationService:
    """
    Service for managing support escalation workflow
    """

    ESCALATION_TRIGGERS = {
        'insult_severe': {'severity': 'high', 'reason': 'Severe language violation'},
        'insult_multiple': {'severity': 'medium', 'reason': 'Repeated inappropriate language'},
        'complex_modification': {'severity': 'low', 'reason': 'Complex order modification request'},
        'payment_issue': {'severity': 'high', 'reason': 'Payment processing failure'},
        'system_error': {'severity': 'high', 'reason': 'System technical error'},
        'user_request': {'severity': 'low', 'reason': 'User requested human assistance'},
        'high_value_order': {'severity': 'medium', 'reason': 'High-value order assistance'},
        'multiple_vendors': {'severity': 'medium', 'reason': 'Multi-vendor order complexity'},
        'address_issue': {'severity': 'medium', 'reason': 'Delivery address complications'}
    }

    def __init__(self):
        self.escalation_queue = []

    def should_escalate(self, trigger_type: str, context: Dict) -> Tuple[bool, str]:
        """
        Determine if an issue should be escalated to human support
        """
        if trigger_type not in self.ESCALATION_TRIGGERS:
            return False, "Unknown escalation trigger"

        trigger_config = self.ESCALATION_TRIGGERS[trigger_type]

        # Automatic escalation for high severity
        if trigger_config['severity'] == 'high':
            return True, trigger_config['reason']

        # Medium severity - check context
        if trigger_config['severity'] == 'medium':
            if self._check_medium_escalation_criteria(trigger_type, context):
                return True, trigger_config['reason']

        # Low severity - usually user-initiated
        if trigger_config['severity'] == 'low':
            return True, trigger_config['reason']

        return False, "Escalation criteria not met"

    def _check_medium_escalation_criteria(self, trigger_type: str, context: Dict) -> bool:
        """
        Check if medium-severity issues should be escalated
        """
        if trigger_type == 'insult_multiple':
            offense_count = context.get('offense_count', 0)
            return offense_count >= 3

        elif trigger_type == 'high_value_order':
            order_total = context.get('order_total', 0)
            return order_total >= 50000  # ₦50,000 threshold

        elif trigger_type == 'multiple_vendors':
            vendor_count = context.get('vendor_count', 1)
            return vendor_count >= 3

        elif trigger_type == 'address_issue':
            # Escalate if address validation failed multiple times
            attempts = context.get('validation_attempts', 0)
            return attempts >= 3

        return False

    def create_escalation(self, conversation: WhatsAppConversation, trigger_type: str,
                         context: Dict, assigned_agent: Optional[User] = None) -> SupportEscalation:
        """
        Create a new support escalation
        """
        should_escalate, reason = self.should_escalate(trigger_type, context)

        if not should_escalate:
            raise ValueError(f"Escalation criteria not met for trigger: {trigger_type}")

        trigger_config = self.ESCALATION_TRIGGERS[trigger_type]

        escalation = SupportEscalation.objects.create(
            conversation=conversation,
            escalation_reason=reason,
            severity_level=trigger_config['severity'],
            assigned_agent=assigned_agent,
            resolution_status='pending',
            context_data=context
        )

        logger.info(f"Created escalation {escalation.id} for conversation {conversation.id}: {reason}")

        # Add to queue for agent assignment
        self.escalation_queue.append(escalation)

        return escalation

    def assign_agent(self, escalation: SupportEscalation, agent: User) -> bool:
        """
        Assign an agent to handle the escalation
        """
        if escalation.assigned_agent:
            logger.warning(f"Escalation {escalation.id} already assigned to agent {escalation.assigned_agent}")
            return False

        escalation.assigned_agent = agent
        escalation.save()

        logger.info(f"Assigned agent {agent.email} to escalation {escalation.id}")

        # Notify agent (would implement notification system)
        self._notify_agent_assignment(escalation, agent)

        return True

    def _notify_agent_assignment(self, escalation: SupportEscalation, agent: User):
        """
        Notify agent of new escalation assignment
        """
        # This would integrate with your notification system
        # For now, just log it
        logger.info(f"Agent {agent.email} notified of escalation {escalation.id}")

    def get_available_agents(self) -> List[User]:
        """
        Get list of available support agents
        """
        # Get users with support agent role
        agents = User.objects.filter(
            user_roles__role='support_agent',
            user_roles__is_active=True,
            is_active=True
        ).distinct()

        # Filter for currently available agents (simplified)
        # In production, you'd check schedules, current workload, etc.
        available_agents = []
        for agent in agents:
            # Check if agent has reasonable workload
            active_escalations = SupportEscalation.objects.filter(
                assigned_agent=agent,
                resolution_status__in=['pending', 'in_progress']
            ).count()

            if active_escalations < 5:  # Max 5 concurrent escalations per agent
                available_agents.append(agent)

        return available_agents

    def auto_assign_escalation(self, escalation: SupportEscalation) -> Optional[User]:
        """
        Automatically assign escalation to available agent
        """
        available_agents = self.get_available_agents()

        if not available_agents:
            logger.warning("No available agents for escalation assignment")
            return None

        # Simple round-robin assignment (could be enhanced with load balancing)
        # For now, assign to first available agent
        assigned_agent = available_agents[0]

        self.assign_agent(escalation, assigned_agent)
        return assigned_agent

    def resolve_escalation(self, escalation: SupportEscalation, resolution: str,
                          resolved_by: User) -> bool:
        """
        Mark escalation as resolved
        """
        escalation.resolution_status = 'resolved'
        escalation.resolution_notes = resolution
        escalation.resolved_at = timezone.now()
        escalation.resolved_by = resolved_by
        escalation.save()

        logger.info(f"Escalation {escalation.id} resolved by {resolved_by.email}: {resolution}")

        # Remove from queue
        if escalation in self.escalation_queue:
            self.escalation_queue.remove(escalation)

        return True

    def get_pending_escalations(self) -> List[SupportEscalation]:
        """
        Get all pending escalations
        """
        return SupportEscalation.objects.filter(
            resolution_status='pending'
        ).order_by('created_at')

    def get_agent_workload(self, agent: User) -> Dict:
        """
        Get agent's current workload statistics
        """
        total_assigned = SupportEscalation.objects.filter(assigned_agent=agent).count()
        pending_count = SupportEscalation.objects.filter(
            assigned_agent=agent,
            resolution_status='pending'
        ).count()
        in_progress_count = SupportEscalation.objects.filter(
            assigned_agent=agent,
            resolution_status='in_progress'
        ).count()
        resolved_today = SupportEscalation.objects.filter(
            assigned_agent=agent,
            resolution_status='resolved',
            resolved_at__date=timezone.now().date()
        ).count()

        return {
            'total_assigned': total_assigned,
            'pending': pending_count,
            'in_progress': in_progress_count,
            'resolved_today': resolved_today,
            'capacity_remaining': max(0, 5 - (pending_count + in_progress_count))  # Max 5 concurrent
        }

    def generate_escalation_response(self, escalation: SupportEscalation) -> str:
        """
        Generate appropriate response message for escalation
        """
        severity = escalation.severity_level

        if severity == 'high':
            return """🚨 *Support Escalation Required*

I need to connect you with our human support team to resolve this issue. A representative will contact you shortly.

For urgent matters, you can also call our support line directly.

Thank you for your patience."""

        elif severity == 'medium':
            return """📞 *Connecting to Human Support*

This issue requires assistance from our support team. A representative will be with you shortly to help resolve this.

You can also request a callback if you prefer to speak by phone."""

        else:  # low severity
            return """👤 *Transferring to Human Support*

I'll connect you with one of our support representatives who can better assist you with this request.

Please hold while I transfer you."""

    def check_conversation_escalation_history(self, conversation: WhatsAppConversation) -> Dict:
        """
        Check escalation history for a conversation
        """
        escalations = SupportEscalation.objects.filter(
            conversation=conversation
        ).order_by('-created_at')

        recent_escalations = escalations.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        )

        return {
            'total_escalations': escalations.count(),
            'recent_escalations': recent_escalations.count(),
            'last_escalation': escalations.first().created_at if escalations.exists() else None,
            'unresolved_count': escalations.filter(resolution_status__in=['pending', 'in_progress']).count()
        }

    def should_prevent_further_escalation(self, conversation: WhatsAppConversation) -> Tuple[bool, str]:
        """
        Check if conversation should be prevented from further escalations
        """
        history = self.check_conversation_escalation_history(conversation)

        # Prevent escalation if too many recent unresolved escalations
        if history['unresolved_count'] >= 3:
            return True, "Too many unresolved escalations. Please resolve existing issues first."

        # Prevent escalation if too many recent escalations
        if history['recent_escalations'] >= 5:
            return True, "Too many recent escalations. Please allow time for current issues to be resolved."

        return False, "Escalation allowed"