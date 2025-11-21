"""
Intention Detection Service for Bestyy WhatsApp AI
Handles:
- Customer service questions
- Bestyy-related scope filtering
- Personalized responses with names and emojis
- User preference tracking (likes/dislikes)
- Order conflict detection
"""
import logging
import re
from typing import Dict, List, Optional, Tuple
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class IntentionDetectionService:
    """Detects user intentions and determines if AI should respond"""
    
    # Bestyy-related topics (AI should respond to these)
    BESTYY_TOPICS = {
        'food_ordering': [
            'order', 'food', 'menu', 'dish', 'meal', 'eat', 'hungry',
            'jollof', 'rice', 'chicken', 'soup', 'stew', 'beans', 'yam',
            'plantain', 'fufu', 'egusi', 'okra', 'pepper soup'
        ],
        'delivery': [
            'delivery', 'deliver', 'courier', 'driver', 'location', 'address',
            'where', 'time', 'eta', 'arrive', 'track', 'status'
        ],
        'payment': [
            'pay', 'payment', 'paid', 'price', 'cost', 'how much', 'total',
            'bank', 'transfer', 'account', 'receipt', 'refund'
        ],
        'account': [
            'account', 'profile', 'login', 'register', 'signup', 'password',
            'email', 'phone', 'update', 'change'
        ],
        'customer_service': [
            'help', 'support', 'issue', 'problem', 'complaint', 'question',
            'how', 'what', 'when', 'why', 'can i', 'do you', 'is it possible'
        ],
        'restaurant': [
            'restaurant', 'vendor', 'shop', 'store', 'kitchen', 'chef',
            'available', 'open', 'closed', 'hours'
        ]
    }
    
    # Out-of-scope topics (AI should politely decline)
    OUT_OF_SCOPE_INDICATORS = [
        'weather', 'news', 'politics', 'sports', 'entertainment',
        'movie', 'music', 'game', 'joke', 'story', 'chat',
        'wikipedia', 'google', 'search', 'translate', 'calculate'
    ]
    
    # Customer service question patterns
    CS_PATTERNS = [
        r'\b(how|what|when|where|why|can|could|would|should|do|does|is|are)\b',
        r'\?$',  # Ends with question mark
        r'\b(help|support|assist|explain|tell me|show me)\b',
    ]
    
    def __init__(self, user_id: str = None, user_name: str = None):
        self.user_id = user_id
        self.user_name = user_name or "there"
        self.preference_cache_key = f"user_preferences_{user_id}" if user_id else None
        
    def detect_intention(self, message: str) -> Dict:
        """
        Detect user intention and determine if AI should respond
        
        Returns:
            {
                'should_respond': bool,
                'intention_type': str,
                'confidence': float,
                'is_question': bool,
                'is_out_of_scope': bool,
                'detected_topics': list,
                'response_tone': str
            }
        """
        message_lower = message.lower().strip()
        
        # Check if it's a question
        is_question = self._is_question(message_lower)
        
        # Detect topics
        detected_topics = self._detect_topics(message_lower)
        
        # Check if out of scope
        is_out_of_scope = self._is_out_of_scope(message_lower)
        
        # Determine if AI should respond
        should_respond = False
        intention_type = 'unknown'
        confidence = 0.0
        
        if is_out_of_scope:
            should_respond = True  # Respond with polite decline
            intention_type = 'out_of_scope'
            confidence = 0.9
        elif detected_topics:
            should_respond = True
            intention_type = detected_topics[0]  # Primary topic
            confidence = len(detected_topics) * 0.3  # More topics = higher confidence
            confidence = min(confidence, 0.95)
        elif is_question:
            # It's a question, let AI try to help
            should_respond = True
            intention_type = 'customer_service'
            confidence = 0.7
            
        # Determine response tone
        response_tone = self._determine_tone(message_lower, is_question)
        
        return {
            'should_respond': should_respond,
            'intention_type': intention_type,
            'confidence': confidence,
            'is_question': is_question,
            'is_out_of_scope': is_out_of_scope,
            'detected_topics': detected_topics,
            'response_tone': response_tone
        }
    
    def _is_question(self, message: str) -> bool:
        """Check if message is a question"""
        for pattern in self.CS_PATTERNS:
            if re.search(pattern, message):
                return True
        return False
    
    def _detect_topics(self, message: str) -> List[str]:
        """Detect Bestyy-related topics in message"""
        detected = []
        for topic, keywords in self.BESTYY_TOPICS.items():
            for keyword in keywords:
                if keyword in message:
                    if topic not in detected:
                        detected.append(topic)
                    break
        return detected
    
    def _is_out_of_scope(self, message: str) -> bool:
        """Check if message is about non-Bestyy topics"""
        for indicator in self.OUT_OF_SCOPE_INDICATORS:
            if indicator in message:
                return True
        return False
    
    def _determine_tone(self, message: str, is_question: bool) -> str:
        """Determine appropriate response tone"""
        # Check for frustration/complaints
        frustration_words = ['bad', 'terrible', 'awful', 'worst', 'angry', 'upset', 'disappointed']
        if any(word in message for word in frustration_words):
            return 'empathetic'
        
        # Check for gratitude
        gratitude_words = ['thank', 'thanks', 'appreciate', 'grateful']
        if any(word in message for word in gratitude_words):
            return 'warm'
        
        # Questions get helpful tone
        if is_question:
            return 'helpful'
        
        # Default to friendly
        return 'friendly'
    
    def get_polite_decline_message(self, message: str) -> str:
        """Generate polite decline for out-of-scope questions"""
        responses = [
            f"Hi {self.user_name}! 😊 I'm Bestyy's food ordering assistant. I'd love to help you with ordering delicious meals, checking delivery status, or answering questions about our service! However, I'm not able to help with that particular request. Is there anything food-related I can assist you with? 🍽️",
            
            f"Hello {self.user_name}! 👋 I specialize in helping with food orders and deliveries here at Bestyy. While I appreciate your message, that's outside my area of expertise. Can I help you order something tasty instead? 😋",
            
            f"Hey {self.user_name}! 🎉 I'm here to make your food ordering experience amazing! Unfortunately, I can't help with that particular topic, but I'm great at helping you find and order delicious meals. What can I get for you today? 🍕"
        ]
        
        # Rotate responses for variety
        import random
        return random.choice(responses)
    
    def add_user_preference(self, item: str, preference_type: str):
        """
        Track user food preferences
        
        Args:
            item: Food item name
            preference_type: 'like' or 'dislike'
        """
        if not self.preference_cache_key:
            return
            
        preferences = cache.get(self.preference_cache_key, {
            'likes': [],
            'dislikes': [],
            'last_updated': timezone.now().isoformat()
        })
        
        item_lower = item.lower()
        
        if preference_type == 'like':
            if item_lower not in preferences['likes']:
                preferences['likes'].append(item_lower)
            # Remove from dislikes if present
            if item_lower in preferences['dislikes']:
                preferences['dislikes'].remove(item_lower)
                
        elif preference_type == 'dislike':
            if item_lower not in preferences['dislikes']:
                preferences['dislikes'].append(item_lower)
            # Remove from likes if present
            if item_lower in preferences['likes']:
                preferences['likes'].remove(item_lower)
        
        preferences['last_updated'] = timezone.now().isoformat()
        cache.set(self.preference_cache_key, preferences, timeout=3600 * 24 * 90)  # 90 days
        
        logger.info(f"Added preference for user {self.user_id}: {item} - {preference_type}")
    
    def get_user_preferences(self) -> Dict:
        """Get user's food preferences"""
        if not self.preference_cache_key:
            return {'likes': [], 'dislikes': []}
            
        return cache.get(self.preference_cache_key, {
            'likes': [],
            'dislikes': [],
            'last_updated': None
        })
    
    def check_order_conflicts(self, ordered_items: List[str]) -> Tuple[bool, List[str], str]:
        """
        Check if user is ordering something they previously said they dislike
        
        Args:
            ordered_items: List of item names being ordered
            
        Returns:
            (has_conflict, conflicting_items, warning_message)
        """
        preferences = self.get_user_preferences()
        dislikes = preferences.get('dislikes', [])
        
        if not dislikes:
            return False, [], ""
        
        conflicting_items = []
        for item in ordered_items:
            item_lower = item.lower()
            for disliked in dislikes:
                # Check for partial matches
                if disliked in item_lower or item_lower in disliked:
                    conflicting_items.append(item)
                    break
        
        if conflicting_items:
            items_text = ", ".join(conflicting_items)
            warning_message = f"⚠️ Hey {self.user_name}, I noticed you're ordering *{items_text}*. "
            warning_message += f"You previously mentioned you don't like this. "
            warning_message += f"Would you like to choose something else? 🤔\n\n"
            warning_message += f"Reply *YES* to continue with this order, or *NO* to choose another dish."
            
            return True, conflicting_items, warning_message
        
        return False, [], ""
    
    def extract_preferences_from_message(self, message: str) -> List[Tuple[str, str]]:
        """
        Extract food preferences from user message
        
        Returns:
            List of (item, preference_type) tuples
        """
        message_lower = message.lower()
        preferences = []
        
        # Patterns for likes
        like_patterns = [
            r"i (love|like|enjoy|prefer|want)\s+([a-z\s]+)",
            r"(love|like|enjoy)\s+([a-z\s]+)",
            r"my favorite is\s+([a-z\s]+)",
        ]
        
        # Patterns for dislikes
        dislike_patterns = [
            r"i (hate|dislike|don't like|dont like)\s+([a-z\s]+)",
            r"(hate|dislike)\s+([a-z\s]+)",
            r"not a fan of\s+([a-z\s]+)",
            r"allergic to\s+([a-z\s]+)",
        ]
        
        # Check for likes
        for pattern in like_patterns:
            matches = re.finditer(pattern, message_lower)
            for match in matches:
                # Get the last captured group (the food item)
                groups = match.groups()
                if groups:
                    item = groups[-1].strip()
                    if len(item) > 2:  # Avoid single letters
                        preferences.append((item, 'like'))
        
        # Check for dislikes
        for pattern in dislike_patterns:
            matches = re.finditer(pattern, message_lower)
            for match in matches:
                # Get the last captured group (the food item)
                groups = match.groups()
                if groups:
                    item = groups[-1].strip()
                    if len(item) > 2:
                        preferences.append((item, 'dislike'))
        
        return preferences


