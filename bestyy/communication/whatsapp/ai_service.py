import requests
import json
import time
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from .models import WhatsAppMessage, AIResponseTemplate, AIProcessingLog
from .whatsapp_order_service import WhatsAppOrderService
from .nigerian_dishes_kb import (
    find_nigerian_dish, is_nigerian_dish, get_dish_info,
    NIGERIAN_DISHES_SYSTEM_PROMPT
)
from .utils import looks_like_address
import re

logger = logging.getLogger(__name__)


class WhatsAppAIService:
    """Service class for processing WhatsApp messages with AI using OpenRouter"""

    def __init__(self):
        # OpenRouter configuration
        self.openrouter_api_key = getattr(settings, 'OPENROUTER_API_KEY', None)
        self.openrouter_base_url = "https://openrouter.ai/api/v1"
        self.app_url = getattr(settings, 'OPENROUTER_APP_URL', 'https://your-app.com')
        self.app_name = getattr(settings, 'OPENROUTER_APP_NAME', 'WhatsApp AI Bot')
        self.order_service = WhatsAppOrderService()

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

            # Check if user needs onboarding (only for new users who haven't completed onboarding)
            user_exists = context.get('user_exists', False) if context else False
            user_needs_onboarding = False

            if user_exists and message.conversation.user:
                try:
                    from bestyy.core_features.user.models import UserProfile
                    profile, created = UserProfile.objects.get_or_create(user=message.conversation.user)
                    user_needs_onboarding = not profile.onboarding_completed
                except Exception as e:
                    logger.warning(f"Error checking user profile: {str(e)}")
                    # Profile doesn't exist yet
                    user_needs_onboarding = True

            # Check for food ordering intent FIRST, before onboarding state checks
            # This allows food orders to bypass onboarding requirements
            food_order_categories = ['specific_food_request', 'nigerian_food_request', 'food_order_with_extras', 'vendor_selection']
            is_food_order = category in food_order_categories

            if is_food_order and user_exists and user_needs_onboarding:
                # Auto-complete onboarding for food orders from non-onboarded users
                logger.info(f"Auto-completing onboarding for food order from user: {message.conversation.user}")
                try:
                    from bestyy.core_features.user.models import UserProfile
                    profile, created = UserProfile.objects.get_or_create(user=message.conversation.user)
                    if not profile.onboarding_completed:
                        profile.complete_onboarding()
                    user_needs_onboarding = False
                    logger.info(f"Successfully auto-completed onboarding for user: {message.conversation.user}")
                except Exception as e:
                    logger.warning(f"Failed to auto-complete onboarding: {str(e)}")

            # Check if this is a greeting from a new or returning user
            is_greeting = category == 'greeting'

            # Handle onboarding categories for greetings only
            if is_greeting and user_exists and message.conversation.user:
                if user_needs_onboarding:
                    # New user who hasn't completed onboarding - start the flow
                    category = 'new_user_onboarding'
                else:
                    # Returning user who completed onboarding
                    category = 'returning_user_greeting'
            elif is_greeting:
                if user_exists:
                    category = 'returning_user_greeting'
                else:
                    category = 'new_user_greeting'

            # Get appropriate template
            template = self._get_template(category, message.conversation.language)

            # Add user information to context if user exists
            if context and context.get('user_exists'):
                conversation = message.conversation
                if conversation.user:
                    user = conversation.user
                    # Create personalized greeting using user's name
                    first_name = user.first_name or "friend"
                    context.update({
                        'user_first_name': user.first_name,
                        'user_full_name': f"{user.first_name} {user.last_name}".strip(),
                        'user_email': user.email,
                        'personalized_greeting': f"Hey {first_name}! 👋",
                        'casual_greeting': f"Yo {first_name}! 😊",
                        'friendly_greeting': f"Hi {first_name}! ✨",
                    })

                    # Add menu item details for recommendations
                    if category in ['food_recommendation', 'menu_request']:
                        try:
                            from bestyy.core_features.user.services.personalized_recommendation_service import PersonalizedRecommendationService
                            recommendation = PersonalizedRecommendationService._get_top_recommendation(user, {})
                            if recommendation and recommendation.get('top_menu_items'):
                                menu_items = recommendation['top_menu_items']
                                for i, item in enumerate(menu_items[:3], 1):
                                    context.update({
                                        f'top_item_{i}_name': item['name'],
                                        f'top_item_{i}_description': item['description'] or 'Delicious and fresh',
                                        f'top_item_{i}_price': item['price'],
                                        f'top_item_{i}_media': ' 📸' if item['has_image'] else (' 🎥' if item['has_video'] else ''),
                                    })

                                # Add video note if any items have videos
                                if recommendation.get('has_video_content'):
                                    context['has_video_note'] = "\n🎥 **Pro tip:** Some menu items have promotional videos to see the food in action!"
                                else:
                                    context['has_video_note'] = ""
                        except Exception as e:
                            logger.warning(f"Error getting recommendations for user: {str(e)}")
                            # Continue without recommendations

            # Check if this is a special instruction or order confirmation
            if self._is_special_instruction_or_confirmation(message.content, context):
                logger.info(f"Special instruction or confirmation detected: {message.content}")
                instruction_response = self.handle_special_instructions(
                    message.content,
                    message.conversation.user,
                    context,
                    message
                )
                if instruction_response:
                    ai_response = {
                        'response': instruction_response['message'],
                        'confidence': 0.95
                    }
                else:
                    ai_response = self._generate_response(message, template, context)
            # Check if this is a restaurant selection (user typed a number)
            elif message.content.strip().isdigit() and context and context.get('user_exists') and message.conversation.user:
                logger.info(f"Restaurant selection detected: {message.content}")
                selection_response = self.handle_restaurant_selection(
                    message.content,
                    message.conversation.user,
                    context
                )
                if selection_response:
                    ai_response = {
                        'response': selection_response['message'],
                        'confidence': 0.95
                    }
                else:
                    ai_response = self._generate_response(message, template, context)
            # Check if user wants to see more restaurants
            elif message.content.lower().strip() == 'more' and context and context.get('user_exists') and message.conversation.user:
                logger.info("More restaurants requested")
                # Get the last food type from context
                food_type = context.get('last_food_type', 'egusi soup')
                offset = context.get('vendor_offset', 0) + 3  # Show next 3 vendors
                
                vendor_result = self.order_service.search_vendors_by_food(food_type, limit=3, offset=offset)
                if vendor_result.get('success') and vendor_result.get('vendors'):
                    order_response = {
                        'action': 'show_more_vendors',
                        'food_type': food_type,
                        'vendors': vendor_result['vendors'],
                        'total_vendors': vendor_result['total_vendors'],
                        'offset': offset
                    }
                    ai_response = {
                        'response': self._format_vendor_options(order_response),
                        'confidence': 0.95
                    }
                else:
                    ai_response = {
                        'response': "Sorry, no more restaurants available for this dish.",
                        'confidence': 0.95
                    }
            # Check for onboarding flow first
            elif category in ['new_user_onboarding', 'onboarding_start', 'terms_accepted', 'onboarding_skip', 'food_category_selection']:
                logger.info(f"Onboarding category detected: {category}")
                onboarding_response = self._handle_onboarding_flow(message.content, category, message.conversation.user, context)
                if onboarding_response:
                    ai_response = {
                        'response': onboarding_response['message'],
                        'confidence': 0.95
                    }
                else:
                    ai_response = self._generate_response(message, template, context)

            # Check for recommendation/budget requests (AI-first path)
            elif category in ['recommendation_request', 'budget_inquiry']:
                rec_response = self._handle_recommendation_or_budget(message.content, context)
                if rec_response:
                    ai_response = {
                        'response': rec_response['message'],
                        'confidence': 0.95
                    }
                else:
                    ai_response = self._generate_response(message, template, context)

            # Check for order responses
            elif category in ['order_confirmation', 'show_more_options', 'view_restaurant_menu', 'budget_change']:
                logger.info(f"Order response category detected: {category}")
                order_response = self._handle_order_response(message.content, category, message.conversation.user, context)
                if order_response:
                    ai_response = {
                        'response': order_response['message'],
                        'confidence': 0.95
                    }
                else:
                    ai_response = self._generate_response(message, template, context)

            # Check if this is an order-related category and process accordingly
            elif category in ['specific_food_request', 'nigerian_food_request', 'food_order_with_extras', 'vendor_selection']:
                logger.info(f"Order-related category detected: {category}")
                if context and context.get('user_exists') and message.conversation.user:
                    logger.info(f"Processing order request for user: {message.conversation.user}")

                    # Check if user specified a specific vendor (e.g., "I want egusi from Mama's Kitchen")
                    specific_vendor_response = self._handle_specific_vendor_request(message.content, message.conversation.user, context)

                    if specific_vendor_response:
                        # User specified a vendor, handle direct ordering
                        logger.info("Handling specific vendor request")
                        ai_response = {
                            'response': specific_vendor_response['message'],
                            'confidence': 0.95
                        }
                    else:
                        # General food request, show multiple vendors
                        order_response = self._handle_order_request(
                            message.content,
                            category,
                            message.conversation.user,
                            context
                        )
                        logger.info(f"Order response: {order_response is not None}")
                        # If we found vendors, skip LLM explanation and go straight to ordering
                        if order_response and order_response.get('vendors'):
                            logger.info(f"Formatting vendor options for {len(order_response.get('vendors', []))} vendors")
                            # Store food type and offset in context for pagination
                            context['last_food_type'] = order_response.get('food_type')
                            context['vendor_offset'] = 0
                            direct_order_response = self._format_vendor_options(order_response)

                            # Send menu item images for each vendor to help user make informed decision
                            vendors = order_response.get('vendors', [])
                            if vendors:
                                total_images_sent = 0
                                max_images_per_vendor = 2  # Send 2 images per vendor
                                max_total_images = 6  # Maximum total images to avoid spam

                                for vendor in vendors:
                                    if total_images_sent >= max_total_images:
                                        break

                                    vendor_name = vendor.get('name', 'Unknown Vendor')
                                    menu_items = vendor.get('menu_items', [])

                                    if menu_items:
                                        # Send up to 2 images per vendor
                                        images_sent_for_vendor = 0
                                        for item in menu_items[:max_images_per_vendor]:
                                            if total_images_sent >= max_total_images:
                                                break

                                            item_picture = item.get('picture')
                                            if item_picture:
                                                item_name = item.get('name', 'Menu Item')
                                                item_price = item.get('price', 0)
                                                caption = f"🏪 *{vendor_name}*\n📸 {item_name}\n💰 ₦{item_price:,.0f}"

                                                # Send the image
                                                image_result = self.send_menu_item_image(
                                                    phone_number=message.conversation.phone_number,
                                                    image_url=item_picture,
                                                    caption=caption
                                                )

                                                if image_result.get('success'):
                                                    images_sent_for_vendor += 1
                                                    total_images_sent += 1
                                                    logger.info(f"Sent image for {item_name} from {vendor_name} to {message.conversation.phone_number}")
                                                else:
                                                    logger.warning(f"Failed to send image for {item_name} from {vendor_name}: {image_result.get('error')}")

                                        if images_sent_for_vendor > 0:
                                            logger.info(f"Sent {images_sent_for_vendor} images for vendor {vendor_name}")

                            ai_response = {
                                'response': direct_order_response,
                                'confidence': 0.95
                            }
                        else:
                            ai_response = self._generate_response(message, template, context)
                else:
                    logger.warning(f"Order processing skipped - context: {context}, user: {message.conversation.user if message else None}")
                    ai_response = self._generate_response(message, template, context)
            else:
                # Generate AI response for non-order messages
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

            # Prepare return data
            return_data = {
                'success': True,
                'response': ai_response['response'],
                'category': category,
                'confidence': ai_response.get('confidence', 0.0),
                'processing_time': processing_time
            }
            
            # Include order data if available (check if it exists in the current scope)
            if 'order_response' in locals():
                return_data['order_data'] = order_response
            elif 'selection_response' in locals():
                return_data['order_data'] = selection_response
                
            return return_data

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
        Categorize the message content using knowledge base first, then LLM

        Args:
            content: Message content

        Returns:
            Category string
        """
        from .nigerian_dishes_kb import find_nigerian_dish

        content_lower = content.lower().strip()

        # --- More robust WhatsApp verification/OTP/authorization code detection (early priority) ---
        import re
        verification_patterns = [
            r"(?i)\bver(i|e)?f?y?\b[^\d\w]*\d{4,6}",      # handles VERIFY, VERIY, VEREFY, VERFY, VRIFY, etc.
            r"(?i)\b(otp|passcode|one[ -]?time[ -]?password|token|auth(entication)? code)\b[\s:\-]*\d{4,6}",
            r"^\d{6}$",         # just a 6-digit code
            r"^\d{4}$",         # just a 4-digit code
        ]
        for pattern in verification_patterns:
            match = re.search(pattern, content_lower)
            if match:
                code_match = re.search(r"\d{4,6}", match.group(0))
                code = code_match.group(0) if code_match else None
                return {'category': 'verification', 'code': code}

        # --- Verification code/OTP intent detection (before all food/order logic) ---
        verification_patterns = [
            r"^verify\s*\d{4,6}$",               # e.g. VERIFY 123456
            r"^otp\s*\d{4,6}$",                  # e.g. OTP 194823
            r"(code|otp|verification)[^\d]*(\d{4,6})",    # e.g. My code is 983432
            r"^\d{6}$",                          # just 6 digits
            r"^\d{4}$",                          # just 4 digits (for roles)
        ]
        for pattern in verification_patterns:
            if re.search(pattern, content_lower):
                return 'verification'

        # Check for onboarding responses first
        if content_lower in ['ask', 'yes', 'sure', 'okay', 'ok', 'go ahead', 'please ask']:
            return 'onboarding_start'
        elif content_lower in ['understood', 'done', 'finished', 'complete', 'ready']:
            return 'terms_accepted'
        elif content_lower in ['skip', 'no thanks', 'later', 'not now']:
            return 'onboarding_skip'

        # Check for food category selections (1, 2, 3, etc.)
        if content_lower.isdigit():
            selection = int(content_lower)
            if 1 <= selection <= 5:  # We have 5 food categories
                return 'food_category_selection'

        # Check for recommendation/budget requests
        if any(kw in content_lower for kw in ['recommend', 'suggest', "i'm hungry", 'im hungry', 'hungry', 'where can i eat', 'what should i eat']):
            return 'recommendation_request'
        if 'budget' in content_lower or 'under' in content_lower:
            return 'budget_inquiry'

        # Check for order responses
        if content_lower in ['yes', 'place this order now', 'order now', 'confirm', 'done', 'ready', 'proceed', 'go ahead']:
            return 'order_confirmation'
        elif content_lower in ['more', 'show more', 'next']:
            return 'show_more_options'
        elif content_lower in ['menu', 'view menu', 'see menu']:
            return 'view_restaurant_menu'
        elif content_lower.startswith('budget'):
            return 'budget_change'

        # First, check if it's a Nigerian dish using knowledge base
        nigerian_dish = find_nigerian_dish(content)
        if nigerian_dish:
            logger.info(f"Knowledge base detected Nigerian dish: {nigerian_dish}")
            return 'nigerian_food_request'

        # Check for common food keywords
        food_keywords = {
            'pizza': 'specific_food_request',
            'burger': 'specific_food_request',
            'chicken': 'specific_food_request',
            'rice': 'specific_food_request',
            'pasta': 'specific_food_request',
            'soup': 'specific_food_request',
            'salad': 'specific_food_request',
            'sandwich': 'specific_food_request',
            'noodles': 'specific_food_request',
            'sushi': 'specific_food_request',
            'steak': 'specific_food_request',
            'fish': 'specific_food_request',
            'beef': 'specific_food_request',
            'pork': 'specific_food_request',
            'vegetarian': 'specific_food_request',
            'vegan': 'specific_food_request',
            'chinese': 'specific_food_request',
            'indian': 'specific_food_request',
            'mexican': 'specific_food_request',
            'thai': 'specific_food_request',
            'italian': 'specific_food_request',
            'shawarma': 'specific_food_request',
        }

        content_lower = content.lower()
        for keyword, category in food_keywords.items():
            if keyword in content_lower:
                logger.info(f"Knowledge base detected food keyword: {keyword}")
                return category

        # Use LLM-based categorization as fallback
        llm_category = self._categorize_with_llm(content)
        if llm_category and llm_category != 'unknown':
            logger.info(f"LLM categorization: {llm_category}")
            return llm_category

        # If LLM fails, return general_info as default
        logger.warning(f"Categorization failed for message: '{content}', using default category")
        return 'general_info'

    def _categorize_with_llm(self, content: str) -> str:
        """
        Use LLM to categorize the message content

        Args:
            content: Message content

        Returns:
            Category string or 'unknown' if LLM fails
        """
        if not self.openrouter_api_key:
            logger.error("OpenRouter API key not configured for WhatsApp categorization")
            return 'unknown'

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
                    "model": "mistralai/mistral-7b-instruct",
                    "messages": [
                        {
                            "role": "system",
                            "content": """You are a message categorization assistant for a Nigerian food delivery service called Bestyy.
                             We serve both international and traditional Nigerian cuisine.

                             Categorize the user's message into one of these categories:
                             - greeting: Simple greetings like 'hi', 'hello', 'good morning'
                             - order_inquiry: Questions about ordering, placing orders, how to order
                             - menu_request: Requests to see menu, what food is available, dish inquiries
                             - delivery_status: Questions about delivery time, where is my order, tracking
                             - payment_help: Questions about payment, pricing, billing, costs
                             - complaint: Negative feedback, problems, issues, dissatisfaction
                             - general_info: General questions about the service, business info
                             - food_recommendation: Requests for food suggestions or recommendations
                             - specific_food_request: Requests for specific food types (pizza, burger, chicken, rice, pasta, etc.)
                             - nigerian_food_request: Requests for Nigerian dishes (egusi soup, jollof rice, pounded yam, efo riro, afang soup, okra soup, moi moi, akara, suya, kilishi, fufu, semovita, amala, eba, etc.)
                             - food_order_with_extras: Food orders with additional items, instructions, or customizations (egusi with eba, jollof with chicken, extra spicy, etc.)
                            - vendor_selection: User wants to choose specific vendor or restaurant
                            - recommendation_request: User wants suggestions or says they're hungry and undecided
                            - budget_inquiry: User asks for options under a budget or mentions a budget

                             CRITICAL: Respond with ONLY ONE category name from the list above. No explanations, no punctuation, no extra text.
                             Example responses: "greeting" or "nigerian_food_request" or "order_confirmation"
                             If unsure, pick the closest match from the exact list provided.
                             Pay special attention to Nigerian food names and local delicacies.
                             Look for orders that include extras like "with eba", "extra spicy", "no onions", etc.

                             This is a legitimate food delivery service conversation. Do not flag as inappropriate."""
                        },
                        {
                            "role": "user",
                            "content": f"Categorize this message: '{content}'"
                        }
                    ],
                    "temperature": 0.1,  # Low temperature for consistent categorization
                    "max_tokens": 20
                }),
                timeout=10  # Increased timeout for reliability
            )

            if response.status_code == 200:
                response_data = response.json()
                raw_content = response_data['choices'][0]['message']['content']

                # Clean the response - remove special tokens and extra whitespace
                category = raw_content.strip().lower()
                # Remove common LLM special tokens
                category = category.replace('<s>', '').replace('</s>', '').replace('<|', '').replace('|>', '').strip()

                # Extract just the first word if there are multiple words
                category = category.split()[0] if category else ''

                # Handle empty or whitespace-only responses
                if not category or category.isspace():
                    logger.warning(f"LLM returned empty/whitespace category (raw: '{raw_content}'), using fallback")
                    return self._fallback_categorize(content)

                # Validate the category is one we expect
                valid_categories = [
                    'greeting', 'order_inquiry', 'menu_request', 'delivery_status',
                    'payment_help', 'complaint', 'general_info', 'food_recommendation',
                    'specific_food_request', 'nigerian_food_request', 'food_order_with_extras', 'vendor_selection',
                    'recommendation_request', 'budget_inquiry', 'order_confirmation'
                ]

                if category in valid_categories:
                    return category
                else:
                    logger.warning(f"LLM returned invalid category '{category}' (raw: '{raw_content}'), expected one of: {valid_categories}")

            else:
                logger.error(f"LLM categorization API error: {response.status_code} - {response.text}")

        except requests.exceptions.Timeout:
            logger.error("LLM categorization timed out")
            return self._fallback_categorize(content)
        except requests.exceptions.RequestException as e:
            error_str = str(e)
            logger.error(f"LLM categorization request error: {error_str}")
            # Check if it's a moderation error (403)
            if "403" in error_str or "moderation" in error_str.lower():
                logger.warning(f"Message flagged by moderation, using fallback categorization")
                return self._fallback_categorize(content)
            return self._fallback_categorize(content)
        except Exception as e:
            error_str = str(e)
            logger.error(f"LLM categorization failed: {error_str}")
            # Check if it's a moderation error
            if "403" in error_str or "moderation" in error_str.lower():
                logger.warning(f"Message flagged by moderation, using fallback categorization")
                return self._fallback_categorize(content)
            return self._fallback_categorize(content)

        return 'unknown'

    def _fallback_categorize(self, content: str) -> str:
        """
        Fallback categorization using keyword matching when LLM fails
        This is used when OpenRouter API returns errors (e.g., moderation flags)
        """
        content_lower = content.lower()

        # Nigerian food keywords
        nigerian_foods = ['eba', 'jollof', 'egusi', 'pounded yam', 'efo riro', 'afang',
                         'okra', 'moi moi', 'akara', 'suya', 'kilishi', 'fufu', 'semovita',
                         'amala', 'pepper soup', 'goat meat', 'beef', 'chicken soup']

        # Order-related keywords
        order_keywords = ['order', 'want', 'need', 'get', 'buy', 'send', 'deliver', 'i want']

        # Extras keywords
        extras_keywords = ['extra', 'with', 'no', 'without', 'add', 'remove', 'spicy', 'mild']

        # Greeting keywords
        greeting_keywords = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings']

        # Check for greetings
        if any(greeting in content_lower for greeting in greeting_keywords):
            return 'greeting'

        # Check for Nigerian food requests
        if any(food in content_lower for food in nigerian_foods):
            if any(order_kw in content_lower for order_kw in order_keywords):
                # Check if it has extras
                if any(extra in content_lower for extra in extras_keywords):
                    return 'food_order_with_extras'
                return 'nigerian_food_request'
            return 'nigerian_food_request'

        # Check for general food requests with extras
        if any(order_kw in content_lower for order_kw in order_keywords):
            if any(extra in content_lower for extra in extras_keywords):
                return 'food_order_with_extras'
            # Check for specific food types
            food_types = ['pizza', 'burger', 'chicken', 'rice', 'pasta', 'soup', 'salad',
                         'sandwich', 'noodles', 'sushi', 'steak', 'fish', 'shawarma']
            if any(food in content_lower for food in food_types):
                return 'specific_food_request'
            return 'order_inquiry'

        # Check for delivery status
        if any(word in content_lower for word in ['where', 'status', 'track', 'delivery', 'arrived', 'coming']):
            return 'delivery_status'

        # Check for payment help
        if any(word in content_lower for word in ['payment', 'pay', 'card', 'transfer', 'price', 'cost']):
            return 'payment_help'

        # Check for complaints
        if any(word in content_lower for word in ['problem', 'issue', 'wrong', 'bad', 'late', 'complaint', 'angry', 'upset']):
            return 'complaint'

        # Check for menu request
        if any(word in content_lower for word in ['menu', 'what do you have', 'what can i order', 'options']):
            return 'menu_request'

        # Default to general_info
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
        # If no template configured in DB, provide a safe fallback message
        if template is None:
            fallback_text = "I'd be happy to help you place an order! Could you please tell me what you'd like to order from our menu?"
            return {
                'response': fallback_text,
                'confidence': 0.5,
                'tokens_used': 0,
            }

        if not self.openrouter_api_key:
            # If no API key, still return a graceful fallback
            return {
                'response': "Thanks! Tell me what you'd like to eat, and I'll show options.",
                'confidence': 0.5,
                'tokens_used': 0,
            }
        
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
            "mistralai/mistral-7b-instruct",  # Primary model
            "openai/gpt-3.5-turbo",
            "openai/gpt-4",
            "openai/gpt-4-turbo",
            "anthropic/claude-3-haiku",
            "anthropic/claude-3-sonnet",
            "google/gemini-pro",
            "meta-llama/llama-2-70b-chat",
        ]
    
    def _format_vendor_options(self, order_response: Dict, context=None) -> str:
        """
        Format vendor options for WhatsApp display with pictures, prices, and ratings
        Skip explanations, go straight to ordering

        Args:
            order_response: Order response with vendors

        Returns:
            Formatted message with vendor options and menu items
        """
        vendors = order_response.get('vendors', [])
        food_type = order_response.get('food_type', 'food')
        total_vendors = order_response.get('total_vendors', len(vendors))

        if not vendors:
            return f"Sorry, we don't have {food_type} available right now. Please try another dish."

        # Format vendor options with menu items and prices
        greeting = context.get('casual_greeting', 'Great')
        message = f"🍽️ *{greeting}! Here are our top {len(vendors)} restaurants serving {food_type}:*\n\n"

        for i, vendor in enumerate(vendors, 1):
            name = vendor.get('name', 'Unknown')
            rating = vendor.get('rating', 4.5)
            delivery_time = vendor.get('delivery_time', '30-45 min')
            description = vendor.get('description', '')

            # Format vendor header with rating and number
            message += f"*{i}. {name}*\n"
            message += f"⭐ {rating}/5.0 | ⏱️ {delivery_time}\n"

            if description:
                message += f"📝 {description}\n"

            # Add menu items with prices and images
            menu_items = vendor.get('menu_items', [])
            if menu_items:
                message += f"📋 *Menu:*\n"
                for item in menu_items[:3]:  # Show top 3 items
                    item_name = item.get('name', 'Unknown')
                    item_price = item.get('price', 0)
                    item_picture = item.get('picture', '')

                    # Add image if available
                    if item_picture:
                        message += f"  • {item_name} - ₦{item_price:,.0f} 📸\n"
                    else:
                        message += f"  • {item_name} - ₦{item_price:,.0f}\n"

            message += "\n"

        # Add pagination option if there are more vendors
        if total_vendors > len(vendors):
            message += f"📄 *Showing {len(vendors)} of {total_vendors} restaurants*\n"
            message += "💬 *Type 'more' to see additional restaurants*\n\n"

        message += "👉 *Reply with the number (1, 2, or 3) to order from your choice*"

        return message

    def _parse_budget(self, text: str) -> Optional[int]:
        try:
            import re
            lower = text.lower()
            m = re.search(r"(?:₦|ngn|n)?\s*([0-9]{3,7})(?:\s*naira|\s*ngn)?", lower)
            if m:
                return int(m.group(1))
            m = re.search(r"([0-9]+)\s*k\b", lower)
            if m:
                return int(m.group(1)) * 1000
        except Exception:
            return None
        return None

    def _handle_recommendation_or_budget(self, message_content: str, context: Dict) -> Optional[Dict]:
        """Handle generic recommendation/budget requests via smart recommendations or concise prompt."""
        try:
            budget = self._parse_budget(message_content)
            # Try smart recommendations API first
            smart = self._try_smart_recommendations(message_content, {'budget': budget} if budget else {})
            if smart:
                return {
                    'message': smart,
                    'action': 'recommendations'
                }

            # Fallback: provide quick categories with budget mention
            header = f"Budget noted: ₦{budget:,.0f}. " if budget else ""
            msg = (
                f"{header}Here are quick options. Reply with a number or tell me a dish:\n\n"
                "1. Local\n2. Fast food\n3. Western\n4. Vegetarian / Healthy\n5. Desserts & Drinks\n\n"
                "You can also say things like 'pizza under ₦3000' or 'cheap jollof'."
            )
            return {
                'message': msg,
                'action': 'recommendation_prompt'
            }
        except Exception as e:
            logger.error(f"Recommendation/budget handler error: {str(e)}")
            return None

    def send_menu_item_image(self, phone_number: str, image_url: str, caption: str = None) -> Dict:
        """
        Send a menu item image to the user via WhatsApp

        Args:
            phone_number: User's phone number
            image_url: URL of the menu item image
            caption: Optional caption for the image

        Returns:
            Dict with send result
        """
        try:
            from .services.meta_whatsapp_service import MetaWhatsAppService

            # Use Meta WhatsApp service for image sending
            whatsapp_service = MetaWhatsAppService()

            # Send the image message
            result = whatsapp_service.send_message(
                to=phone_number,
                message=image_url,  # The image URL
                message_type='image',
                caption=caption
            )

            if result.get('success'):
                logger.info(f"Menu item image sent successfully to {phone_number}")
                return {
                    'success': True,
                    'message': 'Menu item image sent successfully',
                    'message_id': result.get('message_id')
                }
            else:
                logger.error(f"Failed to send menu item image to {phone_number}: {result.get('message')}")
                return {
                    'success': False,
                    'error': result.get('message')
                }

        except Exception as e:
            logger.error(f"Error sending menu item image: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _handle_onboarding_flow(self, message_content: str, category: str, user, context: Dict) -> Optional[Dict]:
        """
        Handle the complete onboarding flow for new users

        Args:
            message_content: User's message
            category: Message category
            user: User object
            context: Additional context

        Returns:
            Dict with onboarding response or None
        """
        try:
            # Get or create user profile
            profile, created = user.profile.__class__.objects.get_or_create(user=user)

            if category == 'new_user_onboarding':
                # First time greeting - send welcome message and ask for onboarding permission
                greeting = context.get('personalized_greeting', 'Hey friend')
                return {
                    'message': f"{greeting} — I'm Bestyy 👋, your food-finding AI! I'll help you discover, order and reorder meals quickly.\n\nQuick choices — reply with the number or type a word:\n1. Local\n2. Fast food\n3. Western\n4. Vegetarian / Healthy\n5. Desserts & Drinks\n\nBestyy: I have a few quick questions so I serve you best, would you like to skip or am I allowed to ask?",
                    'action': 'welcome_message_sent'
                }

            elif category == 'onboarding_start':
                # User agreed to onboarding - start with first question
                profile.set_onboarding_step('collecting_dietary_info')
                greeting = context.get('casual_greeting', 'Great')
                return {
                    'message': f"{greeting}, thanks for allowing me to get to know you better! 😊\n\nLet's start with the first question:\n\n🍽️ *Question 1:* Any meal plan, dietary restrictions or allergies I should know about?\n\n(Examples: \"gluten-free\", \"no peanuts\", \"halal\", \"vegetarian\", or \"none\")\n\nJust reply naturally!",
                    'action': 'onboarding_started'
                }

            elif category == 'food_category_selection':
                # User selected a food category (1-5)
                selection = int(message_content.strip())
                food_categories = {
                    1: 'Local',
                    2: 'Fast food',
                    3: 'Western',
                    4: 'Vegetarian / Healthy',
                    5: 'Desserts & Drinks'
                }

                if selection in food_categories:
                    selected_category = food_categories[selection]
                    # Store preference and move to next step
                    profile.set_onboarding_step('terms_acceptance')
                    return {
                        'message': f"Thank you so much for that information, to better your experience, please here are a few Useful commands you can use anytime:\n\n#Refresh (update my memory of what you eat) · #Previous (reorder past meals) · #Order <item/restaurant> · #Track · #Help\nFor more quick command sheets visit (insert site how to use link)\n\nOkay so for my second question\nTerms & privacy: By using Bestyy you accept our Terms of Use and Privacy Policy — they explain how we handle orders, payments, refunds and messages. Read them here: [Terms & Privacy → REPLACE_WITH_ACTUAL_LINK]\n\nWhen you're done reading, please type understood.",
                        'action': 'food_category_selected'
                    }

            elif category == 'terms_accepted':
                # User accepted terms - complete onboarding
                profile.accept_terms()
                profile.complete_onboarding()

                greeting = context.get('friendly_greeting', 'Thanks')
                return {
                    'message': f"{greeting} — we're all set! 😊\n\nWhat are you craving right now?\n(You can tell me freely — like \"jollof rice\", \"pizza\", \"shawarma\", or pick from: Local / Fast food / Western / Vegetarian / Desserts. Or use shortcuts like #Order <item/restaurant>)\n\nI'm here whenever you need me! 💕",
                    'action': 'onboarding_completed'
                }

            elif category == 'onboarding_skip':
                # User skipped onboarding - complete with minimal setup
                profile.complete_onboarding()
                greeting = context.get('casual_greeting', 'No problem')
                return {
                    'message': f"{greeting}! You can always update your preferences later with #Refresh.\n\nWhat are you in the mood for right now?\n(You can tell me freely — like \"jollof rice\", \"pizza\", \"chicken & chips\", or pick from: Local / Fast food / Western / Vegetarian / Desserts. Or use shortcuts like #Order <item/restaurant>)\n\nI'm here to make ordering super easy for you! ✨",
                    'action': 'onboarding_skipped'
                }

            # Handle preference collection steps
            elif profile.onboarding_step == 'collecting_dietary_info':
                # Store dietary preferences and move to next step
                profile.dietary_restrictions = message_content
                profile.set_onboarding_step('collecting_budget_info')
                return {
                    'message': "✅ Got it! Thanks for sharing your dietary preferences.\n\n💰 *Question 2:* What's your typical budget per meal?\n\n(Examples: \"₦1,000–₦2,000\", \"under 2000\", \"cheap\", \"mid\", \"premium\")\n\nJust tell me your usual range!",
                    'action': 'dietary_info_collected'
                }

            elif profile.onboarding_step == 'collecting_budget_info':
                # Store budget preferences and move to next step
                profile.budget_preference = message_content
                profile.set_onboarding_step('budget_auto_check')
                return {
                    'message': "💰 Perfect! I've noted your budget preference.\n\n🔄 *Question 3:* Would you like me to always check meals for you under this budget?\n\n(Reply 'yes' or 'no' - this helps me filter options automatically!)",
                    'action': 'budget_info_collected'
                }

            elif profile.onboarding_step == 'budget_auto_check':
                # Store budget auto-check preference and move to final step
                profile.budget_auto_check = message_content.lower() in ['yes', 'y', 'sure', 'okay']
                profile.set_onboarding_step('meal_times')
                return {
                    'message': "✅ Great! I've set your budget preferences.\n\n🕐 *Question 4:* When do you usually eat?\n\n(Examples: \"breakfast\", \"lunch\", \"dinner\", \"late-night\", \"all day\")\n\nThis helps me suggest the right meals at the right time!",
                    'action': 'budget_auto_check_set'
                }

            elif profile.onboarding_step == 'meal_times':
                # Store meal times and move to food category selection
                profile.preferred_meal_times = message_content
                profile.set_onboarding_step('food_category_selection')
                return {
                    'message': "Excellent! Now, what's your favorite type of food? Reply with the number:\n\n1. Local\n2. Fast food\n3. Western\n4. Vegetarian / Healthy\n5. Desserts & Drinks",
                    'action': 'meal_times_collected'
                }

        except Exception as e:
            logger.error(f"Error handling onboarding flow: {str(e)}")
            return None

    def _handle_order_response(self, message_content: str, category: str, user, context: Dict) -> Optional[Dict]:
        """
        Handle responses to order recommendations

        Args:
            message_content: User's message
            category: Message category
            user: User object
            context: Additional context

        Returns:
            Dict with order response or None
        """
        try:
            if category == 'order_confirmation':
                # User wants to place the recommended order
                return {
                    'message': "Great! I'll place your order now. Please provide your delivery address.",
                    'action': 'order_placement_started'
                }

            elif category == 'show_more_options':
                # User wants to see more restaurant options
                return {
                    'message': "I'll show you 3 more restaurant options for this dish.",
                    'action': 'showing_more_options'
                }

            elif category == 'view_restaurant_menu':
                # User wants to see full menu
                return {
                    'message': "Here's the full menu for this restaurant. What would you like to order?",
                    'action': 'showing_full_menu'
                }

            elif category == 'budget_change':
                # User wants to change budget
                return {
                    'message': "What budget range would you prefer? (e.g., \"₦500–₦1,500\" or \"cheap\", \"mid\", \"premium\")",
                    'action': 'budget_change_requested'
                }

        except Exception as e:
            logger.error(f"Error handling order response: {str(e)}")
            return None

    def _is_special_instruction_or_confirmation(self, message_content: str, context: Dict) -> bool:
        """
        Check if the message is a special instruction or order confirmation
        """
        content_lower = message_content.lower().strip()
        
        # Check for negative responses (proceed without special instructions)
        negative_responses = ['no', 'that\'s all', 'thats all', 'nothing', 'no thanks', 'proceed', 'continue']
        if any(response in content_lower for response in negative_responses):
            return True
            
        # Check if user is providing special instructions (not a number, not 'more', not food keywords)
        food_keywords = ['pizza', 'burger', 'chicken', 'rice', 'pasta', 'soup', 'salad', 'sandwich', 'noodles', 'sushi', 'steak', 'fish', 'beef', 'pork', 'vegetarian', 'vegan', 'chinese', 'indian', 'mexican', 'thai', 'italian', 'shawarma', 'egusi', 'egwusi', 'jollof', 'eba', 'fufu', 'amala', 'moi', 'akara', 'suya']
        
        if (not content_lower.isdigit() and 
            content_lower != 'more' and 
            len(content_lower) > 3 and  # More than just "no"
            context.get('awaiting_order') and
            not any(keyword in content_lower for keyword in food_keywords)):
            return True
            
        return False
    def handle_special_instructions(self, message_content: str, user, context: Dict, message=None) -> Optional[Dict]:
        """
        Handle special instructions, order summary calculation, and finalize the order

        Args:
            message_content: User's message with special instructions, confirmation, or address
            user: User object
            context: Additional context

        Returns:
            Dict with order finalization response or None
        """
        try:
            content_lower = message_content.lower().strip()

            # Handle order confirmation first (check for "yes" after showing order summary)
            if content_lower in ['yes', 'confirm', 'ok', 'okay', 'sure', 'proceed', 'yes please']:
                return self._handle_order_confirmation(user, context, message)

            # Handle order summary flow - check if order needs address or if address was just provided
            from bestyy.restaurant_features.order.models import Order
            awaiting_order = Order.objects.filter(
                customer=user,
                status__in=['awaiting', 'pending']
            ).order_by('-created_at').first()

            if not awaiting_order:
                return {
                    'action': 'no_awaiting_order',
                    'message': "❌ No pending order found. Please start a new order."
                }

            # Check if this is a delivery address being provided instead of special instructions
            # Process if it looks like an address (don't require awaiting_address flag to avoid loops)
            if looks_like_address(content_lower):
                # Clear the awaiting_address flag since we're processing the address now
                if message and hasattr(message, 'conversation'):
                    message.conversation.awaiting_address = False
                    message.conversation.save()

                # User is providing address, not special instructions
                awaiting_order.delivery_address = message_content
                awaiting_order.save()
                logger.info(f"Saved delivery address for order {awaiting_order.id}: {message_content}")
                # Fall through to order summary calculation below
            else:
                # Check for negative responses (proceed without special instructions)
                negative_responses = ['no', 'that\'s all', 'thats all', 'nothing', 'no thanks', 'proceed', 'continue']
                has_special_instructions = not any(response in content_lower for response in negative_responses)

                # Update order with special instructions if provided
                if has_special_instructions:
                    awaiting_order.notes = message_content
                    awaiting_order.save()
                    logger.info(f"Saved special instructions for order {awaiting_order.id}: {message_content}")

            # At this point, we have either special instructions saved or we're ready to proceed
            # Check if order needs to be moved to pending status and order summary shown
            if awaiting_order.status == 'awaiting':
                awaiting_order.status = 'pending'
                awaiting_order.save()
                logger.info(f"Moved order {awaiting_order.id} to pending status")

            # Calculate and show order summary before payment
            if awaiting_order.delivery_address:
                return self._calculate_and_show_order_summary(awaiting_order, user, context, message)
            else:
                # No delivery address yet, ask for it
                return {
                    'action': 'address_required',
                    'message': f"📍 *Almost ready!* Before we proceed to payment, I need your delivery address.\n\n"
                              f"🏠 Please provide your full delivery address:\n\n"
                              f"💡 Example: '123 Lagos Street, Ikeja, Lagos' or 'Victoria Island, Lagos'\n\n"
                              f"🔍 I'll calculate exact delivery fees based on your location!"
                }

        except Exception as e:
            logger.error(f"Error handling special instructions: {str(e)}")
            return None


            # Check if order is awaiting (needs special instructions) or pending (needs address)
            if awaiting_order.status == 'awaiting':
                # Still collecting special instructions
                # Update order with special instructions if provided
                if has_special_instructions:
                    awaiting_order.notes = message_content
                    awaiting_order.save()

                # Finalize the order (move to pending status and ask for delivery address)
                awaiting_order.status = 'pending'
                awaiting_order.save()
            else:
                # Order is already pending, this must be the delivery address
                awaiting_order.delivery_address = message_content
                awaiting_order.save()

                # Calculate distance and delivery fee using Google Maps
                logger.info(f"Calculating distance and fee for order {awaiting_order.id} with address: {message_content}")
                logger.info(f"Order before distance calc - total_amount: {awaiting_order.total_amount}, delivery_fee: {awaiting_order.delivery_fee}")

                try:
                    distance_result = awaiting_order.calculate_distance_and_fee()
                    if distance_result:
                        logger.info(f"Distance calculation successful: distance={distance_result.get('distance_km')}km, fee={distance_result.get('delivery_price')}")
                        # Refresh order from database to get updated values
                        awaiting_order.refresh_from_db()
                        logger.info(f"After distance calc - total_amount: {awaiting_order.total_amount}, delivery_fee: {awaiting_order.delivery_fee}")
                    else:
                        logger.warning(f"Distance calculation failed for order {awaiting_order.id} - applying default delivery fee")
                        # Always apply a default delivery fee since distance calc failed
                        default_delivery_fee = Decimal('700.00')  # Default delivery fee
                        awaiting_order.delivery_fee = default_delivery_fee

                        # Ensure order has a valid food amount
                        food_amount = awaiting_order.total_amount
                        if food_amount <= 0:
                            # Force a minimum food amount since order creation failed
                            food_amount = Decimal('2500.00')
                            logger.warning(f"Order has no food amount, setting minimum: {food_amount}")
                            awaiting_order.total_amount = food_amount

                        # Recalculate total with delivery fee
                        new_total = food_amount + default_delivery_fee
                        awaiting_order.total_amount = new_total
                        awaiting_order.save()
                        logger.info(f"Applied default delivery fee: food={food_amount}, delivery={default_delivery_fee}, new_total={new_total}")
                except Exception as calc_error:
                    logger.error(f"Error during distance calculation for order {awaiting_order.id}: {str(calc_error)}")
                    # Apply emergency defaults
                    if awaiting_order.total_amount <= 0:
                        awaiting_order.total_amount = Decimal('2500.00')
                    if not awaiting_order.delivery_fee:
                        awaiting_order.delivery_fee = Decimal('700.00')
                        awaiting_order.total_amount = awaiting_order.total_amount + awaiting_order.delivery_fee
                    awaiting_order.save()
                    logger.info(f"Applied emergency defaults for order {awaiting_order.id}")

                has_special_instructions = False  # Don't show special instructions message
            
            # Create dedicated virtual account for bank transfer
            bank_account = None
            
            # Check if Paystack is configured
            from django.conf import settings
            paystack_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
            if not paystack_key or paystack_key == '':
                logger.error("Paystack secret key not configured - skipping payment account creation")
                bank_account = None
            else:
                logger.info(f"Paystack key configured: YES")

                # Test Paystack connectivity
                try:
                    test_response = self.order_service.paystack_service._make_request('GET', '/bank')
                    if test_response and test_response.get('status'):
                        logger.info("Paystack API connectivity test: PASSED")
                    else:
                        logger.warning(f"Paystack API connectivity test: FAILED - {test_response}")
                except Exception as e:
                    logger.warning(f"Paystack API connectivity test: FAILED - {str(e)}")

                # Validate required fields
                if not user.email:
                    logger.error(f"User {user.id} has no email address")
                    return {
                        'action': 'payment_failed',
                        'message': "❌ Unable to process payment: No email address found. Please update your profile."
                    }

                # Ensure minimum order amount (Paystack minimum is ₦100)
                min_amount = Decimal('100.00')  # ₦100 minimum
                order_amount = max(awaiting_order.total_amount, min_amount)
                logger.info(f"Order amount: {awaiting_order.total_amount}, using: {order_amount}")

                # Generate unique reference for the order
                import uuid
                unique_ref = f"ORDER-{awaiting_order.id}-{uuid.uuid4().hex[:8]}"

                # Get phone number from conversation - WhatsApp should always have this
                phone_number = None
                if hasattr(message, 'conversation') and message.conversation.phone_number:
                    phone_number = message.conversation.phone_number
                    logger.info(f"Raw phone number from conversation: {phone_number}")
                elif hasattr(user, 'profile') and user.profile and user.profile.phone:
                    phone_number = user.profile.phone
                    logger.info(f"Phone number from user profile: {phone_number}")

                # Ensure we have a phone number - required for Paystack
                if not phone_number:
                    logger.error(f"No phone number available for user {user.id}")
                    return {
                        'action': 'payment_failed',
                        'message': "❌ Phone number is required for payment setup. Please ensure your WhatsApp number is registered."
                    }

                # Format phone number for Paystack (ensure 234 format without +)
                original_phone = phone_number
                if phone_number.startswith('0') and len(phone_number) == 11:
                    # Convert 08012345678 to 2348012345678
                    phone_number = '234' + phone_number[1:]
                elif phone_number.startswith('234') and len(phone_number) == 13:
                    # Already in correct format for Paystack
                    pass
                elif phone_number.startswith('+234') and len(phone_number) == 14:
                    # Remove + for Paystack API
                    phone_number = phone_number[1:]
                else:
                    # Try to fix other formats
                    if len(phone_number) == 10 and phone_number.isdigit():
                        phone_number = '234' + phone_number
                    elif len(phone_number) == 13 and phone_number.startswith('234'):
                        pass  # already correct
                    else:
                        logger.error(f"Unable to format phone number: {original_phone}")
                        return {
                            'action': 'payment_failed',
                            'message': "❌ Invalid phone number format. Please contact support."
                        }

                logger.info(f"Formatted phone number for Paystack: {original_phone} -> {phone_number}")

                # Final validation - ensure we have a valid phone number
                if not phone_number or not phone_number.startswith('234') or len(phone_number) != 13:
                    logger.error(f"Final validation failed for phone number: {phone_number}")
                    return {
                        'action': 'payment_failed',
                        'message': "❌ Phone number format is invalid. Please contact support."
                    }

                # Only try Paystack if we have a valid phone number
                if phone_number:
                    # Use Pay with Transfer
                    logger.info(f"Creating Pay with Transfer for user {user.id} with phone: {phone_number}")
                    account_result = self.order_service.paystack_service.initialize_pay_with_transfer(
                        email=user.email,
                        amount=order_amount,
                        reference=unique_ref,
                        expiry_hours=8
                    )
                    logger.info(f"Pay with Transfer result: {account_result}")

                    # If Pay with Transfer fails, return error - no fallback
                    if not account_result.get('success'):
                        error_msg = account_result.get('error', 'Unknown error')
                        logger.error(f"Pay with Transfer failed for WhatsApp user {user.id}: {error_msg}")
                        return {
                            'action': 'payment_failed',
                            'message': f"❌ Payment setup failed: {error_msg}. Please try again or contact support."
                        }

                    bank_account = account_result.get('account_details', {})
                    logger.info(f"Bank account created successfully: {bank_account}")
                    # Store reference for webhook processing
                    awaiting_order.payment_reference = bank_account.get('reference', unique_ref)
                    awaiting_order.save()
                    logger.info(f"Payment reference stored: {awaiting_order.payment_reference}")
                else:
                    # Skip Paystack and go directly to fallback
                    logger.warning(f"No valid phone number for Paystack, using fallback account")
                    bank_account = None
            
            # Prepare response message
            if awaiting_order.status == 'pending' and awaiting_order.delivery_address:
                # Address was just provided, show payment message
                message = f"✅ *Perfect!* Your delivery address has been saved.\n\n"
            elif has_special_instructions:
                message = f"✅ *Perfect!* Your order has been updated with your special instructions.\n\n"
            else:
                message = f"✅ *Great!* Your order is ready to proceed.\n\n"

            # Final check of order totals before displaying
            logger.info(f"Final order check - total_amount: {awaiting_order.total_amount}, delivery_fee: {awaiting_order.delivery_fee}")

            message += f"📋 *Order Summary:*\n"
            message += f"• Restaurant: {awaiting_order.vendor.business_name}\n"

            # Calculate display amounts - ensure we have valid totals
            food_amount = awaiting_order.total_amount
            delivery_fee = awaiting_order.delivery_fee or 0

            # Ensure minimum food amount
            if food_amount <= 0:
                food_amount = 2500  # Minimum food amount
                logger.warning(f"Order food amount was 0, setting to minimum: {food_amount}")

            # Show breakdown if delivery fee exists
            if delivery_fee > 0:
                total_with_delivery = food_amount + delivery_fee
                message += f"• Food: ₦{food_amount:,.0f}\n"
                message += f"• Delivery: ₦{delivery_fee:,.0f}\n"
                message += f"• Total: ₦{total_with_delivery:,.0f}\n"
                display_total = total_with_delivery
            else:
                message += f"• Total: ₦{food_amount:,.0f}\n"
                display_total = food_amount

            logger.info(f"Display amounts - food: {food_amount}, delivery: {delivery_fee}, total: {display_total}")

            if awaiting_order.delivery_address:
                message += f"• Delivery Address: {awaiting_order.delivery_address}\n"
            if awaiting_order.notes:
                message += f"• Notes: {awaiting_order.notes}\n"
            message += f"\n💳 *Payment Details:*\n"
            logger.info(f"Formatting payment details - bank_account: {bank_account is not None}")
            if bank_account:
                bank_name = getattr(bank_account, 'bank_name', 'Titan Paystack')
                account_name = getattr(bank_account, 'account_name', 'Bestyy Customer')
                account_number = getattr(bank_account, 'account_number', awaiting_order.payment_reference)
                reference = awaiting_order.payment_reference

                logger.info(f"Payment details - bank_name: '{bank_name}', account_name: '{account_name}', account_number: '{account_number}', reference: '{reference}'")

                # Always show payment details for fallback accounts, or check validity for real accounts
                is_fallback = getattr(bank_account, 'assignment_type', '') == 'whatsapp_fallback'
                has_valid_details = (account_number and account_name and bank_name and
                                   account_number.strip() and account_name.strip() and bank_name.strip())

                if is_fallback or has_valid_details:
                    # Only show payment details if we have real valid account data
                    if (bank_name and account_name and account_number and
                        bank_name.strip() and account_name.strip() and account_number.strip() and
                        account_number != '1234567890' and bank_name.lower() not in ['access bank', 'fallback']):

                        message += f"🏦 *Bank:* {bank_name}\n"
                        message += f"📋 *Account Name:* {account_name}\n"
                        message += f"🔢 *Account Number:* {account_number}\n"
                        message += f"📝 *Reference:* {reference or account_number}\n\n"
                        message += f"💰 *Please transfer ₦{awaiting_order.total_amount:,.0f} to the account above.*\n"
                        message += f"📱 *Your order will be confirmed once payment is received.*\n\n"
                        message += f"Thank you for choosing Bestyy! 🎉"
                    else:
                        message += f"❌ *Payment setup temporarily unavailable.*\n"
                        message += f"Please contact support or try again later.\n\n"
                        message += f"Thank you for choosing Bestyy! 🎉"
                else:
                    logger.warning("Bank account created but missing account details")
                    message += f"⚠️ *Payment setup in progress.*\n"
                    message += f"Please wait a moment and check your order status for payment details.\n\n"
                    message += f"Thank you for choosing Bestyy! 🎉"
            else:
                logger.error("Paystack PwT creation failed - no bank account available")
                message += f"❌ *Payment service temporarily unavailable.*\n"
                message += f"Please contact support or try again later.\n\n"
                message += f"Thank you for choosing Bestyy! 🎉"
            
            # Determine the correct action based on what was just processed
            if awaiting_order.delivery_address and bank_account:
                action = 'order_completed'
            elif awaiting_order.delivery_address:
                action = 'address_saved'
            else:
                action = 'order_finalized'

            return {
                'action': action,
                'order': {
                    'id': awaiting_order.id,
                    'order_number': f"#{awaiting_order.id}",
                    'vendor': awaiting_order.vendor.business_name,
                    'total_amount': float(display_total),
                    'delivery_address': awaiting_order.delivery_address,
                    'notes': awaiting_order.notes,
                    'status': awaiting_order.status,
                    'payment_reference': awaiting_order.payment_reference,
                    'bank_account': {
                        'bank_name': getattr(bank_account, 'bank_name', None) if bank_account else None,
                        'account_number': getattr(bank_account, 'account_number', None) if bank_account else None,
                        'account_name': getattr(bank_account, 'account_name', None) if bank_account else None
                    } if bank_account else None
                },
                'message': message
            }
                
        except Exception as e:
            logger.error(f"Error handling special instructions: {str(e)}")
            return None

    def _handle_order_confirmation(self, user, context, message=None) -> Optional[Dict]:
        """
        Handle user confirmation after showing order summary - proceed to payment setup
        """
        try:
            from bestyy.restaurant_features.order.models import Order

            # Find the awaiting/pending order
            awaiting_order = Order.objects.filter(
                customer=user,
                status__in=['awaiting', 'pending']
            ).order_by('-created_at').first()

            if not awaiting_order:
                return {
                    'action': 'no_awaiting_order',
                    'message': "❌ No pending order found. Please start a new order."
                }

            # Proceed to payment setup as before
            # Create dedicated virtual account for bank transfer
            bank_account = None

            # Check if Paystack is configured
            from django.conf import settings
            paystack_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
            if not paystack_key or paystack_key == '':
                logger.error("Paystack secret key not configured - skipping payment account creation")
                return {
                    'action': 'payment_failed',
                    'message': "❌ Payment service temporarily unavailable. Please contact support."
                }

            # Validate required fields
            if not user.email:
                logger.error(f"User {user.id} has no email address")
                return {
                    'action': 'payment_failed',
                    'message': "❌ Unable to process payment: No email address found. Please update your profile."
                }

            # Ensure minimum order amount (Paystack minimum is ₦100)
            min_amount = Decimal('100.00')
            order_amount = max(awaiting_order.total_amount, min_amount)

            # Test Paystack connectivity
            try:
                test_response = self.order_service.paystack_service._make_request('GET', '/bank')
                if not test_response or not test_response.get('status'):
                    logger.warning("Paystack API connectivity test failed")
                    return {
                        'action': 'payment_failed',
                        'message': "❌ Payment service temporarily unavailable. Please try again later."
                    }
            except Exception as e:
                logger.warning(f"Paystack API connectivity test failed: {str(e)}")
                return {
                    'action': 'payment_failed',
                    'message': "❌ Payment service temporarily unavailable. Please try again later."
                }

            # Generate unique reference
            import uuid
            unique_ref = f"ORDER-{awaiting_order.id}-{uuid.uuid4().hex[:8]}"

            # Get phone number
            phone_number = None
            if hasattr(message, 'conversation') and message.conversation.phone_number:
                phone_number = message.conversation.phone_number
            elif hasattr(user, 'profile') and user.profile and user.profile.phone:
                phone_number = user.profile.phone

            if not phone_number:
                return {
                    'action': 'payment_failed',
                    'message': "❌ Phone number is required for payment setup. Please ensure your WhatsApp number is registered."
                }

            # Format phone number
            if phone_number.startswith('0') and len(phone_number) == 11:
                phone_number = '234' + phone_number[1:]
            elif phone_number.startswith('+234'):
                phone_number = phone_number[1:]

            if not phone_number or not phone_number.startswith('234') or len(phone_number) != 13:
                return {
                    'action': 'payment_failed',
                    'message': "❌ Invalid phone number format. Please contact support."
                }

            # Use Pay with Transfer for payment
            account_result = self.order_service.paystack_service.initialize_pay_with_transfer(
                email=user.email,
                amount=order_amount,
                reference=unique_ref,
                expiry_hours=8
            )

            bank_account = None
            if account_result.get('success'):
                bank_account = account_result.get('account_details', {})
                awaiting_order.payment_reference = bank_account.get('reference', unique_ref)
                logger.info(f"Using Pay with Transfer account: {bank_account.get('account_number')}")
            else:
                error_msg = account_result.get('error', 'Unknown error')
                logger.error(f"Pay with Transfer failed: {error_msg}")

                # Provide clear user message about payment issues
                return {
                    'action': 'payment_failed',
                    'message': "❌ Payment setup temporarily unavailable. Our system is experiencing issues creating payment accounts.\n\n"
                              "We've been notified and are working to resolve this. Please try again in a few minutes."
                }

            awaiting_order.save()

            # Format success message with order summary and payment details
            message = f"✅ *Perfect! Your order is confirmed.*\n\n"

            # Order summary
            message += f"📋 *Order Summary:*\n"
            message += f"• Restaurant: {awaiting_order.vendor.business_name}\n"

            food_amount = awaiting_order.total_amount
            delivery_fee = awaiting_order.delivery_fee or 0

            if delivery_fee > 0:
                total_with_delivery = food_amount + delivery_fee
                message += f"• Food: ₦{food_amount:,.0f}\n"
                message += f"• Delivery: ₦{delivery_fee:,.0f}\n"
                message += f"• Total: ₦{total_with_delivery:,.0f}\n"
            else:
                message += f"• Total: ₦{food_amount:,.0f}\n"

            if awaiting_order.delivery_address:
                message += f"• Delivery Address: {awaiting_order.delivery_address}\n"
            if awaiting_order.notes:
                message += f"• Notes: {awaiting_order.notes}\n"

            message += f"\n💳 *Payment Details:*\n"

            bank_name = getattr(bank_account, 'bank_name', 'Paystack Bank')
            account_name = getattr(bank_account, 'account_name', 'Bestyy Customer')
            account_number = getattr(bank_account, 'account_number', awaiting_order.payment_reference)

            if bank_name and account_name and account_number:
                message += f"🏦 *Bank:* {bank_name}\n"
                message += f"📋 *Account Name:* {account_name}\n"
                message += f"🔢 *Account Number:* {account_number}\n"
                message += f"📝 *Reference:* {awaiting_order.payment_reference}\n\n"
                message += f"💰 *Please transfer ₦{awaiting_order.total_amount:,.0f} to the account above.*\n"
                message += f"📱 *Your order will be confirmed once payment is received.*\n\n"
                message += f"Thank you for choosing Bestyy! 🎉"

                return {
                    'action': 'payment_setup_complete',
                    'order': {
                        'id': awaiting_order.id,
                        'order_number': f"#{awaiting_order.id}",
                        'vendor': awaiting_order.vendor.business_name,
                        'total_amount': float(awaiting_order.total_amount),
                        'delivery_address': awaiting_order.delivery_address,
                        'notes': awaiting_order.notes,
                        'status': awaiting_order.status,
                        'payment_reference': awaiting_order.payment_reference
                    },
                    'message': message
                }
            else:
                return {
                    'action': 'payment_failed',
                    'message': "❌ Payment account setup completed but account details are missing. Please contact support."
                }

        except Exception as e:
            logger.error(f"Error handling order confirmation: {str(e)}")
            return {
                'action': 'confirmation_failed',
                'message': "❌ Sorry, there was an error processing your confirmation. Please try again."
            }

    def _calculate_and_show_order_summary(self, order, user, context, message=None) -> Optional[Dict]:
        """
        Calculate order summary using OrderSummaryView API and show to user for confirmation
        """
        try:
            from django.conf import settings
            import requests

            # Prepare cart items data from order
            cart_items = []
            if hasattr(order, 'order_items') and order.order_items:
                for item in order.order_items.all():
                    cart_items.append({
                        'menu_item_id': item.menu_item.id,
                        'quantity': item.quantity
                    })
            else:
                # Fallback: assume single item from order total
                logger.warning(f"Order {order.id} has no order_items, using fallback calculation")

            # Prepare payload for OrderSummaryView API
            summary_payload = {
                'cart_items': cart_items,
                'delivery_address': order.delivery_address,
                'vendor_id': order.vendor.id
            }

            # Call OrderSummaryView API
            base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
            api_url = f"{base_url}/api/user/order-summary/"

            response = requests.post(api_url, json=summary_payload, timeout=10)

            if response.status_code == 200:
                summary_data = response.json()

                if summary_data.get('success'):
                    summary = summary_data.get('summary', {})
                    delivery_info = summary_data.get('delivery_info', {})
                    items = summary_data.get('items', [])

                    # Update order with calculated fees
                    order.subtotal = Decimal(str(summary.get('subtotal', 0)))
                    order.delivery_fee = Decimal(str(summary.get('delivery_fee', 0)))
                    order.total_amount = Decimal(str(summary.get('grand_total', 0)))
                    order.save()

                    # Format order summary message for user confirmation
                    message = f"📋 *Order Summary - Please Confirm*\n\n"
                    message += f"🏪 *Restaurant:* {delivery_info.get('vendor', {}).get('name', order.vendor.business_name)}\n\n"

                    # List items
                    message += f"🍽️ *Items:*\n"
                    for item in items:
                        message += f"• {item.get('name', 'Item')} x{item.get('quantity', 1)} = ₦{item.get('total', 0):,.0f}\n"

                    # Pricing breakdown
                    message += f"\n💰 *Pricing:*\n"
                    message += f"• Subtotal: ₦{summary.get('subtotal', 0):,.0f}\n"
                    if summary.get('delivery_fee', 0) > 0:
                        message += f"• Delivery Fee: ₦{summary.get('delivery_fee', 0):,.0f}\n"
                    if summary.get('platform_fee', 0) > 0:
                        message += f"• Platform Fee: ₦{summary.get('platform_fee', 0):,.0f}\n"
                    message += f"• *Total: ₦{summary.get('grand_total', 0):,.0f}*\n\n"

                    # Delivery info
                    if delivery_info.get('estimated_time'):
                        message += f"🚀 *Estimated Delivery:* {delivery_info.get('estimated_time', '30-45 minutes')}\n"
                    if delivery_info.get('distance_text'):
                        message += f"📍 *Distance:* {delivery_info.get('distance_text', 'Calculating...')}\n"

                    message += f"\n✅ *Is this order correct?*\n\n"
                    message += f"💬 *Reply 'YES' to confirm and proceed to payment*\n"
                    message += f"💬 *Reply 'NO' to cancel or make changes*\n\n"
                    message += f"Let me know if everything looks good! 👍"

                    return {
                        'action': 'order_summary_shown',
                        'order': {
                            'id': order.id,
                            'vendor': order.vendor.business_name,
                            'total_amount': float(order.total_amount),
                            'delivery_address': order.delivery_address,
                            'notes': order.notes
                        },
                        'message': message
                    }
                else:
                    error_msg = summary_data.get('error', 'Unknown error calculating order summary')
                    logger.error(f"OrderSummaryView API error: {error_msg}")

                    # Fallback: show basic order info and ask for confirmation
                    message = f"📋 *Order Summary*\n\n"
                    message += f"🏪 *Restaurant:* {order.vendor.business_name}\n"
                    message += f"💰 *Total:* ₦{order.total_amount:,.0f}\n"

                    if order.delivery_address:
                        message += f"📍 *Address:* {order.delivery_address}\n"

                    message += f"\n✅ *Ready to proceed to payment?*\n\n"
                    message += f"💬 *Reply 'YES' to continue*\n"
                    message += f"💬 *Reply 'NO' to make changes*\n\n"

                    message += f"There's a small delay calculating exact fees, but your order looks good!"

                    return {
                        'action': 'order_summary_shown_basic',
                        'order': {
                            'id': order.id,
                            'vendor': order.vendor.business_name,
                            'total_amount': float(order.total_amount),
                            'delivery_address': order.delivery_address,
                            'notes': order.notes
                        },
                        'message': message
                    }
            else:
                logger.error(f"OrderSummaryView API request failed: {response.status_code} - {response.text}")

                # Complete fallback
                message = f"📋 *Ready to proceed with your order?*\n\n"
                message += f"🏪 *Restaurant:* {order.vendor.business_name}\n"
                message += f"💰 *Total:* ₦{order.total_amount:,.0f}\n"

                if order.delivery_address:
                    message += f"📍 *Address:* {order.delivery_address}\n"

                message += f"\n✅ *Does this look correct?*\n\n"
                message += f"💬 *Reply 'YES' to confirm and set up payment*\n"
                message += f"💬 *Reply 'NO' to cancel*\n\n"

                return {
                    'action': 'order_summary_fallback',
                    'order': {
                        'id': order.id,
                        'vendor': order.vendor.business_name,
                        'total_amount': float(order.total_amount),
                        'delivery_address': order.delivery_address,
                        'notes': order.notes
                    },
                    'message': message
                }

        except Exception as e:
            logger.error(f"Error calculating order summary: {str(e)}")

            # Emergency fallback
            message = f"📋 *Order Ready*\n\n"
            message += f"🏪 *Restaurant:* {order.vendor.business_name}\n"
            message += f"💰 *Total:* ₦{order.total_amount:,.0f}\n"

            if order.delivery_address:
                message += f"📍 *Address:* {order.delivery_address}\n"

            message += f"\n✅ *Confirm Order?*\n\n"
            message += f"💬 *Reply 'YES' to proceed*\n"

            return {
                'action': 'order_summary_emergency_fallback',
                'order': {
                    'id': order.id,
                    'vendor': order.vendor.business_name if order.vendor else 'Unknown',
                    'total_amount': float(order.total_amount),
                    'delivery_address': order.delivery_address,
                    'notes': order.notes
                },
                'message': message
            }

def handle_special_instructions(self, message_content: str, user, context: Dict, message=None) -> Optional[Dict]:
    """
    Handle special instructions, order summary calculation, and finalize the order

    Args:
        message_content: User's message with special instructions, confirmation, or address
        user: User object
        context: Additional context

    Returns:
        Dict with order finalization response or None
    """
    try:
        content_lower = message_content.lower().strip()

        # Handle order confirmation first (check for "yes" after showing order summary)
        if content_lower in ['yes', 'confirm', 'ok', 'okay', 'sure', 'proceed', 'yes please']:
            return self._handle_order_confirmation(user, context, message)

        # Handle order summary flow - check if order needs address or if address was just provided
        from bestyy.restaurant_features.order.models import Order
        awaiting_order = Order.objects.filter(
            customer=user,
            status__in=['awaiting', 'pending']
        ).order_by('-created_at').first()

        if not awaiting_order:
            return {
                'action': 'no_awaiting_order',
                'message': "❌ No pending order found. Please start a new order."
            }

        # Check if this is a delivery address being provided instead of special instructions
        # REMOVE the awaiting_address check here - just check if it looks like an address
        if looks_like_address(content_lower):
            # Clear the awaiting_address flag since we're processing the address now
            if message and hasattr(message, 'conversation'):
                message.conversation.awaiting_address = False
                message.conversation.save()

            # User is providing address, not special instructions
            awaiting_order.delivery_address = message_content
            awaiting_order.save()
            logger.info(f"Saved delivery address for order {awaiting_order.id}: {message_content}")
            # Fall through to order summary calculation below
        else:
            # Check for negative responses (proceed without special instructions)
            negative_responses = ['no', 'that\'s all', 'thats all', 'nothing', 'no thanks', 'proceed', 'continue']
            has_special_instructions = not any(response in content_lower for response in negative_responses)

            # Update order with special instructions if provided
            if has_special_instructions:
                awaiting_order.notes = message_content
                awaiting_order.save()
                logger.info(f"Saved special instructions for order {awaiting_order.id}: {message_content}")

        # At this point, we have either special instructions saved or we're ready to proceed
        # Check if order needs to be moved to pending status and order summary shown
        if awaiting_order.status == 'awaiting':
            awaiting_order.status = 'pending'
            awaiting_order.save()
            logger.info(f"Moved order {awaiting_order.id} to pending status")

        # Calculate and show order summary before payment
        if awaiting_order.delivery_address:
            return self._calculate_and_show_order_summary(awaiting_order, user, context, message)
        else:
            # No delivery address yet, ask for it
            return {
                'action': 'address_required',
                'message': f"📍 *Almost ready!* Before we proceed to payment, I need your delivery address.\n\n"
                          f"🏠 Please provide your full delivery address:\n\n"
                          f"💡 Example: '123 Lagos Street, Ikeja, Lagos' or 'Victoria Island, Lagos'\n\n"
                          f"🔍 I'll calculate exact delivery fees based on your location!"
            }

    except Exception as e:
        logger.error(f"Error handling special instructions: {str(e)}")
        return None

    def _handle_specific_vendor_request(self, message_content: str, user, context: Dict) -> Optional[Dict]:
        """
        Handle requests that specify both food and vendor (e.g., "I want egusi from Mama's Kitchen")

        Args:
            message_content: The user's message
            user: User object
            context: Additional context

        Returns:
            Dict with direct ordering response, or None if not a specific vendor request
        """
        try:
            content_lower = message_content.lower()

            # Check for vendor-specific keywords
            vendor_indicators = ['from', 'at', 'by', 'restaurant', 'place', 'shop']

            vendor_name = None
            food_type = None

            # Extract vendor name and food type
            for indicator in vendor_indicators:
                if indicator in content_lower:
                    parts = content_lower.split(indicator, 1)
                    if len(parts) == 2:
                        # First part should contain food, second part vendor
                        food_part = parts[0].strip()
                        vendor_part = parts[1].strip()

                        # Extract food type
                        nigerian_dish = find_nigerian_dish(food_part)
                        if nigerian_dish:
                            food_type = nigerian_dish
                        else:
                            food_keywords = [
                                'pizza', 'burger', 'chicken', 'rice', 'pasta', 'soup', 'salad',
                                'sandwich', 'noodles', 'sushi', 'steak', 'fish', 'beef', 'pork',
                                'vegetarian', 'vegan', 'chinese', 'indian', 'mexican', 'thai',
                                'italian', 'african', 'shawarma'
                            ]
                            for keyword in food_keywords:
                                if keyword in food_part:
                                    food_type = keyword
                                    break

                        # Extract vendor name (clean it up)
                        vendor_name = vendor_part.strip()
                        # Remove common words
                        vendor_name = vendor_name.replace('the', '').replace('restaurant', '').replace('place', '').strip()

                        if food_type and vendor_name:
                            break

            if not food_type or not vendor_name:
                return None

            logger.info(f"Detected specific vendor request: {food_type} from {vendor_name}")

            # Search for the specific vendor
            from bestyy.core_features.user.models import VendorProfile
            vendor = VendorProfile.objects.filter(
                business_name__icontains=vendor_name,
                verification_status='approved',
                is_suspended=False
            ).first()

            if not vendor:
                return {
                    'message': f"Sorry, I couldn't find a restaurant named '{vendor_name}'. Let me show you available options for {food_type} instead.",
                    'action': 'vendor_not_found'
                }

            # Check if vendor serves the requested food
            menu_items = self.order_service.search_vendors_by_food(food_type, vendor_ids=[vendor.id])

            if not menu_items.get('success') or not menu_items.get('vendors'):
                return {
                    'message': f"Sorry, {vendor.business_name} doesn't seem to serve {food_type} right now. Let me show you other restaurants that do.",
                    'action': 'food_not_available'
                }

            vendor_data = menu_items['vendors'][0]
            menu_items_list = vendor_data.get('menu_items', [])

            if not menu_items_list:
                return {
                    'message': f"Sorry, {vendor.business_name} doesn't have {food_type} available right now.",
                    'action': 'no_menu_items'
                }

            # Create awaiting order directly for this vendor
            items_data = []
            for item in menu_items_list[:3]:  # Take first 3 items
                items_data.append({
                    'menu_item_id': item['id'],
                    'quantity': 1
                })

            order_result = self.order_service.create_awaiting_order_from_whatsapp(
                user=user,
                vendor_id=vendor.id,
                items_data=items_data
            )

            if order_result.get('success'):
                # Send food images for this specific vendor
                images_sent = 0
                for item in menu_items_list[:3]:  # Send up to 3 images
                    item_picture = item.get('picture')
                    if item_picture and images_sent < 3:
                        item_name = item.get('name', 'Menu Item')
                        item_price = item.get('price', 0)
                        caption = f"🏪 *{vendor.business_name}*\n📸 {item_name}\n💰 ₦{item_price:,.0f}"

                        image_result = self.send_menu_item_image(
                            phone_number=context.get('phone_number', ''),
                            image_url=item_picture,
                            caption=caption
                        )

                        if image_result.get('success'):
                            images_sent += 1
                            logger.info(f"Sent image for {item_name} from {vendor.business_name}")

                # Format response for direct ordering
                greeting = context.get('casual_greeting', 'Perfect')
                order_data = order_result['order']
                message = f"🍽️ *{greeting}! I've found {food_type} at {vendor.business_name}*\n\n"
                message += f"📋 *Your Order:*\n"
                message += f"• {food_type.title()} - ₦{order_data['total_amount']:,.0f}\n"
                message += f"💰 *Total: ₦{order_data['total_amount']:,.0f}*\n\n"
                message += f"❓ *Is that all?* Do you want to add anything else or do you have any special instructions for the vendor?\n\n"
                message += f"💬 *Reply with:*\n"
                message += f"• Your special instructions (if any)\n"
                message += f"• 'No' or 'That's all' to proceed\n"
                message += f"• 'Add [item name]' to add more items\n\n"
                message += f"Let me know how I can make this perfect for you! 💕"

                return {
                    'message': message,
                    'action': 'direct_vendor_order',
                    'vendor': vendor.business_name,
                    'food_type': food_type,
                    'order_id': order_data['id']
                }

            return None

        except Exception as e:
            logger.error(f"Error handling specific vendor request: {str(e)}")
            return None

    def _handle_order_request(self, message_content: str, category: str, user, context: Dict) -> Optional[Dict]:
        """
        Handle order requests by searching for vendors and preparing order data
        Uses Nigerian dishes knowledge base for better recognition

        Args:
            message_content: The user's message
            category: Message category
            user: User object
            context: Additional context

        Returns:
            Dict with vendor options and order data, or None if no vendors found
        """
        try:
            logger.info(f"_handle_order_request called with category: {category}, message: {message_content}")
            food_type = None

            # First, check if it's a Nigerian dish
            nigerian_dish = find_nigerian_dish(message_content)
            if nigerian_dish:
                food_type = nigerian_dish
                logger.info(f"Detected Nigerian dish: {food_type}")
            else:
                # Fall back to keyword matching for other foods
                food_keywords = [
                    'pizza', 'burger', 'chicken', 'rice', 'pasta', 'soup', 'salad',
                    'sandwich', 'noodles', 'sushi', 'steak', 'fish', 'beef', 'pork',
                    'vegetarian', 'vegan', 'chinese', 'indian', 'mexican', 'thai',
                    'italian', 'african', 'shawarma'
                ]

                for keyword in food_keywords:
                    if keyword.lower() in message_content.lower():
                        food_type = keyword
                        logger.info(f"Detected food keyword: {food_type}")
                        break

            if not food_type:
                logger.warning(f"No food type detected in message: {message_content}")
                return None

            # Search for vendors
            logger.info(f"Searching for vendors serving: {food_type}")
            vendor_result = self.order_service.search_vendors_by_food(food_type, limit=3)
            logger.info(f"Vendor search result: success={vendor_result.get('success')}, count={vendor_result.get('count')}")

            if vendor_result.get('success') and vendor_result.get('vendors'):
                logger.info(f"Found {len(vendor_result['vendors'])} vendors for {food_type}")
                return {
                    'action': 'show_vendors',
                    'food_type': food_type,
                    'vendors': vendor_result['vendors'],
                    'message': f"Found {len(vendor_result['vendors'])} restaurants serving {food_type}. Which would you like to order from?"
                }

            logger.warning(f"No vendors found for food type: {food_type}")
            return None

        except Exception as e:
            logger.error(f"Error handling order request: {str(e)}", exc_info=True)
            return None

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

    def _try_smart_recommendations(self, message_content: str, context: Dict) -> Optional[str]:
        """
        Try to get smart recommendations from the API instead of explaining
        """
        try:
            from django.urls import reverse
            from django.test import RequestFactory
            from bestyy.core_features.user.api.smart_recommendations import SmartItemRecommendationsView

            # Create a mock request
            factory = RequestFactory()
            request = factory.get('/api/smart-recommendations/', {
                'item': message_content.strip(),
                'budget': context.get('budget')
            })

            # Create view instance and call get method
            view = SmartItemRecommendationsView()
            response = view.get(request)

            if response.status_code == 200:
                data = response.data
                if data.get('found') is False and data.get('recommendations'):
                    # We found smart alternatives - format them directly
                    return self._format_smart_recommendations_response(data)
                elif data.get('found') is True:
                    # Exact match found - format direct ordering response
                    return self._format_exact_match_response(data)

            return None

        except Exception as e:
            logger.error(f"Error trying smart recommendations: {str(e)}")
            return None

    def _format_smart_recommendations_response(self, data: Dict) -> str:
        """
        Format smart recommendations response for WhatsApp
        """
        message = data.get('message', '')
        recommendations = data.get('recommendations', [])

        if not recommendations:
            return message

        # Add formatted recommendations with images
        formatted_message = f"{message}\n\n"

        for i, rec in enumerate(recommendations[:3], 1):  # Show top 3
            name = rec.get('name', 'Unknown Item')
            price = rec.get('price', 0)
            vendor_name = rec.get('vendor_name', 'Unknown Vendor')
            reason = rec.get('reason', '')

            formatted_message += f"*{i}. {name}*\n"
            formatted_message += f"🏪 {vendor_name}\n"
            formatted_message += f"💰 ₦{price:,.0f}\n"
            if reason:
                formatted_message += f"ℹ️ {reason}\n"
            formatted_message += "\n"

        formatted_message += "👉 *Reply with the number (1, 2, or 3) to order*"

        return formatted_message

    def _format_exact_match_response(self, data: Dict) -> str:
        """
        Format exact match response for direct ordering
        """
        message = data.get('message', '')
        recommendations = data.get('recommendations', [])

        if recommendations:
            rec = recommendations[0]  # Take first match
            formatted_message = f"✅ *Found it!*\n\n"
            formatted_message += f"🏪 *{rec.get('vendor_name', 'Restaurant')}*\n"
            formatted_message += f"📋 *{rec.get('name', 'Item')}*\n"
            formatted_message += f"💰 ₦{rec.get('price', 0):,.0f}\n\n"
            formatted_message += "🍽️ *Ready to order?*\n\n"
            formatted_message += "👉 *Reply 'yes' to place this order*"

            return formatted_message

        return message
