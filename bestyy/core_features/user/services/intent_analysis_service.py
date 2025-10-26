"""
Intent analysis service using OpenRouter LLM to understand vendor and courier messages
"""
import requests
import json
import logging
from typing import Dict, List, Optional
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from .ai_memory_service import AIMemoryService
from .context_window_manager import ContextWindowManager
from .user_type_identification_service import UserTypeIdentificationService

logger = logging.getLogger(__name__)


class IntentAnalysisService:
    """
    Service for analyzing vendor and courier message intents using OpenRouter LLM
    """
    
    def __init__(self):
        # OpenRouter LLM configuration
        self.openrouter_api_key = getattr(settings, 'OPENROUTER_API_KEY', None)
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
        self.app_url = getattr(settings, 'OPENROUTER_APP_URL', 'https://bestyy.com')
        self.app_name = getattr(settings, 'OPENROUTER_APP_NAME', 'Bestyy Intent Analyzer')
        self.memory_service = AIMemoryService()
        self.context_manager = ContextWindowManager()
        self.user_type_identifier = UserTypeIdentificationService()
        
        # Intent categories
        self.vendor_intents = [
            'ready', 'preparing', 'delay', 'problem', 'completed', 'cancelled',
            'ingredient_issue', 'equipment_issue', 'staff_issue', 'payment_issue'
        ]
        
        self.courier_intents = [
            'picked_up', 'on_the_way', 'arrived', 'delivered', 'delay', 'problem',
            'traffic_issue', 'vehicle_issue', 'address_issue', 'customer_issue'
        ]
    
    def analyze_vendor_intent(self, message: str, order_context: Dict = None) -> Dict:
        """
        Analyze vendor message intent
        
        Args:
            message: Vendor's message
            order_context: Order context information
            
        Returns:
            Dictionary with intent analysis
        """
        try:
            if not self.openrouter_api_key:
                return {'error': 'OpenRouter API key not configured'}
            
            # Build analysis prompt
            prompt = self._build_vendor_analysis_prompt(message, order_context)
            
            # Call LLM for analysis
            analysis = self._call_llm_for_intent_analysis(prompt, 'vendor')
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing vendor intent: {str(e)}")
            return {'error': str(e)}
    
    def analyze_courier_intent(self, message: str, order_context: Dict = None) -> Dict:
        """
        Analyze courier message intent
        
        Args:
            message: Courier's message
            order_context: Order context information
            
        Returns:
            Dictionary with intent analysis
        """
        try:
            if not self.openrouter_api_key:
                return {'error': 'OpenRouter API key not configured'}
            
            # Build analysis prompt
            prompt = self._build_courier_analysis_prompt(message, order_context)
            
            # Call LLM for analysis
            analysis = self._call_llm_for_intent_analysis(prompt, 'courier')
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing courier intent: {str(e)}")
            return {'error': str(e)}
    
    def _build_vendor_analysis_prompt(self, message: str, order_context: Dict = None) -> str:
        """
        Build prompt for vendor intent analysis
        """
        context_info = ""
        if order_context:
            context_info = f"""
ORDER CONTEXT:
- Order ID: {order_context.get('order_id', 'N/A')}
- Customer: {order_context.get('customer_name', 'N/A')}
- Order Time: {order_context.get('order_time', 'N/A')}
- Elapsed Time: {order_context.get('elapsed_time', 'N/A')} minutes
"""
        
        prompt = f"""
Analyze this vendor message for intent and urgency:

VENDOR MESSAGE: "{message}"
{context_info}

VENDOR INTENT CATEGORIES:
- ready: Order is ready for pickup
- preparing: Still preparing the order
- delay: Need more time (specify reason)
- problem: Having issues (specify problem)
- completed: Order preparation completed
- cancelled: Cannot fulfill the order
- ingredient_issue: Missing ingredients
- equipment_issue: Equipment problems
- staff_issue: Staff-related problems
- payment_issue: Payment problems

Respond with JSON:
{{
    "primary_intent": "intent_category",
    "confidence": 0.0-1.0,
    "urgency_level": "low|medium|high|critical",
    "extracted_info": {{
        "status": "preparing|ready|delay|problem",
        "estimated_time": "5-10 min|10-15 min|15-20 min|20+ min|unknown",
        "issues": ["list of specific issues"],
        "reason": "explanation of delay or problem"
    }},
    "action_required": "none|contact_customer|find_alternative|escalate",
    "customer_message": "message to send to customer",
    "internal_notes": "notes for internal use"
}}

Focus on:
1. Identifying the main intent
2. Detecting problems or delays
3. Estimating completion time
4. Determining urgency level
5. Providing clear customer communication
"""
        
        return prompt
    
    def _build_courier_analysis_prompt(self, message: str, order_context: Dict = None) -> str:
        """
        Build prompt for courier intent analysis
        """
        context_info = ""
        if order_context:
            context_info = f"""
ORDER CONTEXT:
- Order ID: {order_context.get('order_id', 'N/A')}
- Customer: {order_context.get('customer_name', 'N/A')}
- Pickup Location: {order_context.get('pickup_location', 'N/A')}
- Delivery Location: {order_context.get('delivery_location', 'N/A')}
- Elapsed Time: {order_context.get('elapsed_time', 'N/A')} minutes
"""
        
        prompt = f"""
Analyze this courier message for intent and urgency:

COURIER MESSAGE: "{message}"
{context_info}

COURIER INTENT CATEGORIES:
- picked_up: Order has been picked up from vendor
- on_the_way: Heading to customer location
- arrived: Arrived at customer location
- delivered: Successfully delivered to customer
- delay: Running late (specify reason)
- problem: Having issues (specify problem)
- traffic_issue: Traffic-related delays
- vehicle_issue: Vehicle problems
- address_issue: Cannot find delivery address
- customer_issue: Customer-related problems

Respond with JSON:
{{
    "primary_intent": "intent_category",
    "confidence": 0.0-1.0,
    "urgency_level": "low|medium|high|critical",
    "extracted_info": {{
        "status": "picked_up|on_the_way|arrived|delivered|delay|problem",
        "estimated_delivery": "5-10 min|10-15 min|15-20 min|20+ min|unknown",
        "issues": ["list of specific issues"],
        "reason": "explanation of delay or problem",
        "location": "current location if mentioned"
    }},
    "action_required": "none|contact_customer|find_alternative|escalate",
    "customer_message": "message to send to customer",
    "internal_notes": "notes for internal use"
}}

Focus on:
1. Identifying delivery progress
2. Detecting delays or problems
3. Estimating delivery time
4. Determining urgency level
5. Providing clear customer communication
"""
        
        return prompt
    
    def _call_llm_for_intent_analysis(self, prompt: str, user_type: str) -> Dict:
        """
        Call OpenRouter LLM for intent analysis
        """
        try:
            response = requests.post(
                url=f"{self.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self.app_url,
                    "X-Title": self.app_name,
                },
                data=json.dumps({
                    "model": "meta-llama/llama-3.2-3b-instruct:free",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"You are an expert intent analysis AI for a food delivery service. Analyze {user_type} messages to understand their intent, urgency, and required actions. Always respond with valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 400
                })
            )
            
            if response.status_code == 200:
                response_data = response.json()
                ai_response = response_data['choices'][0]['message']['content'].strip()
                
                try:
                    analysis = json.loads(ai_response)
                    
                    # Add metadata
                    analysis['analysis_timestamp'] = timezone.now().isoformat()
                    analysis['user_type'] = user_type
                    analysis['model_used'] = 'meta-llama/llama-3.2-3b-instruct:free'
                    
                    return analysis
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse LLM response as JSON: {e}")
                    return {
                        'error': 'Failed to parse LLM response',
                        'raw_response': ai_response,
                        'user_type': user_type
                    }
            else:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return {
                    'error': f'LLM API error: {response.status_code}',
                    'user_type': user_type
                }
                
        except Exception as e:
            logger.error(f"Error calling LLM for intent analysis: {str(e)}")
            # Fallback to keyword-based analysis
            return self._fallback_keyword_analysis(message, user_type)
    
    def analyze_customer_support_intent(self, message: str, customer_context: Dict = None) -> Dict:
        """
        Analyze customer support message intent
        
        Args:
            message: Customer's message
            customer_context: Customer context information
            
        Returns:
            Dictionary with intent analysis
        """
        try:
            if not self.openrouter_api_key:
                return {'error': 'OpenRouter API key not configured'}
            
            context_info = ""
            if customer_context:
                context_info = f"""
CUSTOMER CONTEXT:
- Customer ID: {customer_context.get('customer_id', 'N/A')}
- Order ID: {customer_context.get('order_id', 'N/A')}
- Order Status: {customer_context.get('order_status', 'N/A')}
- Order Time: {customer_context.get('order_time', 'N/A')}
- Elapsed Time: {customer_context.get('elapsed_time', 'N/A')} minutes
"""
            
            prompt = f"""
Analyze this customer support message for intent and urgency:

CUSTOMER MESSAGE: "{message}"
{context_info}

CUSTOMER INTENT CATEGORIES:
- order_status: Asking about order status
- delivery_time: Asking about delivery time
- complaint: Expressing dissatisfaction
- cancellation: Wanting to cancel order
- modification: Wanting to modify order
- payment_issue: Payment-related problems
- refund_request: Requesting refund
- general_inquiry: General questions
- emergency: Urgent situation

Respond with JSON:
{{
    "primary_intent": "intent_category",
    "confidence": 0.0-1.0,
    "urgency_level": "low|medium|high|critical",
    "sentiment": "positive|neutral|negative|angry",
    "extracted_info": {{
        "order_id": "extracted order ID if mentioned",
        "specific_issue": "specific problem or concern",
        "requested_action": "what customer wants",
        "emotion_level": "calm|concerned|frustrated|angry"
    }},
    "response_priority": "low|medium|high|urgent",
    "suggested_response": "suggested response to customer",
    "escalation_needed": true/false,
    "internal_notes": "notes for internal use"
}}

Focus on:
1. Identifying the main concern
2. Detecting urgency and emotion
3. Extracting specific information
4. Determining response priority
5. Suggesting appropriate response
"""
            
            # Call LLM for analysis
            response = requests.post(
                url=f"{self.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self.app_url,
                    "X-Title": self.app_name,
                },
                data=json.dumps({
                    "model": "meta-llama/llama-3.2-3b-instruct:free",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert customer support AI for a food delivery service. Analyze customer messages to understand their intent, urgency, and provide appropriate response suggestions. Always respond with valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 400
                })
            )
            
            if response.status_code == 200:
                response_data = response.json()
                ai_response = response_data['choices'][0]['message']['content'].strip()
                
                try:
                    analysis = json.loads(ai_response)
                    analysis['analysis_timestamp'] = timezone.now().isoformat()
                    analysis['user_type'] = 'customer'
                    analysis['model_used'] = 'meta-llama/llama-3.2-3b-instruct:free'
                    
                    return analysis
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse customer support LLM response: {e}")
                    return {
                        'error': 'Failed to parse LLM response',
                        'raw_response': ai_response,
                        'user_type': 'customer'
                    }
            else:
                return {
                    'error': f'LLM API error: {response.status_code}',
                    'user_type': 'customer'
                }
                
        except Exception as e:
            logger.error(f"Error analyzing customer support intent: {str(e)}")
            return {'error': str(e)}
    
    def get_intent_summary(self, analyses: List[Dict]) -> Dict:
        """
        Get summary of multiple intent analyses
        
        Args:
            analyses: List of intent analysis results
            
        Returns:
            Summary of all analyses
        """
        try:
            if not analyses:
                return {'error': 'No analyses provided'}
            
            # Count intents
            intent_counts = {}
            urgency_counts = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
            total_confidence = 0
            
            for analysis in analyses:
                if 'error' not in analysis:
                    intent = analysis.get('primary_intent', 'unknown')
                    intent_counts[intent] = intent_counts.get(intent, 0) + 1
                    
                    urgency = analysis.get('urgency_level', 'low')
                    urgency_counts[urgency] += 1
                    
                    confidence = analysis.get('confidence', 0)
                    total_confidence += confidence
            
            # Calculate averages
            avg_confidence = total_confidence / len(analyses) if analyses else 0
            
            # Determine overall urgency
            overall_urgency = 'low'
            if urgency_counts['critical'] > 0:
                overall_urgency = 'critical'
            elif urgency_counts['high'] > 0:
                overall_urgency = 'high'
            elif urgency_counts['medium'] > 0:
                overall_urgency = 'medium'
            
            return {
                'total_analyses': len(analyses),
                'intent_distribution': intent_counts,
                'urgency_distribution': urgency_counts,
                'overall_urgency': overall_urgency,
                'average_confidence': round(avg_confidence, 2),
                'summary_timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating intent summary: {str(e)}")
            return {'error': str(e)}
    
    def _fallback_keyword_analysis(self, message: str, user_type: str) -> Dict:
        """
        Fallback keyword-based intent analysis when LLM is unavailable
        
        Args:
            message: Message to analyze
            user_type: Type of user (vendor, courier, customer)
            
        Returns:
            Dictionary with keyword-based analysis
        """
        try:
            message_lower = message.lower().strip()
            
            if user_type == 'vendor':
                return self._analyze_vendor_keywords(message_lower)
            elif user_type == 'courier':
                return self._analyze_courier_keywords(message_lower)
            elif user_type == 'customer':
                return self._analyze_customer_keywords(message_lower)
            else:
                return {
                    'primary_intent': 'unknown',
                    'confidence': 0.3,
                    'urgency_level': 'low',
                    'extracted_info': {},
                    'action_required': 'none',
                    'fallback_used': True,
                    'user_type': user_type
                }
                
        except Exception as e:
            logger.error(f"Error in keyword fallback analysis: {str(e)}")
            return {
                'primary_intent': 'unknown',
                'confidence': 0.1,
                'urgency_level': 'low',
                'extracted_info': {},
                'action_required': 'none',
                'fallback_used': True,
                'error': str(e),
                'user_type': user_type
            }
    
    def _analyze_vendor_keywords(self, message: str) -> Dict:
        """
        Analyze vendor message using keyword matching
        """
        # Ready keywords
        ready_keywords = ['ready', 'done', 'finished', 'complete', 'prepared', 'pickup', 'collected']
        if any(keyword in message for keyword in ready_keywords):
            return {
                'primary_intent': 'ready',
                'confidence': 0.8,
                'urgency_level': 'low',
                'extracted_info': {
                    'status': 'ready',
                    'estimated_time': '5-10 min',
                    'issues': [],
                    'reason': 'Order preparation completed'
                },
                'action_required': 'none',
                'customer_message': 'Your order is ready for pickup!',
                'internal_notes': 'Order ready, courier can be notified',
                'fallback_used': True,
                'user_type': 'vendor'
            }
        
        # Preparing keywords
        preparing_keywords = ['preparing', 'cooking', 'making', 'working', 'almost', 'soon', 'few minutes']
        if any(keyword in message for keyword in preparing_keywords):
            return {
                'primary_intent': 'preparing',
                'confidence': 0.7,
                'urgency_level': 'low',
                'extracted_info': {
                    'status': 'preparing',
                    'estimated_time': '10-15 min',
                    'issues': [],
                    'reason': 'Order still being prepared'
                },
                'action_required': 'none',
                'customer_message': 'Your order is being prepared. We\'ll keep you updated.',
                'internal_notes': 'Order in preparation, continue monitoring',
                'fallback_used': True,
                'user_type': 'vendor'
            }
        
        # Delay keywords
        delay_keywords = ['delay', 'late', 'wait', 'more time', 'busy', 'rush', 'queue', 'backlog']
        if any(keyword in message for keyword in delay_keywords):
            return {
                'primary_intent': 'delay',
                'confidence': 0.8,
                'urgency_level': 'medium',
                'extracted_info': {
                    'status': 'delayed',
                    'estimated_time': '15-20 min',
                    'issues': ['preparation_delay'],
                    'reason': 'Preparation taking longer than expected'
                },
                'action_required': 'monitor',
                'customer_message': 'Your order is taking a bit longer to prepare. We\'re working to get it ready as soon as possible.',
                'internal_notes': 'Order delayed, monitor closely',
                'fallback_used': True,
                'user_type': 'vendor'
            }
        
        # Problem keywords
        problem_keywords = ['problem', 'issue', 'trouble', 'can\'t', 'unable', 'missing', 'out of', 'broken']
        if any(keyword in message for keyword in problem_keywords):
            return {
                'primary_intent': 'problem',
                'confidence': 0.8,
                'urgency_level': 'high',
                'extracted_info': {
                    'status': 'problem',
                    'estimated_time': '20+ min',
                    'issues': ['preparation_issue'],
                    'reason': 'Issue with order preparation'
                },
                'action_required': 'investigate',
                'customer_message': 'We\'re experiencing a minor issue with your order. Our team is working to resolve this quickly.',
                'internal_notes': 'Order has issues, investigate immediately',
                'fallback_used': True,
                'user_type': 'vendor'
            }
        
        # Default response
        return {
            'primary_intent': 'preparing',
            'confidence': 0.5,
            'urgency_level': 'low',
            'extracted_info': {
                'status': 'preparing',
                'estimated_time': '10-15 min',
                'issues': [],
                'reason': 'Order being prepared'
            },
            'action_required': 'none',
            'customer_message': 'Your order is being prepared. We\'ll keep you updated.',
            'internal_notes': 'Default vendor response, continue monitoring',
            'fallback_used': True,
            'user_type': 'vendor'
        }
    
    def _analyze_courier_keywords(self, message: str) -> Dict:
        """
        Analyze courier message using keyword matching
        """
        # Picked up keywords
        picked_up_keywords = ['picked up', 'collected', 'got the order', 'on my way', 'leaving now']
        if any(keyword in message for keyword in picked_up_keywords):
            return {
                'primary_intent': 'picked_up',
                'confidence': 0.8,
                'urgency_level': 'low',
                'extracted_info': {
                    'status': 'picked_up',
                    'estimated_delivery': '10-15 min',
                    'issues': [],
                    'reason': 'Order picked up from vendor'
                },
                'action_required': 'none',
                'customer_message': 'Your order has been picked up and is on its way to you!',
                'internal_notes': 'Order picked up, delivery in progress',
                'fallback_used': True,
                'user_type': 'courier'
            }
        
        # On the way keywords
        on_the_way_keywords = ['on the way', 'heading', 'driving', 'en route', 'coming', 'almost there']
        if any(keyword in message for keyword in on_the_way_keywords):
            return {
                'primary_intent': 'on_the_way',
                'confidence': 0.8,
                'urgency_level': 'low',
                'extracted_info': {
                    'status': 'on_the_way',
                    'estimated_delivery': '5-10 min',
                    'issues': [],
                    'reason': 'Courier en route to customer'
                },
                'action_required': 'none',
                'customer_message': 'Your order is on its way to you!',
                'internal_notes': 'Courier en route, delivery imminent',
                'fallback_used': True,
                'user_type': 'courier'
            }
        
        # Arrived keywords
        arrived_keywords = ['arrived', 'here', 'at location', 'reached', 'outside', 'door']
        if any(keyword in message for keyword in arrived_keywords):
            return {
                'primary_intent': 'arrived',
                'confidence': 0.8,
                'urgency_level': 'low',
                'extracted_info': {
                    'status': 'arrived',
                    'estimated_delivery': '1-2 min',
                    'issues': [],
                    'reason': 'Courier arrived at customer location'
                },
                'action_required': 'none',
                'customer_message': 'Our courier has arrived at your location!',
                'internal_notes': 'Courier arrived, delivery imminent',
                'fallback_used': True,
                'user_type': 'courier'
            }
        
        # Delivered keywords
        delivered_keywords = ['delivered', 'completed', 'done', 'finished', 'handed over']
        if any(keyword in message for keyword in delivered_keywords):
            return {
                'primary_intent': 'delivered',
                'confidence': 0.9,
                'urgency_level': 'low',
                'extracted_info': {
                    'status': 'delivered',
                    'estimated_delivery': 'completed',
                    'issues': [],
                    'reason': 'Order successfully delivered'
                },
                'action_required': 'complete',
                'customer_message': 'Your order has been successfully delivered!',
                'internal_notes': 'Order delivered successfully',
                'fallback_used': True,
                'user_type': 'courier'
            }
        
        # Delay keywords
        delay_keywords = ['delay', 'late', 'traffic', 'stuck', 'waiting', 'problem']
        if any(keyword in message for keyword in delay_keywords):
            return {
                'primary_intent': 'delay',
                'confidence': 0.8,
                'urgency_level': 'medium',
                'extracted_info': {
                    'status': 'delayed',
                    'estimated_delivery': '15-20 min',
                    'issues': ['delivery_delay'],
                    'reason': 'Delivery experiencing delay'
                },
                'action_required': 'monitor',
                'customer_message': 'Your delivery is experiencing a slight delay. We\'re working to get your order to you as soon as possible.',
                'internal_notes': 'Delivery delayed, monitor closely',
                'fallback_used': True,
                'user_type': 'courier'
            }
        
        # Default response
        return {
            'primary_intent': 'on_the_way',
            'confidence': 0.5,
            'urgency_level': 'low',
            'extracted_info': {
                'status': 'on_the_way',
                'estimated_delivery': '10-15 min',
                'issues': [],
                'reason': 'Courier en route'
            },
            'action_required': 'none',
            'customer_message': 'Your order is being delivered.',
            'internal_notes': 'Default courier response, continue monitoring',
            'fallback_used': True,
            'user_type': 'courier'
        }
    
    def _analyze_customer_keywords(self, message: str) -> Dict:
        """
        Analyze customer message using keyword matching
        """
        # Order status keywords
        status_keywords = ['where', 'status', 'update', 'progress', 'how long', 'when']
        if any(keyword in message for keyword in status_keywords):
            return {
                'primary_intent': 'order_status',
                'confidence': 0.8,
                'urgency_level': 'medium',
                'extracted_info': {
                    'specific_issue': 'order_status_inquiry',
                    'requested_action': 'status_update',
                    'emotion_level': 'concerned'
                },
                'response_priority': 'high',
                'suggested_response': 'Let me check the current status of your order and provide you with an update.',
                'escalation_needed': False,
                'internal_notes': 'Customer asking for order status',
                'fallback_used': True,
                'user_type': 'customer'
            }
        
        # Delivery time keywords
        time_keywords = ['how long', 'when', 'time', 'delivery', 'arrive', 'minutes', 'hours']
        if any(keyword in message for keyword in time_keywords):
            return {
                'primary_intent': 'delivery_time',
                'confidence': 0.8,
                'urgency_level': 'medium',
                'extracted_info': {
                    'specific_issue': 'delivery_time_inquiry',
                    'requested_action': 'time_estimate',
                    'emotion_level': 'concerned'
                },
                'response_priority': 'high',
                'suggested_response': 'Let me check the estimated delivery time for your order.',
                'escalation_needed': False,
                'internal_notes': 'Customer asking about delivery time',
                'fallback_used': True,
                'user_type': 'customer'
            }
        
        # Complaint keywords
        complaint_keywords = ['angry', 'frustrated', 'disappointed', 'terrible', 'awful', 'horrible', 'worst']
        if any(keyword in message for keyword in complaint_keywords):
            return {
                'primary_intent': 'complaint',
                'confidence': 0.9,
                'urgency_level': 'high',
                'extracted_info': {
                    'specific_issue': 'customer_complaint',
                    'requested_action': 'issue_resolution',
                    'emotion_level': 'angry'
                },
                'response_priority': 'urgent',
                'suggested_response': 'I sincerely apologize for the inconvenience. Let me help resolve this issue immediately.',
                'escalation_needed': True,
                'internal_notes': 'Customer complaint, escalate immediately',
                'fallback_used': True,
                'user_type': 'customer'
            }
        
        # Cancellation keywords
        cancel_keywords = ['cancel', 'refund', 'money back', 'don\'t want', 'stop']
        if any(keyword in message for keyword in cancel_keywords):
            return {
                'primary_intent': 'cancellation',
                'confidence': 0.8,
                'urgency_level': 'high',
                'extracted_info': {
                    'specific_issue': 'order_cancellation',
                    'requested_action': 'cancel_order',
                    'emotion_level': 'frustrated'
                },
                'response_priority': 'urgent',
                'suggested_response': 'I understand you want to cancel your order. Let me help you with that.',
                'escalation_needed': True,
                'internal_notes': 'Customer wants to cancel order',
                'fallback_used': True,
                'user_type': 'customer'
            }
        
        # Default response
        return {
            'primary_intent': 'general_inquiry',
            'confidence': 0.5,
            'urgency_level': 'low',
            'extracted_info': {
                'specific_issue': 'general_question',
                'requested_action': 'information',
                'emotion_level': 'neutral'
            },
            'response_priority': 'medium',
            'suggested_response': 'How can I help you today?',
            'escalation_needed': False,
            'internal_notes': 'General customer inquiry',
            'fallback_used': True,
            'user_type': 'customer'
        }
    
    def analyze_intent_with_memory(self, 
                                 message: str, 
                                 user_type: str, 
                                 user: User = None,
                                 session_id: str = None,
                                 conversation_id: str = None,
                                 context: Dict = None) -> Dict:
        """
        Analyze intent with memory and context awareness
        """
        try:
            # Get conversation context and relevant memories
            if user and session_id and conversation_id:
                conversation_context = self.context_manager.get_conversation_context(
                    user=user,
                    session_id=session_id,
                    conversation_id=conversation_id,
                    query=message
                )
                
                # Enhance context with memories
                enhanced_context = self._enhance_context_with_memories(
                    context or {},
                    conversation_context
                )
            else:
                enhanced_context = context or {}
            
            # Perform intent analysis with enhanced context
            if user_type == 'vendor':
                result = self.analyze_vendor_intent(message, enhanced_context)
            elif user_type == 'courier':
                result = self.analyze_courier_intent(message, enhanced_context)
            elif user_type == 'customer':
                result = self.analyze_customer_support_intent(message, enhanced_context)
            else:
                result = {'error': f'Unknown user type: {user_type}'}
            
            # Store analysis as episodic memory
            if user and 'error' not in result:
                self._store_intent_analysis_memory(
                    message=message,
                    user_type=user_type,
                    analysis_result=result,
                    user=user,
                    session_id=session_id,
                    conversation_id=conversation_id,
                    context=enhanced_context
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in memory-enhanced intent analysis: {str(e)}")
            # Fallback to regular analysis
            if user_type == 'vendor':
                return self.analyze_vendor_intent(message, context)
            elif user_type == 'courier':
                return self.analyze_courier_intent(message, context)
            elif user_type == 'customer':
                return self.analyze_customer_support_intent(message, context)
            else:
                return {'error': str(e)}
    
    def _enhance_context_with_memories(self, context: Dict, conversation_context: Dict) -> Dict:
        """
        Enhance context with relevant memories
        """
        try:
            enhanced_context = context.copy()
            
            # Add relevant memories
            if conversation_context.get('relevant_memories'):
                enhanced_context['relevant_memories'] = conversation_context['relevant_memories']
            
            # Add conversation history
            if conversation_context.get('current_context', {}).get('messages'):
                enhanced_context['conversation_history'] = conversation_context['current_context']['messages'][-3:]
            
            # Add memory summary
            if conversation_context.get('memory_summary'):
                enhanced_context['memory_summary'] = conversation_context['memory_summary']
            
            # Add conversation continuity
            if conversation_context.get('conversation_continuity'):
                enhanced_context['conversation_continuity'] = conversation_context['conversation_continuity']
            
            return enhanced_context
            
        except Exception as e:
            logger.error(f"Error enhancing context with memories: {str(e)}")
            return context
    
    def _store_intent_analysis_memory(self,
                                    message: str,
                                    user_type: str,
                                    analysis_result: Dict,
                                    user: User,
                                    session_id: str = None,
                                    conversation_id: str = None,
                                    context: Dict = None) -> str:
        """
        Store intent analysis as episodic memory
        """
        try:
            # Determine memory type based on user type
            memory_type_map = {
                'vendor': 'vendor_interaction',
                'courier': 'courier_interaction',
                'customer': 'support_interaction'
            }
            
            memory_type = memory_type_map.get(user_type, 'conversation')
            
            # Create memory content
            memory_content = {
                'original_message': message,
                'user_type': user_type,
                'intent_analysis': analysis_result,
                'context': context or {},
                'analysis_timestamp': timezone.now().isoformat(),
                'session_id': session_id,
                'conversation_id': conversation_id
            }
            
            # Store as episodic memory
            memory_id = self.memory_service.store_episodic_memory(
                memory_type=memory_type,
                title=f"{user_type.title()} Intent Analysis",
                description=f"Analyzed {user_type} message: {message[:50]}...",
                content=memory_content,
                user=user,
                session_id=session_id,
                conversation_id=conversation_id,
                importance_score=analysis_result.get('confidence', 0.5),
                emotional_tone=analysis_result.get('sentiment'),
                tags=['intent_analysis', user_type, analysis_result.get('primary_intent', 'unknown')]
            )
            
            return memory_id
            
        except Exception as e:
            logger.error(f"Error storing intent analysis memory: {str(e)}")
            return None
    
    def analyze_intent_with_auto_identification(self,
                                              message: str,
                                              user: User = None,
                                              phone_number: str = None,
                                              session_id: str = None,
                                              conversation_id: str = None) -> Dict:
        """
        Analyze intent with automatic user type identification
        """
        try:
            # Step 1: Identify user type
            identification_result = self.user_type_identifier.identify_user_type(
                user=user,
                phone_number=phone_number,
                message=message,
                session_id=session_id
            )
            
            # Step 2: Store identification result
            self.user_type_identifier.store_user_type_identification(
                identification_result=identification_result,
                phone_number=phone_number,
                message=message
            )
            
            # Step 3: Perform intent analysis with identified user type
            user_type = identification_result.get('user_type', 'unknown')
            
            if user_type == 'unknown':
                # Try to analyze as customer by default
                user_type = 'customer'
                identification_result['user_type'] = 'customer'
                identification_result['confidence'] = 0.3
                identification_result['identification_method'] = 'default_fallback'
            
            # Step 4: Perform memory-enhanced intent analysis
            intent_result = self.analyze_intent_with_memory(
                message=message,
                user_type=user_type,
                user=user,
                session_id=session_id,
                conversation_id=conversation_id
            )
            
            # Step 5: Combine results
            combined_result = {
                'intent_analysis': intent_result,
                'user_identification': identification_result,
                'analysis_timestamp': timezone.now().isoformat(),
                'session_id': session_id,
                'conversation_id': conversation_id
            }
            
            # Step 6: Store combined analysis as memory
            if user:
                self._store_combined_analysis_memory(
                    message=message,
                    combined_result=combined_result,
                    user=user,
                    session_id=session_id,
                    conversation_id=conversation_id
                )
            
            return combined_result
            
        except Exception as e:
            logger.error(f"Error in auto-identification intent analysis: {str(e)}")
            return {
                'intent_analysis': {'error': str(e)},
                'user_identification': {'user_type': 'unknown', 'confidence': 0.0, 'error': str(e)},
                'analysis_timestamp': timezone.now().isoformat()
            }
    
    def _store_combined_analysis_memory(self,
                                      message: str,
                                      combined_result: Dict,
                                      user: User,
                                      session_id: str = None,
                                      conversation_id: str = None) -> str:
        """
        Store combined analysis as episodic memory
        """
        try:
            user_type = combined_result['user_identification']['user_type']
            intent_analysis = combined_result['intent_analysis']
            
            # Determine memory type
            memory_type_map = {
                'vendor': 'vendor_interaction',
                'courier': 'courier_interaction',
                'customer': 'support_interaction'
            }
            
            memory_type = memory_type_map.get(user_type, 'conversation')
            
            # Create memory content
            memory_content = {
                'original_message': message,
                'user_type': user_type,
                'intent_analysis': intent_analysis,
                'user_identification': combined_result['user_identification'],
                'combined_analysis': combined_result,
                'analysis_timestamp': timezone.now().isoformat(),
                'session_id': session_id,
                'conversation_id': conversation_id
            }
            
            # Store as episodic memory
            memory_id = self.memory_service.store_episodic_memory(
                memory_type=memory_type,
                title=f"Auto-Identified {user_type.title()} Intent Analysis",
                description=f"Auto-identified {user_type} message: {message[:50]}...",
                content=memory_content,
                user=user,
                session_id=session_id,
                conversation_id=conversation_id,
                importance_score=intent_analysis.get('confidence', 0.5),
                emotional_tone=intent_analysis.get('sentiment'),
                tags=['auto_identification', 'intent_analysis', user_type, intent_analysis.get('primary_intent', 'unknown')]
            )
            
            return memory_id
            
        except Exception as e:
            logger.error(f"Error storing combined analysis memory: {str(e)}")
            return None
