"""
Enhanced AI Service with:
- Conversation Memory (short-term and long-term)
- Context Management
- RLHF (Reinforcement Learning from Human Feedback)
- Spell Correction and Fuzzy Matching
- AI-first message processing
"""
import logging
import re
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from django.core.cache import cache
from difflib import SequenceMatcher
from collections import deque

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Manages conversation memory with short-term and long-term storage"""
    
    def __init__(self, conversation_id: str, max_short_term: int = 10):
        self.conversation_id = conversation_id
        self.max_short_term = max_short_term
        self.cache_key_short = f"conv_memory_short_{conversation_id}"
        self.cache_key_long = f"conv_memory_long_{conversation_id}"
        self.cache_key_context = f"conv_context_{conversation_id}"
        
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """Add message to conversation memory"""
        message = {
            'role': role,  # 'user' or 'assistant'
            'content': content,
            'timestamp': timezone.now().isoformat(),
            'metadata': metadata or {}
        }
        
        # Short-term memory (last N messages)
        short_term = cache.get(self.cache_key_short, [])
        short_term.append(message)
        if len(short_term) > self.max_short_term:
            # Move oldest to long-term summary
            oldest = short_term.pop(0)
            self._add_to_long_term_summary(oldest)
        cache.set(self.cache_key_short, short_term, timeout=3600 * 24)  # 24 hours
        
    def _add_to_long_term_summary(self, message: Dict):
        """Summarize and store in long-term memory"""
        long_term = cache.get(self.cache_key_long, {
            'user_preferences': {},
            'order_history': [],
            'common_requests': {},
            'interaction_count': 0
        })
        
        long_term['interaction_count'] += 1
        
        # Extract patterns from message
        content_lower = message['content'].lower()
        
        # Track food preferences
        if 'food_order' in message.get('metadata', {}).get('category', ''):
            food_items = self._extract_food_items(content_lower)
            for item in food_items:
                if item not in long_term['user_preferences']:
                    long_term['user_preferences'][item] = 0
                long_term['user_preferences'][item] += 1
        
        # Track order completions
        if message.get('metadata', {}).get('order_completed'):
            long_term['order_history'].append({
                'timestamp': message['timestamp'],
                'order_id': message.get('metadata', {}).get('order_id')
            })
        
        cache.set(self.cache_key_long, long_term, timeout=3600 * 24 * 30)  # 30 days
    
    def _extract_food_items(self, content: str) -> List[str]:
        """Extract food items from message content"""
        from .nigerian_dishes_kb import NIGERIAN_DISHES
        found_items = []
        # NIGERIAN_DISHES is a dict with dish names as keys
        for dish_name in NIGERIAN_DISHES.keys():
            if dish_name.lower() in content:
                found_items.append(dish_name)
        return found_items
    
    def get_short_term(self) -> List[Dict]:
        """Get recent conversation history"""
        return cache.get(self.cache_key_short, [])
    
    def get_long_term(self) -> Dict:
        """Get long-term conversation summary"""
        return cache.get(self.cache_key_long, {
            'user_preferences': {},
            'order_history': [],
            'common_requests': {},
            'interaction_count': 0
        })
    
    def get_context(self) -> Dict:
        """Get current conversation context"""
        return cache.get(self.cache_key_context, {})
    
    def update_context(self, key: str, value):
        """Update conversation context"""
        context = self.get_context()
        context[key] = value
        cache.set(self.cache_key_context, context, timeout=3600 * 2)  # 2 hours
    
    def clear_context(self, key: str = None):
        """Clear specific context key or entire context"""
        if key:
            context = self.get_context()
            context.pop(key, None)
            cache.set(self.cache_key_context, context, timeout=3600 * 2)
        else:
            cache.delete(self.cache_key_context)


class SpellCorrector:
    """Corrects spelling and handles fuzzy matching for food items"""
    
    def __init__(self):
        from .nigerian_dishes_kb import NIGERIAN_DISHES
        # NIGERIAN_DISHES is a dict, keys are dish names
        self.food_dictionary = list(NIGERIAN_DISHES.keys())
        
        # Add aliases from each dish
        for dish_name, dish_data in NIGERIAN_DISHES.items():
            if isinstance(dish_data, dict) and 'aliases' in dish_data:
                self.food_dictionary.extend([alias.lower() for alias in dish_data['aliases']])
        
        # Add common foods and misspellings
        self.food_dictionary.extend([
            'pizza', 'burger', 'chicken', 'rice', 'pasta', 'salad',
            'jollof', 'jellof', 'jolof', 'egusi', 'egushi', 'eguisi',
            'suya', 'suuya', 'pounded yam', 'poundo yam'
        ])
        
        # Remove duplicates
        self.food_dictionary = list(set([item.lower() for item in self.food_dictionary]))
        
    def similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def correct_food_name(self, text: str, threshold: float = 0.75) -> str:
        """Correct misspelled food names using fuzzy matching"""
        words = text.lower().split()
        corrected_words = []
        
        for word in words:
            # Skip very short words
            if len(word) < 3:
                corrected_words.append(word)
                continue
            
            # Check if word is already correct
            if word in self.food_dictionary:
                corrected_words.append(word)
                continue
            
            # Find best match
            best_match = None
            best_score = 0
            
            for food_item in self.food_dictionary:
                # Check full match
                score = self.similarity(word, food_item)
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = food_item
                
                # Check if word is part of multi-word food
                if ' ' in food_item:
                    for food_word in food_item.split():
                        score = self.similarity(word, food_word)
                        if score > best_score and score >= threshold:
                            best_score = score
                            best_match = food_word
            
            if best_match:
                corrected_words.append(best_match)
                logger.info(f"Spell correction: '{word}' -> '{best_match}' (confidence: {best_score:.2f})")
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
    def correct_message(self, content: str) -> Tuple[str, bool]:
        """
        Correct entire message
        Returns: (corrected_content, was_corrected)
        """
        corrected = self.correct_food_name(content)
        was_corrected = corrected != content
        
        if was_corrected:
            logger.info(f"Message corrected: '{content}' -> '{corrected}'")
        
        return corrected, was_corrected


class RLHFFeedbackCollector:
    """Collects and stores feedback for RLHF"""
    
    def __init__(self):
        self.feedback_key_prefix = "rlhf_feedback"
    
    def record_interaction(self, conversation_id: str, message_id: str, 
                          user_message: str, ai_response: str, 
                          category: str, confidence: float):
        """Record AI interaction for potential feedback"""
        try:
            # Store in cache for quick access (no DB changes needed)
            cache_key = f"{self.feedback_key_prefix}_{message_id}"
            cache.set(cache_key, {
                'conversation_id': conversation_id,
                'message_id': message_id,
                'user_message': user_message,
                'ai_response': ai_response,
                'category': category,
                'confidence': confidence,
                'timestamp': timezone.now().isoformat()
            }, timeout=3600 * 24 * 7)  # 7 days
            
            logger.info(f"RLHF: Recorded interaction for message {message_id} (category: {category}, confidence: {confidence:.2f})")
            
        except Exception as e:
            logger.error(f"Error recording RLHF interaction: {str(e)}")
    
    def collect_feedback(self, message_id: str, feedback_type: str, 
                        feedback_score: Optional[float] = None, feedback_text: Optional[str] = None):
        """
        Collect user feedback on AI response
        feedback_type: 'positive', 'negative', 'correction'
        feedback_score: 1-5 rating
        feedback_text: Optional text feedback
        """
        try:
            cache_key = f"{self.feedback_key_prefix}_{message_id}"
            interaction_data = cache.get(cache_key)
            
            if not interaction_data:
                logger.warning(f"No interaction found for message {message_id}")
                return False
            
            # Store detailed feedback in cache
            feedback_data = {
                'type': feedback_type,
                'score': feedback_score,
                'text': feedback_text,
                'timestamp': timezone.now().isoformat()
            }
            
            # Update interaction data with feedback
            interaction_data['feedback'] = feedback_data
            cache.set(cache_key, interaction_data, timeout=3600 * 24 * 7)
            
            logger.info(f"RLHF Feedback received for message {message_id}: {feedback_data}")
            
            # Update category performance metrics
            category = interaction_data.get('category', 'unknown')
            self._update_category_performance(category, feedback_type, feedback_score)
            
            return True
            
        except Exception as e:
            logger.error(f"Error collecting RLHF feedback: {str(e)}")
            return False
    
    def _update_category_performance(self, category: str, feedback_type: str, score: Optional[float]):
        """Update performance metrics for category"""
        metrics_key = f"rlhf_metrics_{category}"
        metrics = cache.get(metrics_key, {
            'total_interactions': 0,
            'positive_feedback': 0,
            'negative_feedback': 0,
            'avg_score': 0.0,
            'total_score': 0.0
        })
        
        metrics['total_interactions'] += 1
        
        if feedback_type == 'positive':
            metrics['positive_feedback'] += 1
        elif feedback_type == 'negative':
            metrics['negative_feedback'] += 1
        
        if score:
            metrics['total_score'] += score
            metrics['avg_score'] = metrics['total_score'] / metrics['total_interactions']
        
        cache.set(metrics_key, metrics, timeout=3600 * 24 * 30)  # 30 days
        
        logger.info(f"Updated RLHF metrics for {category}: {metrics}")
    
    def get_category_performance(self, category: str) -> Dict:
        """Get performance metrics for a category"""
        metrics_key = f"rlhf_metrics_{category}"
        return cache.get(metrics_key, {
            'total_interactions': 0,
            'positive_feedback': 0,
            'negative_feedback': 0,
            'avg_score': 0.0
        })


class EnhancedAIService:
    """Enhanced AI service with memory, context, RLHF, and spell correction"""
    
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.memory = ConversationMemory(conversation_id)
        self.spell_corrector = SpellCorrector()
        self.rlhf = RLHFFeedbackCollector()
    
    def preprocess_message(self, content: str) -> Tuple[str, Dict]:
        """
        Preprocess message before AI processing
        Returns: (processed_content, preprocessing_metadata)
        """
        metadata = {
            'original_content': content,
            'was_spell_corrected': False,
            'corrections': []
        }
        
        # Apply spell correction
        corrected_content, was_corrected = self.spell_corrector.correct_message(content)
        
        if was_corrected:
            metadata['was_spell_corrected'] = True
            metadata['corrections'].append({
                'from': content,
                'to': corrected_content,
                'type': 'spell_correction'
            })
        
        # Normalize whitespace
        processed_content = ' '.join(corrected_content.split())
        
        logger.info(f"Preprocessed message: '{content}' -> '{processed_content}'")
        
        return processed_content, metadata
    
    def get_contextual_prompt(self, user_message: str) -> str:
        """Build contextual prompt with memory"""
        # Get conversation history
        short_term = self.memory.get_short_term()
        long_term = self.memory.get_long_term()
        
        # Build context
        context_parts = []
        
        # Add user preferences
        if long_term.get('user_preferences'):
            top_preferences = sorted(
                long_term['user_preferences'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
            if top_preferences:
                prefs_text = ', '.join([f"{item[0]} ({item[1]} times)" for item in top_preferences])
                context_parts.append(f"User's favorite foods: {prefs_text}")
        
        # Add recent conversation
        if short_term:
            recent_messages = short_term[-3:]  # Last 3 messages
            context_parts.append("\nRecent conversation:")
            for msg in recent_messages:
                context_parts.append(f"{msg['role']}: {msg['content'][:100]}")
        
        # Add current message
        context_parts.append(f"\nCurrent message: {user_message}")
        
        return '\n'.join(context_parts)
    
    def record_feedback_trigger(self, message_id: str, user_message: str, 
                               ai_response: str, category: str, confidence: float):
        """Record interaction for RLHF"""
        self.rlhf.record_interaction(
            self.conversation_id,
            message_id,
            user_message,
            ai_response,
            category,
            confidence
        )
    
    def handle_feedback_command(self, content: str, message_id: str) -> Optional[str]:
        """
        Handle feedback commands from users
        Examples: "👍", "👎", "that was helpful", "wrong answer"
        """
        content_lower = content.lower().strip()
        
        # Check for feedback indicators
        positive_indicators = ['👍', 'good', 'great', 'helpful', 'thanks', 'perfect', 'correct']
        negative_indicators = ['👎', 'bad', 'wrong', 'incorrect', 'not helpful', 'error']
        
        is_positive = any(ind in content_lower for ind in positive_indicators)
        is_negative = any(ind in content_lower for ind in negative_indicators)
        
        if is_positive:
            self.rlhf.collect_feedback(message_id, 'positive', feedback_score=5.0)
            return "Thank you for the positive feedback! 😊"
        elif is_negative:
            self.rlhf.collect_feedback(message_id, 'negative', feedback_score=1.0, feedback_text=content)
            return "Thank you for the feedback. We're constantly improving! 🙏"
        
        return None
