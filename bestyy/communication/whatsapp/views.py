from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Avg
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, JsonResponse
from datetime import timedelta
import json
import logging
import os

from .models import (
    WhatsAppConversation, 
    WhatsAppMessage, 
    AIResponseTemplate, 
    AIProcessingLog,
    WhatsAppWebhookLog
)
from .serializers import (
    WhatsAppConversationSerializer,
    WhatsAppMessageSerializer,
    WhatsAppMessageCreateSerializer,
    AIResponseTemplateSerializer,
    AIProcessingLogSerializer,
    WhatsAppWebhookLogSerializer,
    WhatsAppWebhookSerializer,
    AIResponseRequestSerializer,
    WhatsAppSendMessageSerializer,
    ConversationStatsSerializer
)
from .ai_service import WhatsAppAIService

logger = logging.getLogger(__name__)


def _get_food_restaurants_text(food_type):
    """Get text description of restaurants that serve a specific food type - BACKEND DATA ONLY"""
    try:
        # Try to call the vendor search API for restaurants serving this food type
        import requests

        # Call the vendor search API
        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
        api_url = f"{base_url}/api/user/search/vendors/"

        response = requests.get(api_url, params={
            'cuisine': food_type,
            'page_size': 3
        }, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('vendors'):
                vendors = data['vendors']
                if vendors:
                    emoji = _get_food_emoji(food_type)
                    message = f"{emoji} Here are some great {food_type} restaurants:\n\n"

                    for i, vendor in enumerate(vendors[:3], 1):
                        name = vendor.get('business_name', 'Restaurant')
                        rating = vendor.get('rating', 0)
                        delivery_time = vendor.get('delivery_time', '30-45 min')

                        message += f"{i}. {name} "
                        if rating > 0:
                            message += f"⭐ {rating}/5 "
                        message += f"({delivery_time})\n"

                    message += f"\nWhich restaurant would you like to order {food_type} from? Just tell me the number!"
                    return message

        # NO FALLBACK - if no restaurants found, tell user we don't have it
        return _get_no_food_available_message(food_type)

    except Exception as e:
        logger.error(f"Error getting {food_type} restaurants: {str(e)}")
        # NO FALLBACK - tell user we don't have it
        return _get_no_food_available_message(food_type)


def _get_food_emoji(food_type):
    """Get emoji for different food types"""
    food_emojis = {
        'pizza': '🍕',
        'burger': '🍔',
        'chicken': '🍗',
        'rice': '🍚',
        'pasta': '🍝',
        'soup': '🍲',
        'salad': '🥗',
        'sandwich': '🥪',
        'noodles': '🍜',
        'sushi': '🍱',
        'steak': '🥩',
        'fish': '🐟',
        'beef': '🥩',
        'pork': '🥩',
        'vegetarian': '🥬',
        'vegan': '🌱',
    }
    return food_emojis.get(food_type.lower(), '🍽️')


# REMOVED: _get_fallback_restaurants function - we only show real backend data


@csrf_exempt
def whatsapp_webhook(request):
    """
    WhatsApp webhook endpoint for receiving messages and status updates
    Simple, robust implementation that handles Meta's requirements
    """
    
    # Handle GET request (Webhook verification)
    if request.method == "GET":
        print(f"=== WHATSAPP WEBHOOK VERIFICATION ===")
        print(f"Request method: {request.method}")
        print(f"All GET parameters: {dict(request.GET)}")
        
        # Get parameters - Meta sends them with dots
        mode = request.GET.get('hub.mode', '')
        token = request.GET.get('hub.verify_token', '')
        challenge = request.GET.get('hub.challenge', '')
        
        print(f"Mode: '{mode}'")
        print(f"Token: '{token}'")
        print(f"Challenge: '{challenge}'")
        
        # Get expected token from environment
        expected_token = getattr(settings, 'WHATSAPP_VERIFY_TOKEN', '')
        print(f"Expected token: '{expected_token}'")
        
        # Check if we have the required parameters
        if not challenge:
            print("ERROR: Missing hub.challenge parameter")
            return HttpResponse("Missing challenge parameter", status=400)
        
        if not expected_token:
            print("ERROR: WHATSAPP_VERIFY_TOKEN not configured in settings")
            return HttpResponse("Server configuration error", status=500)
        
        # Verify the webhook
        if mode == 'subscribe' and token == expected_token:
            print("SUCCESS: Webhook verified!")
            return HttpResponse(challenge, content_type='text/plain')
        else:
            print(f"FAILED: mode='{mode}' (expected 'subscribe'), token match: {token == expected_token}")
            return HttpResponse("Forbidden", status=403)
    
    # Handle POST request (Incoming messages/status updates)
    elif request.method == "POST":
        print(f"=== WHATSAPP WEBHOOK POST ===")
        try:
            # Parse JSON body
            body = json.loads(request.body.decode('utf-8'))
            print(f"Received webhook data: {json.dumps(body, indent=2)}")
            
            # Process the webhook and send response
            process_result = _process_webhook(body, request)
            if isinstance(process_result, dict):
                return JsonResponse(process_result, status=200 if process_result.get('success', True) else 500)
            return JsonResponse({'status': 'processed'}, status=200)
            
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON: {str(e)}")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f"ERROR: {str(e)}")
            return JsonResponse({'error': 'Internal server error'}, status=500)
    
    # Handle other methods
    else:
        print(f"ERROR: Unsupported method: {request.method}")
        return HttpResponse("Method not allowed", status=405)
    
def _process_webhook(data, request=None):
    """Process WhatsApp webhook data"""
    try:
        # Process Meta WhatsApp Business API webhook
        return _process_whatsapp_business_webhook(data, request)

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'processing_time': 0
        }


