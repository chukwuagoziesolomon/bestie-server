#!/usr/bin/env python3
"""
AI-powered message categorization system for WhatsApp messages
Uses OpenRouter API to classify user intents intelligently
"""
import requests
import json
import logging
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

class WhatsAppMessageCategorizer:
    """
    AI-powered message categorization system that classifies user intents
    more intelligently than rule-based keyword matching
    """
    
    def __init__(self):
        self.openrouter_api_key = getattr(settings, 'OPENROUTER_API_KEY', None)
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Define message categories with clear descriptions
        self.categories = {
            "greeting": "User is saying hello, hi, good morning, etc. - wants to start conversation",
            "food_order": "User wants to order food, add items to cart, or place an order",
            "menu_inquiry": "User asking about menu, food options, what's available",
            "food_search": "User looking for specific food types (pizza, burger, etc.) or cuisines",
            "account_help": "User needs help with account, login, password, or profile",
            "delivery_inquiry": "User asking about delivery, location, time, or fees", 
            "payment_help": "User has payment issues, wants to pay, or asking about costs",
            "complaint": "User has a problem, complaint, or negative feedback",
            "order_tracking_complaint": "User complaining about missing, late, or undelivered order",
            "general_question": "User asking general questions about the service",
            "unclear": "Message is unclear, ambiguous, or doesn't fit other categories"
        }
    
    def categorize_message(self, message: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Categorize a user message using AI
        
        Args:
            message: The user's message text
            user_context: Optional context about user (name, onboarding state, etc.)
            
        Returns:
            Dict with category, confidence, and reasoning
        """
        if not self.openrouter_api_key:
            logger.warning("No OpenRouter API key configured, falling back to rule-based")
            return self._fallback_categorization(message)
        
        try:
            # Build context-aware prompt
            context_info = ""
            if user_context:
                if user_context.get('onboarding_state') != 'onboarded':
                    context_info += "User is not fully onboarded yet. "
                if user_context.get('first_name'):
                    context_info += f"User's name is {user_context['first_name']}. "
            
            # Create categorization prompt
            prompt = f"""You are an expert at categorizing customer messages for a food delivery app called Bestyy.

{context_info}

Categories available:
{json.dumps(self.categories, indent=2)}

User message: "{message}"

Classify this message into ONE of the above categories. Consider:
1. Primary intent of the message
2. Context clues and user state
3. Common patterns in food delivery conversations

Respond with valid JSON only:
{{
    "category": "category_name",
    "confidence": 0.95,
    "reasoning": "Brief explanation of why this category was chosen"
}}"""

            # Make API call
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 200
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
                
                # Parse JSON response
                try:
                    categorization = json.loads(ai_response)
                    
                    # Validate response format
                    if all(key in categorization for key in ['category', 'confidence', 'reasoning']):
                        # Ensure category exists in our defined categories
                        if categorization['category'] in self.categories:
                            logger.info(f"AI categorized '{message}' as '{categorization['category']}' with confidence {categorization['confidence']}")
                            return categorization
                        else:
                            logger.warning(f"AI returned unknown category: {categorization['category']}")
                    
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse AI response as JSON: {ai_response}")
            
            else:
                logger.error(f"OpenRouter API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error in AI categorization: {str(e)}")
        
        # Fallback to rule-based if AI fails
        return self._fallback_categorization(message)
    
    def _fallback_categorization(self, message: str) -> Dict[str, Any]:
        """
        Fallback rule-based categorization when AI is unavailable
        """
        content = message.lower().strip()
        
        # Greeting patterns - check these first!
        greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings']
        if any(word in content for word in greeting_words) and len(content) < 20:
            return {
                "category": "greeting",
                "confidence": 0.9,
                "reasoning": "Contains greeting words and is short message"
            }
        
        # Food search patterns
        food_keywords = ['pizza', 'burger', 'chicken', 'rice', 'pasta', 'soup', 'salad', 'sandwich', 'noodles', 'sushi', 'steak', 'fish', 'beef', 'pork', 'vegetarian', 'vegan']
        if any(food in content for food in food_keywords):
            return {
                "category": "food_search", 
                "confidence": 0.8,
                "reasoning": "Contains specific food type keywords"
            }
        
        # Order intent
        order_patterns = ['order', 'buy', 'purchase', 'add to cart', 'i want', 'get me']
        if any(pattern in content for pattern in order_patterns):
            return {
                "category": "food_order",
                "confidence": 0.7,
                "reasoning": "Contains order-related keywords"
            }
        
        # Menu inquiry
        menu_patterns = ['menu', 'what do you have', 'what food', 'available', 'options']
        if any(pattern in content for pattern in menu_patterns):
            return {
                "category": "menu_inquiry",
                "confidence": 0.7,
                "reasoning": "Asking about menu or food options"
            }
        
        # Enhanced complaint detection with subcategories
        complaint_patterns = ['problem', 'issue', 'wrong', 'bad', 'terrible', 'complaint', 'disappointed', 'upset', 'angry', 'stupid', 'useless', 'hate', 'sucks', 'awful']
        order_tracking_patterns = ['haven\'t received', 'not delivered', 'where is', 'tracking', 'late', 'delayed', 'hours', 'waiting', 'haven\'t seen']
        
        if any(pattern in content for pattern in complaint_patterns):
            # Check if it's specifically an order tracking complaint
            if any(pattern in content for pattern in order_tracking_patterns) and 'order' in content:
                return {
                    "category": "order_tracking_complaint", 
                    "confidence": 0.95,
                    "reasoning": "Complaint about order delivery/tracking"
                }
            return {
                "category": "complaint",
                "confidence": 0.9,
                "reasoning": "Contains complaint indicators"
            }
        
        # Default to unclear
        return {
            "category": "unclear",
            "confidence": 0.5,
            "reasoning": "Could not clearly categorize with available patterns"
        }
    
    def get_response_for_category(self, category: str, user_context: Dict[str, Any] = None, message: str = None) -> str:
        """
        Generate appropriate response based on message category
        """
        user_name = user_context.get('first_name', 'there') if user_context else 'there'
        
        # Import greeting service for personalized responses
        from bestyy.communication.whatsapp.greeting_service import WhatsAppGreetingService
        greeting_service = WhatsAppGreetingService()
        
        if category == "greeting":
            is_returning = user_context.get('onboarding_state') == 'onboarded' if user_context else False
            greeting = greeting_service.get_personalized_greeting(user_name, is_returning)
            return f"{greeting}\n\nHow can I assist you with your food order today?"
            
        elif category == "food_order":
            return "I'd be happy to help you place an order! What delicious food are you craving today?"
            
        elif category == "menu_inquiry":
            return "I can help you explore our amazing menu! We have a variety of delicious options. What type of cuisine interests you?"
            
        elif category == "food_search":
            return "Great choice! Let me help you find the perfect restaurant for that craving. What specific dish are you looking for?"
            
        elif category == "account_help":
            return "I'm here to help with your account! What do you need assistance with?"
            
        elif category == "delivery_inquiry":
            return "I can help you with delivery information! What would you like to know about delivery to your area?"
            
        elif category == "payment_help":
            return "I can assist you with payment questions! What payment issue can I help resolve?"
            
        elif category == "complaint":
            # Use intelligent complaint handler
            from .complaint_handler import WhatsAppComplaintHandler
            complaint_handler = WhatsAppComplaintHandler()
            complaint_response = complaint_handler.handle_complaint(message or "", user_context)
            return complaint_response['response']
            
        elif category == "order_tracking_complaint":
            # Use specific complaint handler for order tracking
            from .complaint_handler import WhatsAppComplaintHandler
            complaint_handler = WhatsAppComplaintHandler()
            complaint_response = complaint_handler.handle_complaint(message or "", user_context)
            return complaint_response['response']
            
        elif category == "general_question":
            return "I'm happy to answer your questions about Bestyy! What would you like to know?"
            
        else:  # unclear or unknown
            return "I want to make sure I understand you correctly! Could you tell me a bit more about what you're looking for?"