import requests
import json
import time
import logging
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from .models import WhatsAppMessage, AIResponseTemplate, AIProcessingLog

logger = logging.getLogger(__name__)


class WhatsAppAIService:
    """Service class for processing WhatsApp messages with AI using OpenRouter"""
    
    def __init__(self):
        # OpenRouter configuration
        self.openrouter_api_key = getattr(settings, 'OPENROUTER_API_KEY', None)
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
        self.app_url = getattr(settings, 'OPENROUTER_APP_URL', 'https://your-app.com')
        self.app_name = getattr(settings, 'OPENROUTER_APP_NAME', 'WhatsApp AI Bot')
        
        if not self.openrouter_api_key:
            logger.warning("OpenRouter API key not configured")
    
    def process_message(self, message: WhatsAppMessage, context: Dict = None) -> Dict:
        """
        Process a WhatsApp message and generate AI response
        
        Args:
            message: WhatsAppMessage instance
            context: Additional context for AI processing
            
        Returns:
            Dict containing AI response and metadata
        """
        start_time = time.time()
        
        try:
            # Determine message category
            category = self._categorize_message(message.content)
            
            # Get appropriate template
            template = self._get_template(category, message.conversation.language)
            
            # Generate AI response
            ai_response = self._generate_response(message, template, context)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log the processing
            self._log_processing(message, template, 'success', processing_time, ai_response)
            
            # Update message with AI response
            message.ai_response = ai_response['response']
            message.ai_confidence = ai_response.get('confidence', 0.0)
            message.is_ai_processed = True
            message.save()
            
            return {
                'success': True,
                'response': ai_response['response'],
                'category': category,
                'confidence': ai_response.get('confidence', 0.0),
                'processing_time': processing_time
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            
            # Log the error
            self._log_processing(message, None, 'error', processing_time, None, error_msg)
            
            logger.error(f"AI processing failed for message {message.id}: {error_msg}")
            
            return {
                'success': False,
                'error': error_msg,
                'processing_time': processing_time
            }
    
    def _categorize_message(self, content: str) -> str:
        """
        Categorize the message content to determine response type
        
        Args:
            content: Message content
            
        Returns:
            Category string
        """
        content_lower = content.lower()
        
        # Greeting patterns
        greeting_keywords = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        if any(keyword in content_lower for keyword in greeting_keywords):
            return 'greeting'
        
        # Order inquiry patterns
        order_keywords = ['order', 'buy', 'purchase', 'want', 'need', 'get', 'delivery']
        if any(keyword in content_lower for keyword in order_keywords):
            return 'order_inquiry'
        
        # Menu request patterns
        menu_keywords = ['menu', 'food', 'dish', 'item', 'available', 'what do you have']
        if any(keyword in content_lower for keyword in menu_keywords):
            return 'menu_request'
        
        # Delivery status patterns
        delivery_keywords = ['delivery', 'status', 'where', 'track', 'arrive', 'coming']
        if any(keyword in content_lower for keyword in delivery_keywords):
            return 'delivery_status'
        
        # Payment help patterns
        payment_keywords = ['payment', 'pay', 'money', 'cost', 'price', 'bill', 'charge']
        if any(keyword in content_lower for keyword in payment_keywords):
            return 'payment_help'
        
        # Complaint patterns
        complaint_keywords = ['problem', 'issue', 'wrong', 'bad', 'complaint', 'angry', 'disappointed']
        if any(keyword in content_lower for keyword in complaint_keywords):
            return 'complaint'
        
        # Default to general info
        return 'general_info'
    
    def _get_template(self, category: str, language: str = 'en') -> Optional[AIResponseTemplate]:
        """
        Get the appropriate AI response template
        
        Args:
            category: Message category
            language: Language code
            
        Returns:
            AIResponseTemplate instance or None
        """
        try:
            template = AIResponseTemplate.objects.get(
                category=category,
                language=language,
                is_active=True
            )
            return template
        except AIResponseTemplate.DoesNotExist:
            # Fallback to English or default template
            try:
                template = AIResponseTemplate.objects.get(
                    category='fallback',
                    language='en',
                    is_active=True
                )
                return template
            except AIResponseTemplate.DoesNotExist:
                return None
    
    def _generate_response(self, message: WhatsAppMessage, template: AIResponseTemplate, context: Dict = None) -> Dict:
        """
        Generate AI response using OpenRouter API
        
        Args:
            message: WhatsAppMessage instance
            template: AIResponseTemplate instance
            context: Additional context
            
        Returns:
            Dict containing response and metadata
        """
        if not self.openrouter_api_key:
            raise Exception("OpenRouter API key not configured")
        
        # Prepare the prompt
        prompt = self._build_prompt(message, template, context)
        
        try:
            # Make request to OpenRouter API
            response = requests.post(
                url=f"{self.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self.app_url,
                    "X-Title": self.app_name,
                },
                data=json.dumps({
                    "model": template.ai_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a helpful AI assistant for a food delivery service. Respond in a friendly, professional manner."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": template.temperature,
                    "max_tokens": template.max_tokens
                })
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")
            
            response_data = response.json()
            ai_response = response_data['choices'][0]['message']['content'].strip()
            
            # Calculate confidence based on response quality
            confidence = self._calculate_confidence(ai_response, message.content)
            
            # Update template usage
            template.usage_count += 1
            template.save()
            
            # Extract usage information
            usage = response_data.get('usage', {})
            
            return {
                'response': ai_response,
                'confidence': confidence,
                'tokens_used': usage.get('total_tokens', 0),
                'prompt_tokens': usage.get('prompt_tokens', 0),
                'completion_tokens': usage.get('completion_tokens', 0),
                'model': template.ai_model
            }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenRouter API request error: {str(e)}")
        except Exception as e:
            raise Exception(f"OpenRouter API error: {str(e)}")
    
    def _build_prompt(self, message: WhatsAppMessage, template: AIResponseTemplate, context: Dict = None) -> str:
        """
        Build the prompt for AI processing
        
        Args:
            message: WhatsAppMessage instance
            template: AIResponseTemplate instance
            context: Additional context
            
        Returns:
            Formatted prompt string
        """
        # Base prompt with template
        prompt = template.template_text
        
        # Replace variables in template
        variables = {
            'user_message': message.content,
            'phone_number': message.conversation.phone_number,
            'language': message.conversation.language,
            'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # Add context variables
        if context:
            variables.update(context)
        
        # Replace placeholders
        for var_name, var_value in variables.items():
            placeholder = f"{{{var_name}}}"
            prompt = prompt.replace(placeholder, str(var_value))
        
        return prompt
    
    def _calculate_confidence(self, ai_response: str, user_message: str) -> float:
        """
        Calculate confidence score for AI response
        
        Args:
            ai_response: Generated AI response
            user_message: Original user message
            
        Returns:
            Confidence score between 0 and 1
        """
        # Simple confidence calculation based on response length and content
        confidence = 0.5  # Base confidence
        
        # Increase confidence for longer, more detailed responses
        if len(ai_response) > 50:
            confidence += 0.2
        
        # Increase confidence for responses that address the user's message
        if any(word in ai_response.lower() for word in user_message.lower().split()[:3]):
            confidence += 0.2
        
        # Decrease confidence for generic responses
        generic_responses = ['i understand', 'thank you', 'okay', 'sure']
        if any(phrase in ai_response.lower() for phrase in generic_responses):
            confidence -= 0.1
        
        return min(1.0, max(0.0, confidence))
    
    def _log_processing(self, message: WhatsAppMessage, template: AIResponseTemplate, 
                       status: str, processing_time: float, ai_response: Dict = None, 
                       error_message: str = None) -> None:
        """
        Log AI processing activity
        
        Args:
            message: WhatsAppMessage instance
            template: AIResponseTemplate instance
            status: Processing status
            processing_time: Processing time in seconds
            ai_response: AI response data
            error_message: Error message if any
        """
        log_data = {
            'message': message,
            'template': template,
            'status': status,
            'processing_time': processing_time,
            'ai_model_used': template.ai_model if template else 'unknown',
        }
        
        if ai_response:
            log_data.update({
                'tokens_used': ai_response.get('tokens_used'),
                'prompt_tokens': ai_response.get('prompt_tokens'),
                'completion_tokens': ai_response.get('completion_tokens'),
            })
        
        if error_message:
            log_data['error_message'] = error_message
        
        AIProcessingLog.objects.create(**log_data)
    
    def get_conversation_context(self, conversation_id: str) -> Dict:
        """
        Get conversation context for better AI responses
        
        Args:
            conversation_id: Conversation UUID
            
        Returns:
            Context dictionary
        """
        try:
            from .models import WhatsAppConversation
            conversation = WhatsAppConversation.objects.get(id=conversation_id)
            
            # Get recent messages for context
            recent_messages = conversation.messages.filter(
                direction='inbound'
            ).order_by('-timestamp')[:5]
            
            context = {
                'conversation_id': str(conversation.id),
                'phone_number': conversation.phone_number,
                'language': conversation.language,
                'recent_messages': [
                    {
                        'content': msg.content,
                        'timestamp': msg.timestamp.isoformat(),
                        'category': self._categorize_message(msg.content)
                    }
                    for msg in recent_messages
                ]
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {str(e)}")
            return {}
    
    def get_available_models(self) -> List[Dict]:
        """
        Get list of available models from OpenRouter
        
        Returns:
            List of available models with their details
        """
        if not self.openrouter_api_key:
            return []
        
        try:
            response = requests.get(
                f"{self.openrouter_base_url}/models",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "HTTP-Referer": self.app_url,
                    "X-Title": self.app_name,
                }
            )
            
            if response.status_code == 200:
                models_data = response.json()
                return models_data.get('data', [])
            else:
                logger.error(f"Failed to fetch models: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching available models: {str(e)}")
            return []
    
    def get_recommended_models(self) -> List[str]:
        """
        Get list of recommended models for WhatsApp AI responses
        
        Returns:
            List of recommended model names
        """
        return [
            "meta-llama/llama-3.3-8b-instruct:free",  # Free model
            "openai/gpt-3.5-turbo",
            "openai/gpt-4",
            "openai/gpt-4-turbo",
            "anthropic/claude-3-haiku",
            "anthropic/claude-3-sonnet",
            "google/gemini-pro",
            "meta-llama/llama-2-70b-chat",
            "mistralai/mistral-7b-instruct",
        ]
    
    def send_whatsapp_message(self, phone_number: str, message: str, message_type: str = 'text') -> Dict:
        """
        Send WhatsApp message (placeholder for WhatsApp Business API integration)
        
        Args:
            phone_number: Recipient phone number
            message: Message content
            message_type: Type of message
            
        Returns:
            Dict with send status
        """
        # This is a placeholder for WhatsApp Business API integration
        # In a real implementation, you would integrate with WhatsApp Business API
        
        logger.info(f"Sending WhatsApp message to {phone_number}: {message}")
        
        # For now, return success status
        return {
            'success': True,
            'message_id': f"msg_{int(time.time())}",
            'status': 'sent',
            'timestamp': timezone.now().isoformat()
        }