def _process_whatsapp_business_webhook(data, request):
    """Process WhatsApp Business API webhook"""
    try:
        # Validate the webhook payload using SHA256 signature
        # Skip validation in development if META_APP_SECRET is not set
        meta_app_secret = getattr(settings, 'META_APP_SECRET', '')
        if meta_app_secret:
            if not _validate_meta_signature(request):
                logger.warning("Invalid Meta webhook signature")
                return {
                    'success': False,
                    'error': 'Invalid signature',
                    'processing_time': 0
                }
        else:
            logger.warning("META_APP_SECRET not configured - skipping signature validation (development mode)")

        # Process each entry in the webhook
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                if change.get('field') == 'messages':
                    value = change.get('value', {})
                    messages = value.get('messages', [])

                    for message in messages:
                        _process_meta_message(message, value)

        return {
            'success': True,
            'message': 'WhatsApp Business webhook processed successfully',
            'processing_time': 0
        }

    except Exception as e:
        logger.error(f"Error processing WhatsApp Business webhook: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'processing_time': 0
        }

def _validate_meta_signature(request):
    """Validate Meta webhook signature using SHA256"""
    import hmac
    import hashlib

    signature = request.META.get('HTTP_X_HUB_SIGNATURE_256', '')
    if not signature.startswith('sha256='):
        return False

    expected_signature = signature[7:]  # Remove 'sha256=' prefix
    app_secret = getattr(settings, 'META_APP_SECRET', '')

    if not app_secret:
        logger.warning("META_APP_SECRET not configured")
        return False

    # Get raw body
    body = request.body.decode('utf-8')

    # Calculate expected signature
    calculated_signature = hmac.new(
        app_secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, calculated_signature)

