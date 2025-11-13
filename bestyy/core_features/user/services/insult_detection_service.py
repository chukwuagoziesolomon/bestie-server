"""
Insult detection and conversation moderation service
"""
import re
import logging
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from ..models import WhatsAppConversation, SupportEscalation

logger = logging.getLogger(__name__)


class InsultDetectionService:
    """
    Service for detecting insults and managing conversation boundaries
    """

    # Insult patterns organized by severity
    INSULT_PATTERNS = {
        'mild': [
            r'\b(stupid|dumb|useless|worthless)\b.*\b(bot|system|app|you)\b',
            r'\b(slow|terrible|awful|horrible)\b.*\b(service|response|you)\b',
            r'\b(worst|garbage|trash)\b.*\b(app|system|service)\b',
        ],
        'moderate': [
            r'\b(idiot|moron|jerk|asshole)\b',
            r'\b(fuck|shit|damn)\b.*\b(you|this|it)\b',
            r'\b(suck|sucks)\b.*\b(ass|dick|balls)\b',
            r'\b(bitch|bastard|cunt)\b',
        ],
        'severe': [
            r'\b(fuck\s+you|fuck\s+off|go\s+fuck\s+yourself)\b',
            r'\b(motherfucker|mother\s+fucker)\b',
            r'\b(kill\s+yourself|die|death)\b.*\bthreats?',
            r'\b(rape|sexual|harass)\b.*\b(you|me|us)\b',
        ]
    }

    # Warning thresholds
    WARNING_THRESHOLDS = {
        'mild': 2,      # 2 mild offenses before warning
        'moderate': 1,  # 1 moderate offense triggers warning
        'severe': 0     # Any severe offense triggers immediate action
    }

    def __init__(self):
        self.conversation_history = {}  # Track offenses per conversation

    def analyze_message(self, message_content: str, conversation_id: str) -> Dict:
        """
        Analyze message for insults and return severity assessment
        """
        content_lower = message_content.lower().strip()

        # Initialize conversation tracking if needed
        if conversation_id not in self.conversation_history:
            self.conversation_history[conversation_id] = {
                'mild_offenses': 0,
                'moderate_offenses': 0,
                'severe_offenses': 0,
                'last_offense_time': None,
                'warning_given': False,
                'escalation_triggered': False
            }

        history = self.conversation_history[conversation_id]

        # Check for severe insults first
        severe_matches = self._check_patterns(content_lower, self.INSULT_PATTERNS['severe'])
        if severe_matches:
            history['severe_offenses'] += 1
            history['last_offense_time'] = timezone.now()
            return self._generate_response('severe', severe_matches, history)

        # Check for moderate insults
        moderate_matches = self._check_patterns(content_lower, self.INSULT_PATTERNS['moderate'])
        if moderate_matches:
            history['moderate_offenses'] += 1
            history['last_offense_time'] = timezone.now()
            return self._generate_response('moderate', moderate_matches, history)

        # Check for mild insults
        mild_matches = self._check_patterns(content_lower, self.INSULT_PATTERNS['mild'])
        if mild_matches:
            history['mild_offenses'] += 1
            history['last_offense_time'] = timezone.now()
            return self._generate_response('mild', mild_matches, history)

        # No insults detected
        return {
            'has_insult': False,
            'severity': 'none',
            'action_required': False,
            'response_message': None
        }

    def _check_patterns(self, content: str, patterns: List[str]) -> List[str]:
        """
        Check content against insult patterns
        """
        matches = []
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                matches.append(pattern)
        return matches

    def _generate_response(self, severity: str, matches: List[str], history: Dict) -> Dict:
        """
        Generate appropriate response based on severity and history
        """
        base_response = {
            'has_insult': True,
            'severity': severity,
            'matched_patterns': matches,
            'offense_count': {
                'mild': history['mild_offenses'],
                'moderate': history['moderate_offenses'],
                'severe': history['severe_offenses']
            }
        }

        # Determine action based on severity and thresholds
        if severity == 'severe':
            base_response.update({
                'action_required': True,
                'action_type': 'escalate_immediately',
                'response_message': self._get_severe_response(history),
                'should_pause_chat': True,
                'escalation_reason': 'Severe language violation'
            })
        elif severity == 'moderate':
            if history['moderate_offenses'] >= self.WARNING_THRESHOLDS['moderate']:
                base_response.update({
                    'action_required': True,
                    'action_type': 'warning',
                    'response_message': self._get_moderate_response(history),
                    'warning_given': True
                })
                history['warning_given'] = True
            else:
                base_response.update({
                    'action_required': False,
                    'response_message': self._get_mild_response()
                })
        elif severity == 'mild':
            if history['mild_offenses'] >= self.WARNING_THRESHOLDS['mild'] and not history['warning_given']:
                base_response.update({
                    'action_required': True,
                    'action_type': 'warning',
                    'response_message': self._get_mild_warning_response(history),
                    'warning_given': True
                })
                history['warning_given'] = True
            else:
                base_response.update({
                    'action_required': False,
                    'response_message': self._get_mild_response()
                })

        return base_response

    def _get_mild_response(self) -> str:
        """Response for mild insults or first offenses"""
        return "I understand you're frustrated. I'm here to help resolve this. Could you please tell me specifically what went wrong so I can assist you better?"

    def _get_mild_warning_response(self, history: Dict) -> str:
        """Warning response for repeated mild offenses"""
        return f"I notice there have been a few instances of strong language (this is the {history['mild_offenses']} time). I want to keep our conversation productive and respectful. If you continue to use offensive language, I'll need to pause this chat and connect you with human support. Would you like to continue helping me understand the issue?"

    def _get_moderate_response(self, history: Dict) -> str:
        """Response for moderate insults"""
        return "I want to help you, but I need to keep our conversation respectful. If you'd like to speak with a human agent who can better assist you, I can arrange that. Otherwise, please let me know how I can help resolve your issue without using offensive language."

    def _get_severe_response(self, history: Dict) -> str:
        """Response for severe insults - immediate escalation"""
        return "I'm sorry, but I cannot continue this conversation due to the use of highly offensive language. For your security and ours, I'm pausing this chat and connecting you with our human support team. A representative will contact you shortly by phone to assist you. If this is urgent, please call our support line directly."

    def should_escalate_to_human(self, conversation_id: str) -> bool:
        """
        Determine if conversation should be escalated to human support
        """
        if conversation_id not in self.conversation_history:
            return False

        history = self.conversation_history[conversation_id]

        # Escalate if severe offenses detected
        if history['severe_offenses'] > 0:
            return True

        # Escalate if multiple moderate offenses
        if history['moderate_offenses'] >= 3:
            return True

        # Escalate if many mild offenses
        if history['mild_offenses'] >= 5:
            return True

        # Escalate if warning given and more offenses occur
        if history['warning_given'] and (history['mild_offenses'] >= self.WARNING_THRESHOLDS['mild'] + 2):
            return True

        return False

    def create_escalation_record(self, conversation: WhatsAppConversation,
                               escalation_reason: str, severity: str) -> SupportEscalation:
        """
        Create a support escalation record
        """
        severity_map = {
            'mild': 'low',
            'moderate': 'medium',
            'severe': 'high'
        }

        escalation = SupportEscalation.objects.create(
            conversation=conversation,
            escalation_reason=escalation_reason,
            severity_level=severity_map.get(severity, 'medium'),
            resolution_status='pending'
        )

        logger.info(f"Created support escalation for conversation {conversation.id}: {escalation_reason}")
        return escalation

    def reset_conversation_warnings(self, conversation_id: str):
        """
        Reset warning flags for a conversation (after successful resolution)
        """
        if conversation_id in self.conversation_history:
            history = self.conversation_history[conversation_id]
            history['warning_given'] = False
            history['escalation_triggered'] = False
            logger.info(f"Reset warning flags for conversation {conversation_id}")

    def get_conversation_status(self, conversation_id: str) -> Dict:
        """
        Get current status of conversation moderation
        """
        if conversation_id not in self.conversation_history:
            return {
                'offenses': {'mild': 0, 'moderate': 0, 'severe': 0},
                'warning_given': False,
                'escalation_triggered': False,
                'status': 'clean'
            }

        history = self.conversation_history[conversation_id]
        return {
            'offenses': {
                'mild': history['mild_offenses'],
                'moderate': history['moderate_offenses'],
                'severe': history['severe_offenses']
            },
            'warning_given': history['warning_given'],
            'escalation_triggered': history['escalation_triggered'],
            'last_offense': history['last_offense_time'],
            'status': self._calculate_status(history)
        }

    def _calculate_status(self, history: Dict) -> str:
        """
        Calculate overall conversation status
        """
        if history['severe_offenses'] > 0:
            return 'critical'
        elif history['moderate_offenses'] >= 3 or history['mild_offenses'] >= 5:
            return 'escalated'
        elif history['warning_given']:
            return 'warned'
        elif history['mild_offenses'] > 0 or history['moderate_offenses'] > 0:
            return 'flagged'
        else:
            return 'clean'