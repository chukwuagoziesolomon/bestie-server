"""
AI-First Message Processor
Routes all messages through AI first for intelligent handling
Handles spelling mistakes, context, and edge cases
Includes intention detection, personalization, and preference tracking
"""
import logging
from typing import Dict, Optional, Tuple
from .enhanced_ai_service import EnhancedAIService, SpellCorrector
from .intention_detection_service import IntentionDetectionService, PersonalizedResponseGenerator
from .ai_service import WhatsAppAIService

logger = logging.getLogger(__name__)


class AIFirstMessageProcessor:
    """
    Process messages through AI first before rule-based handlers
    This ensures typos and variations are handled gracefully
    """
    
    def __init__(self, conversation_id: str, user_id: str = None, user_name: str = None):
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.user_name = user_name or "there"
        self.enhanced_ai = EnhancedAIService(conversation_id)
        self.base_ai = WhatsAppAIService()
        self.spell_corrector = SpellCorrector()
        self.intention_detector = IntentionDetectionService(user_id, user_name)
        self.response_generator = PersonalizedResponseGenerator(user_name)
    
    def should_bypass_ai(self, content: str, context: Dict) -> Tuple[bool, Optional[str]]:
        """
        Check if message should bypass AI processing
        Returns: (should_bypass, reason)
        """
        content_lower = content.lower().strip()
        
        # Explicit commands that should be handled directly
        direct_commands = [
            'paid', 'accept', 'reject', 'ready', 'status',
            'cancel', 'help', 'menu'
        ]
        
        # Check if it's a pure command (no extra text)
        if content_lower in direct_commands:
            return True, f"direct_command_{content_lower}"
        
        # Check if it's a numeric selection (restaurant/menu item)
        if content.strip().isdigit() and len(content.strip()) <= 2:
            return True, "numeric_selection"
        
        # Check if awaiting specific input (address, phone, etc.)
        if context.get('awaiting_address'):
            # Let AI validate if it looks like an address
            return False, None
        
        # Everything else goes through AI first
        return False, None
    
    def process_with_ai_first(self, content: str, whatsapp_message, context: Dict) -> Dict:
        """
        Main processing function - routes through AI first
        Returns: {
            'response': str,
            'handled_by': str,  # 'ai', 'direct_command', 'hybrid'
            'confidence': float,
            'metadata': dict
        }
        """
        try:
            # CRITICAL: Block AI processing if user hasn't completed signup
            conversation = context.get('conversation')
            if conversation and not context.get('user_exists') and conversation.onboarding_state != 'onboarded':
                logger.info("AI-first blocked: User must complete signup first")
                return {
                    'response': None,  # Let caller handle signup flow
                    'handled_by': 'signup_required',
                    'bypass_reason': 'needs_signup',
                    'confidence': 1.0,
                    'metadata': {'signup_required': True}
                }
            
            # Step 1: Check if should bypass AI
            should_bypass, bypass_reason = self.should_bypass_ai(content, context)
            
            if should_bypass:
                logger.info(f"Bypassing AI for direct command: {bypass_reason}")
                return {
                    'response': None,  # Let caller handle
                    'handled_by': 'direct_command',
                    'bypass_reason': bypass_reason,
                    'confidence': 1.0,
                    'metadata': {}
                }
            
            # Step 2: Preprocess message (spell correction, normalization)
            processed_content, preprocessing_meta = self.enhanced_ai.preprocess_message(content)
            
            # Step 2.5: Detect intentions (customer service, out-of-scope, etc.)
            intention_result = self.intention_detector.detect_intention(processed_content)
            logger.info(f"Intention detected: {intention_result}")
            
            # Handle out-of-scope messages
            if intention_result.get('is_out_of_scope'):
                polite_decline = self.intention_detector.get_polite_decline_message(processed_content)
                return {
                    'response': polite_decline,
                    'handled_by': 'intention_filter',
                    'confidence': intention_result.get('confidence', 0.9),
                    'metadata': {**preprocessing_meta, 'intention': intention_result}
                }
            
            # Step 2.6: Extract and track food preferences
            preferences = self.intention_detector.extract_preferences_from_message(processed_content)
            for item, preference_type in preferences:
                self.intention_detector.add_user_preference(item, preference_type)
                logger.info(f"Tracked preference: {item} - {preference_type}")
            
            # Step 3: Check for feedback commands
            feedback_response = self.enhanced_ai.handle_feedback_command(
                processed_content, 
                whatsapp_message.message_id
            )
            if feedback_response:
                return {
                    'response': feedback_response,
                    'handled_by': 'feedback_system',
                    'confidence': 1.0,
                    'metadata': preprocessing_meta
                }
            
            # Step 4: Get contextual information
            contextual_prompt = self.enhanced_ai.get_contextual_prompt(processed_content)
            
            # Step 5: Add preprocessing info to context
            if preprocessing_meta.get('was_spell_corrected'):
                context['spell_corrected'] = True
                context['original_message'] = preprocessing_meta['original_content']
            
            # Step 6: Process with base AI service
            # Update message content to corrected version
            original_content = whatsapp_message.content
            whatsapp_message.content = processed_content
            
            ai_result = self.base_ai.process_message(whatsapp_message, context)
            
            # Restore original content
            whatsapp_message.content = original_content
            
            # Step 7: Add message to memory
            self.enhanced_ai.memory.add_message(
                'user',
                processed_content,
                metadata={
                    'category': ai_result.get('category', 'unknown'),
                    'confidence': ai_result.get('confidence', 0.0),
                    'preprocessing': preprocessing_meta
                }
            )
            
            response_text = ai_result.get('response', '')
            
            self.enhanced_ai.memory.add_message(
                'assistant',
                response_text,
                metadata={'category': ai_result.get('category', 'unknown')}
            )
            
            # Step 8: Record for RLHF
            self.enhanced_ai.record_feedback_trigger(
                whatsapp_message.message_id,
                processed_content,
                response_text,
                ai_result.get('category', 'unknown'),
                ai_result.get('confidence', 0.0)
            )
            
            # Step 9: Log spell correction for debugging (don't send to user)
            if preprocessing_meta.get('was_spell_corrected'):
                corrections = preprocessing_meta.get('corrections', [])
                if corrections:
                    logger.info(f"Spell correction applied: '{content}' → '{processed_content}' (corrections: {corrections})")
                    # Note: Don't add correction note to user response - keep it internal
            
            return {
                'response': response_text,
                'handled_by': 'ai',
                'confidence': ai_result.get('confidence', 0.0),
                'metadata': {
                    **preprocessing_meta,
                    'category': ai_result.get('category', 'unknown'),
                    'contextual_prompt': contextual_prompt[:200]  # First 200 chars
                },
                'ai_result': ai_result  # Include full AI result
            }
            
        except Exception as e:
            logger.error(f"Error in AI-first processing: {str(e)}", exc_info=True)
            return {
                'response': None,
                'handled_by': 'error',
                'confidence': 0.0,
                'metadata': {'error': str(e)}
            }
    
    def check_order_for_conflicts(self, ordered_items: list) -> Optional[str]:
        """
        Check if user is ordering something they previously disliked
        Returns warning message if conflict found, None otherwise
        """
        try:
            has_conflict, conflicting_items, warning_msg = self.intention_detector.check_order_conflicts(ordered_items)
            
            if has_conflict:
                logger.warning(f"Order conflict detected: User ordering {conflicting_items} which they previously disliked")
                return warning_msg
            
            return None
        except Exception as e:
            logger.error(f"Error checking order conflicts: {str(e)}")
            return None
    
    def get_personalized_response(self, base_message: str, category: str = 'friendly') -> str:
        """
        Add personalization to AI responses
        """
        try:
            # Add emoji based on category
            personalized = self.response_generator.add_emoji(base_message, category)
            return personalized
        except Exception as e:
            logger.error(f"Error personalizing response: {str(e)}")
            return base_message
    
    def get_conversation_summary(self) -> Dict:
        """Get summary of conversation for debugging/analytics"""
        short_term = self.enhanced_ai.memory.get_short_term()
        long_term = self.enhanced_ai.memory.get_long_term()
        user_prefs = self.intention_detector.get_user_preferences()
        
        return {
            'conversation_id': self.conversation_id,
            'user_name': self.user_name,
            'message_count': len(short_term),
            'total_interactions': long_term.get('interaction_count', 0),
            'user_food_preferences': long_term.get('user_preferences', {}),
            'user_likes': user_prefs.get('likes', []),
            'user_dislikes': user_prefs.get('dislikes', []),
            'order_history_count': len(long_term.get('order_history', [])),
            'recent_messages': [
                {
                    'role': msg['role'],
                    'content': msg['content'][:50],
                    'timestamp': msg['timestamp']
                }
                for msg in short_term[-5:]
            ]
        }


def integrate_ai_first_processing(content: str, whatsapp_message, conversation, context: Dict) -> Optional[Dict]:
    """
    Helper function to integrate AI-first processing into existing flow
    Returns None if should continue with rule-based processing
    Returns dict with response if AI handled it
    """
    processor = AIFirstMessageProcessor(str(conversation.id))
    result = processor.process_with_ai_first(content, whatsapp_message, context)
    
    # If it's a direct command, let rule-based handlers take over
    if result['handled_by'] == 'direct_command':
        return None
    
    # If AI handled it successfully, return the response
    if result.get('response'):
        return result
    
    # Otherwise, continue with rule-based processing
    return None