def _process_meta_message(message, value):
    """Enhanced: Process Meta WhatsApp message with robust onboarding state and polite chatbot flow."""
    from .services.meta_whatsapp_service import MetaWhatsAppService
    from django.contrib.auth import get_user_model
    from django.conf import settings
    import os
    print("[WEBHOOK DEBUG] WHATSAPP_ACCESS_TOKEN (from settings):", getattr(settings, 'WHATSAPP_ACCESS_TOKEN', 'NOT SET'))
    User = get_user_model()
    WEB_SIGNUP_URL = "https://bestyy.com/onboard"

    try:
        message_type = message.get('type')
        from_number = message.get('from')
        message_id = message.get('id')
        timestamp = message.get('timestamp')

        # Contact & content
        contacts = value.get('contacts', [])
        contact_name = contacts[0].get('profile', {}).get('name', '') if contacts else ''
        content = message.get('text', {}).get('body', '').strip() if message_type == 'text' else "[Non-text message]"

        # CONVERSATION: Create/get, prepare state
        conversation, _ = WhatsAppConversation.objects.get_or_create(
            phone_number=from_number,
            defaults={
                'is_active': True,
            }
        )

        # Link user if unknown but matches by phone (robustify)
        if not conversation.user:
            user = User.objects.filter(phone__icontains=from_number.replace('+','').replace('-','').replace(' ','')).first()
            if user:
                conversation.user = user
            conversation.save()

        user_obj = conversation.user
        user_role = None
        if user_obj:
            user_role = getattr(user_obj, 'role', None)

        meta_service = MetaWhatsAppService()
        polite_wait = "Thank you for your patience. "

        # --- VENDOR/COURIER branch: never chat-onboard, always reply politely with web signup url ---
        if (user_role in ['vendor','courier']) or (content.lower() in ['signup vendor','signup courier']):
            reply = (
                f"Hello! For vendors and couriers, we require proper verification. "
                f"Kindly complete your sign-up at our website: {WEB_SIGNUP_URL}\n"
                "Once verified, you'll receive updates & codes directly here."
            )
            meta_service.send_message(to=from_number, message=reply)
            return

        # --- VENDOR/COURIER receiving order/code - skip conversational flow, allow normal code delivery ---
        if user_role in ['vendor','courier'] and content.startswith('[CODE]'):
            return  # Let external logic deliver code, do NOT chatbot/onboard

        # --- VENDOR/COURIER CODE VERIFICATION COMMANDS ---
        if user_role in ['vendor', 'courier']:
            # Handle pickup code verification for vendors
            if user_role == 'vendor' and content.strip().isdigit() and len(content.strip()) == 6:
                code = content.strip()
                # Check if this vendor has any orders with this pickup code
                from bestyy.core_features.user.models import Order
                try:
                    order = Order.objects.filter(
                        vendor__user=user_obj,
                        pickup_code=code,
                        pickup_code_verified=False
                    ).first()

                    if order:
                        # Verify the pickup code
                        if order.verify_pickup_code(code):
                            # Trigger vendor payout
                            payout_success = order.trigger_vendor_payout()

                            reply = (
                                f"✅ Pickup code verified successfully!\n\n"
                                f"Order #{order.id} - {order.order_name}\n"
                                f"Amount: ₦{order.vendor_payout_amount}\n"
                                f"Payout: {'✅ Initiated' if payout_success else '⏳ Processing'}\n\n"
                                f"Thank you for your service! The courier has picked up the order."
                            )
                        else:
                            reply = "❌ Invalid pickup code. Please check the code and try again."
                    else:
                        reply = "❌ No matching order found for this pickup code."

                    meta_service.send_message(to=from_number, message=reply)
                    return

                except Exception as e:
                    logger.error(f"Error verifying pickup code for vendor {user_obj}: {str(e)}")
                    reply = "❌ Error processing pickup code. Please try again or contact support."
                    meta_service.send_message(to=from_number, message=reply)
                    return

            # Handle delivery OTP verification for couriers
            elif user_role == 'courier' and content.strip().isdigit() and len(content.strip()) == 6:
                otp = content.strip()
                # Check if this courier has any orders with this delivery OTP
                from bestyy.core_features.user.models import Order
                try:
                    order = Order.objects.filter(
                        courier__user=user_obj,
                        delivery_otp=otp,
                        delivery_otp_verified=False
                    ).first()

                    if order:
                        # Verify the delivery OTP
                        if order.verify_delivery_otp(otp):
                            # Mark order as delivered and trigger courier payout
                            order.mark_as_delivered()
                            payout_success = order.trigger_courier_payout()

                            reply = (
                                f"✅ Delivery OTP verified successfully!\n\n"
                                f"Order #{order.id} - {order.order_name}\n"
                                f"Amount: ₦{order.courier_payout_amount}\n"
                                f"Payout: {'✅ Initiated' if payout_success else '⏳ Processing'}\n\n"
                                f"Thank you for your service! The order has been marked as delivered."
                            )
                        else:
                            reply = "❌ Invalid delivery OTP. Please check the code and try again."
                    else:
                        reply = "❌ No matching order found for this delivery OTP."

                    meta_service.send_message(to=from_number, message=reply)
                    return

                except Exception as e:
                    logger.error(f"Error verifying delivery OTP for courier {user_obj}: {str(e)}")
                    reply = "❌ Error processing delivery OTP. Please try again or contact support."
                    meta_service.send_message(to=from_number, message=reply)
                    return

            # Handle help commands for vendors/couriers
            elif content.lower().strip() in ['help', 'commands', 'what can i do', 'menu']:
                if user_role == 'vendor':
                    reply = (
                        "🏪 Vendor Commands:\n\n"
                        "• Enter 6-digit pickup codes to verify order pickup\n"
                        "• Example: 123456\n\n"
                        "When a courier arrives to pick up an order, they'll give you a code. "
                        "Enter it here to confirm pickup and receive payment.\n\n"
                        "Need help? Contact support."
                    )
                else:  # courier
                    reply = (
                        "🚴 Courier Commands:\n\n"
                        "• Enter 6-digit delivery OTPs to verify order delivery\n"
                        "• Example: 789012\n\n"
                        "When you deliver an order, ask the customer for the OTP shown in their app. "
                        "Enter it here to confirm delivery and receive payment.\n\n"
                        "Need help? Contact support."
                    )

                meta_service.send_message(to=from_number, message=reply)
                return

        # --- SIGNUP VERIFICATION - Check for signup verification codes ---
        # This handles verification codes sent during signup process
        if content.strip().isdigit() and len(content.strip()) == 6:
            code = content.strip()
            # Check if this matches any pending user verification codes
            from bestyy.core_features.user.models import PendingUser
            try:
                pending_user = PendingUser.objects.get(
                    verification_code=code,
                    phone=from_number,
                    is_verified=False
                )

                if not pending_user.is_expired:
                    # Verify the user and create account
                    user, message = pending_user.create_user_account()

                    if user:
                        reply = f"""✅ Welcome {user.first_name}!

Your {pending_user.user_type} account has been created successfully!

You can now log in to your dashboard and start using Bestyy.

Best regards,
Bestyy Team"""
                    else:
                        reply = "❌ Account creation failed. Please contact support."
                else:
                    reply = "❌ Verification code expired. Please start signup again."

                meta_service.send_message(to=from_number, message=reply)
                return

            except PendingUser.DoesNotExist:
                # Not a signup verification code, continue with normal flow
                pass
            except Exception as e:
                logger.error(f"Error processing signup verification: {str(e)}")
                reply = "❌ Error processing verification. Please try again."
                meta_service.send_message(to=from_number, message=reply)
                return

        # --- CUSTOMER CHATBOT CONVERSATIONAL FLOW (ONBOARDING FSM) ---
        state = conversation.onboarding_state

        # - Not onboarded and no state yet: Check if greeting or ask for email
        # If user exists but state is not 'onboarded', treat as returning user
        if user_obj and state != 'onboarded':
            conversation.onboarding_state = 'onboarded'
            conversation.save()
            state = 'onboarded'

        if not user_obj and not state:
            # Check if this is an email first
            import re
            email_match = re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", content)
            if email_match:
                # Set state to awaiting_email so the email processing logic below will handle it
                conversation.onboarding_state = 'awaiting_email'
                conversation.save()
                # Continue to process as if we're in awaiting_email state
                pass  # Fall through to the awaiting_email logic
            else:
                # Check if this is a greeting
                greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings']
                if content.lower().strip() in greeting_words or any(word in content.lower() for word in greeting_words):
                    conversation.onboarding_state = 'awaiting_email'
                    conversation.save()
                    reply = (
                        f"Hello there! 👋 Welcome to Bestyy! We're thrilled to have you here.\n\n"
                        f"I can see this is a new number for us. To get you all set up and provide you with the best service, "
                        f"could you please kindly share your email address with us?\n\n"
                        f"This will help us create your account and ensure seamless communication. "
                        f"If you've used Bestyy before, please use the same email address you registered with."
                    )
                    meta_service.send_message(to=from_number, message=reply)
                    return
                else:
                    # Not a greeting, ask what they need
                    conversation.onboarding_state = 'awaiting_email'
                    conversation.save()
                    reply = (
                        f"Hello! Welcome to Bestyy! 👋\n\n"
                        f"I don't recognize this number, so you might be a new user. "
                        f"To help you get started, could you please provide your email address? "
                        f"This will allow us to set up your account and serve you better."
                    )
                    meta_service.send_message(to=from_number, message=reply)
                    return

        # - Awaiting email: check if email provided, look up, branch for linking if needed
        if state == 'awaiting_email' or (not user_obj and conversation.onboarding_state == 'awaiting_email'):
            import re
            email_match = re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", content)
            if email_match:
                email = content
                existing = User.objects.filter(email=email).first()
                if existing and (not existing.phone or from_number not in existing.phone):
                    # Need confirmation to link WhatsApp to this email (different phone)
                    conversation.pending_email = email
                    conversation.onboarding_state = 'awaiting_link_confirmation'
                    conversation.pending_link_action = 'email'
                    conversation.save()
                    reply = (
                        f"Thank you! We noticed this email is already registered. "
                        "If this is your account, reply YES to link this WhatsApp number to it. "
                        "If not, kindly provide a different email address."
                    )
                    meta_service.send_message(to=from_number, message=reply)
                    return
                elif existing:
                    # Same email/phone: just welcome back
                    conversation.user = existing
                    conversation.onboarding_state = 'onboarded'
                    conversation.save()
                    reply = (
                        "Welcome back to Bestyy! You're all set—how can we help you today? 🍔"
                    )
                    meta_service.send_message(to=from_number, message=reply)
                    return
                else:
                    # New user: proceed with account creation and notify
                    import secrets
                    from bestyy.core_features.user.serializers.user_serializers import UserRegistrationSerializer
                    from django.core.mail import send_mail
                    from django.conf import settings
                    password = secrets.token_urlsafe(8)
                    signup_data = {
                        'email': email,
                        'first_name': contact_name.split()[0] if contact_name else 'WhatsApp',
                        'last_name': ' '.join(contact_name.split()[1:]) if contact_name and len(contact_name.split()) > 1 else 'User',
                        'phone': from_number,
                        'role': 'user',
                        'password': password,
                        'confirm_password': password,
                    }
                    serializer = UserRegistrationSerializer(data=signup_data)
                    if serializer.is_valid():
                        user = serializer.save()
                        conversation.user = user
                        conversation.onboarding_state = 'onboarded'
                        conversation.save()
                        # Send HTML welcome email using template
                        base_url = getattr(settings, 'BASE_URL', 'https://bestyy.com')
                        logo_url = f"{base_url}/static/logo.png"
                        subject = "Welcome to Bestyy - Your Account Details"
                        html_message = f"""
                            <html><body style='font-family: Nunito Sans, Arial, sans-serif; background: #fafbfc; max-width: 640px; margin: auto;'>
                                <div style='background: linear-gradient(90deg, #23C7B2 0%, #25AC9B 100%); padding: 24px 0; text-align: center; color: #fff;'>
                                    <img src='{logo_url}' alt='Bestyy' style='max-width: 84px; border-radius: 10px;'><br>
                                    <h1>Welcome to Bestyy!</h1>
                                </div>
                                <div style='background: #fff; border-radius: 12px; margin: 32px 0; padding: 32px;'>
                                    <p style='font-size: 18px;'>Hello {signup_data['first_name']},</p>
                                    <p>We're excited to have you! Here are your account details for Bestyy:</p>
                                    <ul>
                                        <li><strong>Email:</strong> {email}</li>
                                        <li><strong>Temporary Password:</strong> {password}</li>
                                    </ul>
                                    <p>You can update your password anytime in your profile settings.</p>
                                    <p>If you did not request this, please ignore this email. </p>
                                    <div style='margin: 32px 0 0; color: #666;'>Thank you for joining Bestyy!<br>— The Bestyy Team</div>
                                </div>
                                <footer style='text-align: center; color: #999; font-size: 12px; margin-top: 24px;'>Bestyy &copy; 2025</footer>
                            </body></html>
                        """
                        send_mail(
                            subject=subject,
                            message=f"Welcome! Your login is {email}. Your password: {password}.",
                            html_message=html_message,
                            from_email=getattr(settings,'DEFAULT_FROM_EMAIL', 'noreply@bestyy.com'),
                            recipient_list=[email],
                            fail_silently=False
                        )
                        reply = (
                            f"Thank you for providing your email! Your Bestyy account is now ready. "
                            "We've sent your login details and password to your email. "
                            "You can now place orders and enjoy Bestyy. Please check your inbox!"
                        )
                        meta_service.send_message(to=from_number, message=reply)
                    else:
                        reply = (
                            f"Sorry, we couldn't create your account: {serializer.errors}. Please try again later or contact support."
                        )
                        meta_service.send_message(to=from_number, message=reply)
                    return
            else:
                # Check if this is a greeting - if so, acknowledge and remind about email
                greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings']
                if content.lower().strip() in greeting_words or any(word in content.lower() for word in greeting_words):
                    reply = (
                        f"Hello again! 👋 Nice to hear from you.\n\n"
                        f"To continue setting up your Bestyy account, please share your email address with us. "
                        f"This will help us create your account and get you started!"
                    )
                    meta_service.send_message(to=from_number, message=reply)
                    return

                # Not a valid email; prompt again politely
                reply = (
                    "That doesn't look like a valid email address. "
                    "Would you please resend your email so we can continue?"
                )
                meta_service.send_message(to=from_number, message=reply)
                return

        if state == 'awaiting_link_confirmation':
            if content.lower().strip() == 'yes':
                email = conversation.pending_email
                existing = User.objects.filter(email=email).first()
                if existing:
                    # Link WhatsApp number to this account
                    existing.phone = from_number
                    existing.save()
                    conversation.user = existing
                    conversation.onboarding_state = 'onboarded'
                    conversation.save()
                    # Send confirmation email about linking number
                    from django.core.mail import send_mail
                    from django.conf import settings
                    base_url = getattr(settings, 'BASE_URL', 'https://bestyy.com')
                    logo_url = f"{base_url}/static/logo.png"
                    subject = "Bestyy Account Now Linked to WhatsApp"
                    html_message = f"""
                        <html><body style='font-family: Nunito Sans, Arial, sans-serif; background: #fafbfc; max-width: 640px; margin: auto;'>
                            <div style='background: linear-gradient(90deg, #23C7B2 0%, #25AC9B 100%); padding: 24px 0; text-align: center; color: #fff;'>
                                <img src='{logo_url}' alt='Bestyy' style='max-width: 84px; border-radius: 10px;'><br>
                                <h1>Your WhatsApp Number Linked!</h1>
                            </div>
                            <div style='background: #fff; border-radius: 12px; margin: 32px 0; padding: 32px;'>
                                <p style='font-size: 18px;'>Hello,</p>
                                <p>Your WhatsApp number {from_number} is now linked to your Bestyy account ({email}). </p>
                                <p>You can conveniently place orders and receive notifications through WhatsApp!</p>
                                <div style='margin: 32px 0 0; color: #666;'>Thank you for using Bestyy!<br>— The Bestyy Team</div>
                            </div>
                            <footer style='text-align: center; color: #999; font-size: 12px; margin-top: 24px;'>Bestyy &copy; 2025</footer>
                        </body></html>
                    """
                    send_mail(
                        subject=subject,
                        message=f"Your WhatsApp number ({from_number}) is now linked to your Bestyy account.",
                        html_message=html_message,
                        from_email=getattr(settings,'DEFAULT_FROM_EMAIL', 'noreply@bestyy.com'),
                        recipient_list=[email],
                        fail_silently=False
                    )
                    reply = (
                        f"Wonderful! Your WhatsApp number is now linked to your Bestyy account. You’re all set. How may we assist you today?"
                    )
                    meta_service.send_message(to=from_number, message=reply)
                    return
            else:
                reply = (
                    "No worries! If that's not your account, please reply with your best email to register."
                )
                meta_service.send_message(to=from_number, message=reply)
                return

        # Already onboarded or returning user (customer role); smart intent detection
        # Also check if conversation has a user linked (safety check)
        if state == 'onboarded' or user_obj or conversation.user:
            # SMART INTENT DETECTION: Check for direct food ordering requests
            food_intent = _detect_food_ordering_intent(content)
            if food_intent:
                try:
                    # Direct API call to get recommendations for the specific food type
                    recommendation_message = _get_food_recommendations_with_api(food_intent, user_obj)
                    meta_service.send_message(to=from_number, message=recommendation_message)
                    return
                except Exception as e:
                    logger.error(f"Error getting food recommendations for {food_intent}: {str(e)}")
                    # Fallback to generic food message
                    fallback_message = _get_food_restaurants_text(food_intent)
                    meta_service.send_message(to=from_number, message=fallback_message)
                    return

            # For non-food ordering messages, use normal AI service
            try:
                ai_service = WhatsAppAIService()
                whatsapp_message = WhatsAppMessage.objects.create(
                    conversation=conversation,
                    message_id=message_id,
                    message_type='text',
                    content=content,
                    direction='inbound',
                    timestamp=timezone.now()
                )

                # Ensure user is linked to conversation if not already
                if not conversation.user and user_obj:
                    conversation.user = user_obj
                    conversation.save()

                ai_response = ai_service.process_message(whatsapp_message, context={'user_exists': True})
                if ai_response.get('success'):
                    meta_service.send_message(
                        to=from_number,
                        message=ai_response['response']
                    )
                else:
                    # AI service failed, send helpful fallback message based on message content
                    logger.error(f"AI service failed for user {user_obj}: {ai_response.get('error', 'Unknown error')}")

                    # Provide contextual fallback responses
                    fallback_message = _get_contextual_fallback_message(content)
                    meta_service.send_message(to=from_number, message=fallback_message)
            except Exception as e:
                logger.error(f"Error processing message for onboarded user {user_obj}: {str(e)}")
                fallback_message = _get_contextual_fallback_message(content)
                meta_service.send_message(to=from_number, message=fallback_message)
            return

        # Unexpected fallback
        reply = "Thank you for reaching out! How may we help you today?"
        meta_service.send_message(to=from_number, message=reply)
        return

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        try:
            # Provide contextual fallback response even for general errors
            # Check for specific food types and provide restaurant recommendations
            food_keywords = ['pizza', 'burger', 'chicken', 'rice', 'pasta', 'soup', 'salad', 'sandwich', 'noodles', 'sushi', 'steak', 'fish', 'beef', 'pork', 'vegetarian', 'vegan']
            for food in food_keywords:
                if food in content.lower():
                    error_message = _get_food_restaurants_text(food)
                    break
            else:
                # No specific food type found, use generic responses
                if 'order' in content.lower():
                    error_message = "I'd be happy to help you place an order! Could you please tell me what you'd like to order?"
                elif 'menu' in content.lower() or 'food' in content.lower():
                    error_message = "I can help you with our menu! What type of food are you interested in?"
                elif any(word in content.lower() for word in ['hello', 'hi', 'hey']):
                    error_message = "Hello! Welcome to Bestyy! How can I assist you today?"
                else:
                    error_message = "Thanks for your message! I'm here to help with food delivery and orders. What can I do for you?"

            meta_service.send_message(to=from_number, message=error_message)
        except Exception:
            pass