class PersonalizedResponseGenerator:
    """Generates personalized, polite responses with proper emojis"""
    
    EMOJI_MAP = {
        'greeting': ['👋', '😊', '🎉', '✨'],
        'food': ['🍽️', '😋', '🍕', '🍜', '🍛', '🥘'],
        'delivery': ['🚗', '📦', '🛵', '🏃‍♂️'],
        'payment': ['💳', '💰', '💵', '✅'],
        'success': ['✅', '🎉', '👍', '🌟'],
        'warning': ['⚠️', '🤔', '❗'],
        'error': ['❌', '😕', '🙏'],
        'thinking': ['🤔', '💭', '🧐'],
        'help': ['🆘', '💁‍♀️', '🤝', '💡'],
    }
    
    def __init__(self, user_name: str = "there", tone: str = "friendly"):
        self.user_name = user_name
        self.tone = tone
    
    def generate_greeting(self) -> str:
        """Generate personalized greeting"""
        greetings = [
            f"Hi {self.user_name}! 👋 How can I help you today?",
            f"Hello {self.user_name}! 😊 What would you like to order?",
            f"Hey {self.user_name}! 🎉 Ready to order something delicious?",
            f"Welcome back {self.user_name}! ✨ What can I get for you?",
        ]
        import random
        return random.choice(greetings)
    
    def generate_order_confirmation(self, items: List[str]) -> str:
        """Generate personalized order confirmation"""
        items_text = ", ".join(items)
        responses = [
            f"Great choice {self.user_name}! 😋 You've ordered: *{items_text}*. Anything else?",
            f"Excellent! 🎉 I've added *{items_text}* to your order. Would you like something else?",
            f"Perfect {self.user_name}! 👍 *{items_text}* has been added. Anything more?",
        ]
        import random
        return random.choice(responses)
    
    def generate_preference_acknowledgment(self, item: str, preference_type: str) -> str:
        """Acknowledge user preference"""
        if preference_type == 'like':
            responses = [
                f"Noted! 📝 I'll remember that you love *{item}*! ❤️",
                f"Got it {self.user_name}! 😊 I know *{item}* is your favorite!",
                f"Great to know! 🌟 I'll suggest *{item}* more often!",
            ]
        else:  # dislike
            responses = [
                f"Noted! 📝 I'll remember you don't like *{item}* and won't suggest it.",
                f"Got it {self.user_name}! 👍 I'll avoid recommending *{item}*.",
                f"Understood! 🙏 I'll keep *{item}* off your suggestions.",
            ]
        import random
        return random.choice(responses)
    
    def generate_empathetic_response(self, issue: str) -> str:
        """Generate empathetic response for complaints"""
        responses = [
            f"I'm really sorry to hear that {self.user_name}! 😔 Let me help resolve this for you right away.",
            f"I understand your frustration {self.user_name}. 🙏 I'll do my best to fix this!",
            f"My apologies {self.user_name}! 😕 Let's sort this out together.",
        ]
        import random
        return random.choice(responses)
    
    def add_emoji(self, message: str, category: str) -> str:
        """Add appropriate emoji to message"""
        if category in self.EMOJI_MAP:
            import random
            emoji = random.choice(self.EMOJI_MAP[category])
            if emoji not in message:
                message += f" {emoji}"
        return message