def _check_and_auto_signup_user(phone_number, contact_name):
    """
    Check if user exists by phone number, and auto-signup if they say 'hi' and don't exist.
    Returns the user object if found/created, None otherwise.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # Clean phone number for lookup
    clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')

    # Try to find existing user by phone
    user = None
    try:
        user = User.objects.filter(phone__icontains=clean_phone).first()
    except:
        pass

    return user


def _auto_signup_user(phone_number, contact_name):
    """
    Auto-signup a user with just phone number and optional name.
    Creates a user account with no password required.
    """
    from django.contrib.auth import get_user_model
    from bestyy.core_features.user.serializers.user_serializers import UserRegistrationSerializer

    User = get_user_model()

    # Clean phone number
    clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')

    # Check if user already exists
    existing_user = User.objects.filter(phone__icontains=clean_phone).first()
    if existing_user:
        return existing_user

    # Generate a placeholder email for the user
    placeholder_email = f"whatsapp_{clean_phone}@temp.bestyy.com"

    # Prepare data for auto-signup
    signup_data = {
        'email': placeholder_email,
        'first_name': contact_name.split()[0] if contact_name else 'WhatsApp',
        'last_name': ' '.join(contact_name.split()[1:]) if contact_name and len(contact_name.split()) > 1 else 'User',
        'phone': phone_number,
        'role': 'user'
        # No password - will be handled by the serializer
    }

    # Use the serializer to create the user
    serializer = UserRegistrationSerializer(data=signup_data)
    if serializer.is_valid():
        user = serializer.save()
        logger.info(f"Auto-signed up user: {user.email} with phone {phone_number}")
        return user
    else:
        logger.error(f"Failed to auto-signup user with phone {phone_number}: {serializer.errors}")
        return None

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def _detect_food_ordering_intent(content):
    """Detect if the user wants to order specific food and return the food type"""
    content_lower = content.lower().strip()
    
    # Food ordering patterns
    ordering_patterns = [
        'i want to order', 'i want', 'i need', 'i would like', 'can i get', 
        'get me', 'bring me', 'i want some', 'order me', 'i crave'
    ]
    
    # Check if it's an ordering request
    is_ordering = any(pattern in content_lower for pattern in ordering_patterns)
    
    if not is_ordering:
        return None
    
    # Food types to detect
    food_types = [
        'pizza', 'burger', 'chicken', 'rice', 'pasta', 'soup', 'salad', 
        'sandwich', 'noodles', 'sushi', 'steak', 'fish', 'beef', 'pork', 
        'vegetarian', 'vegan', 'chinese', 'indian', 'mexican', 'thai',
        'italian', 'african', 'jollof', 'fried rice', 'shawarma', 'suya'
    ]
    
    # Find the food type in the message
    for food_type in food_types:
        if food_type in content_lower:
            return food_type
    
    return None


def _get_food_recommendations_with_api(food_type, user=None):
    """Get food recommendations by calling the actual API endpoints with time-based suggestions - ONLY show real backend data"""
    try:
        import requests
        from django.utils import timezone
        
        # Get base URL from settings
        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
        
        # Get current time for time-based recommendations
        current_hour = timezone.now().hour
        
        # Try unified recommendations API first
        try:
            api_url = f"{base_url}/api/user/recommendations/"
            params = {
                'cuisine': food_type,
                'page_size': 4
            }
            
            # Add user authentication if available
            headers = {}
            if user:
                # You might need to add authentication headers here
                pass
            
            response = requests.get(api_url, params=params, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('recommendations'):
                    recommendations = data['recommendations']
                    return _format_recommendations_message(food_type, recommendations)
                else:
                    # No recommendations found - suggest time-appropriate alternatives
                    return _get_time_based_no_food_message(food_type, current_hour)
        except Exception as e:
            logger.warning(f"Unified recommendations API failed: {str(e)}")
        
        # Fallback to vendor search API
        try:
            api_url = f"{base_url}/api/user/search/vendors/"
            params = {
                'cuisine': food_type,
                'page_size': 4
            }
            
            response = requests.get(api_url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('vendors'):
                    vendors = data['vendors']
                    return _format_vendors_message(food_type, vendors)
                else:
                    # No vendors found - tell user we don't have this food type
                    return _get_no_food_available_message(food_type)
        except Exception as e:
            logger.warning(f"Vendor search API failed: {str(e)}")
        
        # If all APIs fail, tell user we don't have this food type
        return _get_no_food_available_message(food_type)
        
    except Exception as e:
        logger.error(f"Error getting food recommendations for {food_type}: {str(e)}")
        return _get_no_food_available_message(food_type)


def _format_recommendations_message(food_type, recommendations):
    """Format recommendations from the unified API into a WhatsApp message"""
    emoji = _get_food_emoji(food_type)
    message = f"{emoji} Great choice! Here are our top {food_type} recommendations:\n\n"
    
    for i, rec in enumerate(recommendations[:4], 1):
        vendor_name = rec.get('vendor_name', 'Restaurant')
        rating = rec.get('rating', 0)
        delivery_time = rec.get('delivery_time', '30-45 min')
        
        message += f"{i}. {vendor_name}"
        if rating > 0:
            message += f" ⭐ {rating}/5"
        message += f" ({delivery_time})\n"
        
        # Add menu item details if available
        menu_items = rec.get('menu_items', [])
        if menu_items:
            message += f"   🍽️ {menu_items[0].get('name', 'Menu available')} - ₦{menu_items[0].get('price', 'N/A')}\n"
    
    message += f"\nWhich restaurant would you like to order {food_type} from? Just tell me the number!"
    return message


def _format_vendors_message(food_type, vendors):
    """Format vendors from the search API into a WhatsApp message"""
    emoji = _get_food_emoji(food_type)
    message = f"{emoji} Here are great {food_type} restaurants:\n\n"
    
    for i, vendor in enumerate(vendors[:4], 1):
        name = vendor.get('business_name', 'Restaurant')
        rating = vendor.get('rating', 0)
        delivery_time = vendor.get('delivery_time', '30-45 min')
        
        message += f"{i}. {name}"
        if rating > 0:
            message += f" ⭐ {rating}/5"
        message += f" ({delivery_time})\n"
    
    message += f"\nWhich restaurant would you like to order {food_type} from? Just tell me the number!"
    return message


def _get_no_food_available_message(food_type):
    """Tell user we don't have the requested food type and suggest time-based alternatives"""
    emoji = _get_food_emoji(food_type)
    
    # Get current time for time-based suggestions
    from django.utils import timezone
    current_hour = timezone.now().hour
    
    # Use time-based suggestions
    return _get_time_based_no_food_message(food_type, current_hour)


def _get_time_based_no_food_message(food_type, current_hour):
    """Get time-based message when requested food type is not available - BACKEND DATA ONLY"""
    try:
        # Get real food types from backend instead of hardcoded suggestions
        available_foods = _get_available_food_types()
        
        if not available_foods:
            emoji = _get_food_emoji(food_type)
            return f"{emoji} Sorry, we don't currently have {food_type} available in our system.\n\nWe're working on expanding our menu. Please check back later or contact our support team for more information."
        
        # Determine current time category
        current_category = None
        time_range = ""
        if 6 <= current_hour < 11:
            current_category = 'morning'
            time_range = '6 AM - 11 AM'
        elif 11 <= current_hour < 17:
            current_category = 'afternoon'
            time_range = '11 AM - 5 PM'
        elif 17 <= current_hour < 21:
            current_category = 'evening'
            time_range = '5 PM - 9 PM'
        else:
            current_category = 'night'
            time_range = '9 PM - 6 AM'
        
        # Create message with real backend data
        emoji = _get_food_emoji(food_type)
        message = f"{emoji} Sorry, we don't currently have {food_type} available in our system.\n\n"
        message += f"🌅 Since it's {time_range}, here are some great options we currently have:\n\n"
        
        for i, food in enumerate(available_foods[:4], 1):
            food_emoji = _get_food_emoji(food)
            message += f"{i}. {food_emoji} {food.title()}\n"
        
        message += f"\nWould you like to try any of these options instead? Just tell me which one!"
        return message
        
    except Exception as e:
        logger.error(f"Error in _get_time_based_no_food_message: {str(e)}")
        emoji = _get_food_emoji(food_type)
        return f"{emoji} Sorry, we don't currently have {food_type} available in our system. Please try again later."


def _get_available_food_types():
    """Get available food types from the backend"""
    try:
        import requests
        
        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
        
        # Try to get available cuisines from the search API
        try:
            api_url = f"{base_url}/api/user/search/vendors/"
            response = requests.get(api_url, params={'page_size': 10}, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('vendors'):
                    # Extract unique cuisines from vendors
                    cuisines = set()
                    for vendor in data['vendors']:
                        if vendor.get('business_category'):
                            cuisines.add(vendor['business_category'].lower())
                    return list(cuisines)[:6]  # Return up to 6 cuisines
        except Exception as e:
            logger.warning(f"Could not fetch available cuisines: {str(e)}")
        
        # NO FALLBACK - if we can't get data from backend, return empty list
        logger.warning("Could not fetch any food types from backend")
        return []
        
    except Exception as e:
        logger.error(f"Error getting available food types: {str(e)}")
        # NO FALLBACK - return empty list if backend is unavailable
        return []


def _get_contextual_fallback_message(content):
    """Get contextual fallback message based on content - BACKEND DATA ONLY"""
    content_lower = content.lower()
    
    # Check for specific food types and provide restaurant recommendations
    food_keywords = ['pizza', 'burger', 'chicken', 'rice', 'pasta', 'soup', 'salad', 'sandwich', 'noodles', 'sushi', 'steak', 'fish', 'beef', 'pork', 'vegetarian', 'vegan']
    for food in food_keywords:
        if food in content_lower:
            return _get_food_restaurants_text(food)
    
    # Generic responses based on content
    if 'order' in content_lower:
        return "I'd be happy to help you place an order! Could you please tell me what you'd like to order from our menu?"
    elif 'menu' in content_lower or 'food' in content.lower():
        return "I can help you with our menu! We have a variety of delicious options. What type of food are you interested in?"
    elif any(word in content_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! Welcome to Bestyy! How can I assist you today?"
    else:
        return "Thanks for your message! I'm here to help you with food delivery, orders, or any questions you might have. What can I do for you?"
