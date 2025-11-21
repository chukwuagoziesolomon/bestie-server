from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import models
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
import requests
import re

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
        # Call the vendor search API
        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
        api_url = f"{base_url}/api/user/vendors/search/"

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
        # Ensure phone number is in international format for Paystack compatibility
        formatted_phone = _format_phone_for_paystack(from_number)
        print(f"[DEBUG] Original phone: {from_number}, Formatted: {formatted_phone}")

        conversation, created = WhatsAppConversation.objects.get_or_create(
            phone_number=formatted_phone,
            defaults={
                'is_active': True,
            }
        )

        if created:
            print(f"[DEBUG] Created new conversation with phone: {formatted_phone}")
        else:
            print(f"[DEBUG] Found existing conversation with phone: {conversation.phone_number}")

        # Link user if unknown but matches by phone (robustify)
        if not conversation.user:
            # Try to find user by phone number in different profile models
            user = None
            clean_phone = from_number.replace('+','').replace('-','').replace(' ','')

            # Check UserProfile first
            try:
                from bestyy.core_features.user.models import UserProfile
                profile = UserProfile.objects.filter(phone__icontains=clean_phone).first()
                if profile:
                    user = profile.user
            except:
                pass

            # Check VendorProfile
            if not user:
                try:
                    from bestyy.core_features.user.models import VendorProfile
                    profile = VendorProfile.objects.filter(phone__icontains=clean_phone).first()
                    if profile:
                        user = profile.user
                except:
                    pass

            # Check CourierProfile
            if not user:
                try:
                    from bestyy.core_features.user.models import CourierProfile
                    profile = CourierProfile.objects.filter(phone__icontains=clean_phone).first()
                    if profile:
                        user = profile.user
                except:
                    pass

            if user:
                conversation.user = user
            conversation.save()

        user_obj = conversation.user
        user_role = None
        if user_obj:
            user_role = getattr(user_obj, 'role', None)

        meta_service = MetaWhatsAppService()
        polite_wait = "Thank you for your patience. "

        # --- AUTO-VERIFICATION LOGIC (run FIRST - most user-friendly) ---
        # Check if incoming WhatsApp number matches a pending user for auto-verification
        try:
            from bestyy.core_features.user.models import PendingUser
            from bestyy.core_features.user.api.verification_views import _process_whatsapp_signup_core
            import re
            
            def normalize_phone(p):
                return re.sub(r'[^0-9]', '', str(p or ''))  # remove any non-digit
            
            incoming_normal = normalize_phone(from_number)
            # Try to auto-verify if any active pending user matches this phone
            pending_qs = PendingUser.objects.filter(is_verified=False, expires_at__gt=timezone.now()).order_by('-created_at')
            for pending_user in pending_qs:
                pending_phone_normal = normalize_phone(pending_user.phone)
                if pending_phone_normal == incoming_normal:
                    # Phone matches! Auto-verify using the pending user's code
                    ok, payload, http_status = _process_whatsapp_signup_core(from_number, pending_user.verification_code)
                    if ok:
                        first_name = payload.get('first_name', '')
                        primary_role = payload.get('role', 'user')
                        if primary_role == 'vendor':
                            reply_success = f"""✅ Welcome {first_name}!
You are now verified as a vendor. You can start managing your store.
"""
                        elif primary_role == 'courier':
                            reply_success = f"""✅ Welcome {first_name}!
You are now verified as a courier. You can start delivering orders.
"""
                        else:
                            reply_success = f"""✅ Welcome {first_name}!
Your account is now verified. Enjoy the service!
"""
                        meta_service.send_message(to=from_number, message=reply_success)
                        return
                    else:
                        # Verification failed for some reason, continue to normal flow
                        logger.warning(f"Auto-verification failed for {from_number}: {payload.get('error', 'Unknown error')}")
                        break
        except Exception as e:
            logger.error(f"Error in auto-verification logic: {str(e)}")
            # Continue to normal flow if auto-verification fails

        # --- Handle explicit verification code entry (fallback if auto-verification didn't work) ---
        content_lower = content.lower().strip()
        if content_lower.startswith('verify ') and len(content.split()) == 2:
            code_part = content.split()[1]
            if code_part.isdigit() and len(code_part) == 6:
                # Call HTTP verification endpoint (single source of truth)
                try:
                    base_url = (
                        getattr(settings, 'SELF_BASE_URL', '') or
                        getattr(settings, 'PUBLIC_BASE_URL', '') or
                        getattr(settings, 'API_BASE_URL', '')
                    ).rstrip('/')
                    if not base_url:
                        hosts = getattr(settings, 'ALLOWED_HOSTS', [])
                        base_url = f"http://{hosts[0]}" if hosts else 'http://127.0.0.1:8000'
                    endpoint = f"{base_url}/api/auth/verify-whatsapp-signup/"
                    logger.info(f"[VERIFICATION] Calling endpoint: {endpoint} for {from_number} code={code_part}")
                    resp = requests.post(endpoint, json={
                        'phone': from_number,
                        'code': code_part
                    }, timeout=5)
                    status_code = resp.status_code
                    data = {}
                    try:
                        data = resp.json()
                    except Exception:
                        pass
                    logger.info(f"[VERIFICATION] Response status: {status_code} body={data}")
                except requests.Timeout:
                    reply = "⏳ Verification service timed out. Please try again in a moment."
                    meta_service.send_message(to=from_number, message=reply)
                    return
                except Exception as e:
                    logger.error(f"[VERIFICATION] HTTP error: {str(e)}")
                    reply = "❌ Temporary error verifying your code. Please try again shortly."
                    meta_service.send_message(to=from_number, message=reply)
                    return

                # Handle 400 errors (invalid code, expired, etc.)
                if status_code == 400:
                    error_msg = data.get('error', 'Invalid verification code')
                    if 'expired' in error_msg.lower():
                        reply = "❌ Your verification code has expired.\n\nIf you see this message, simply reply here on WhatsApp with anything and we will automatically verify you if your number matches our records.\nOtherwise, please visit the website and click 'Resend code'."
                    elif 'invalid' in error_msg.lower() or 'not found' in error_msg.lower():
                        reply = f"❌ {error_msg}\n\nIf you see this message, simply reply here on WhatsApp with anything and we will automatically verify you if your number matches our records.\nOtherwise, please visit the website and click 'Resend code'."
                    else:
                        reply = f"❌ {error_msg}\n\nPlease check your code and try again, or visit the website to request a new code."
                    meta_service.send_message(to=from_number, message=reply)
                    return

                if status_code == 200 and data.get('ok') is True:
                    first_name = data.get('first_name', '')
                    primary_role = data.get('role', 'user')

                    if primary_role == 'vendor':
                        reply = f"""✅ Welcome {first_name}!

Your vendor account has been created successfully!

📱 What you can do with WhatsApp:
• Accept and manage orders
• Send delivery updates to customers
• Receive customer inquiries
• Get order notifications

🌐 Next Steps:
1. Visit your dashboard: bestyy.com/vendor/dashboard
2. Upload your menu items
3. Set your business hours
4. Configure delivery settings

💡 Pro Tips:
• Keep your menu updated
• Respond quickly to customer messages
• Set competitive prices

Reply with HELP anytime for assistance or MENU to see available commands.

Best regards,
Bestyy Team"""
                    elif primary_role == 'courier':
                        reply = f"""✅ Welcome {first_name}!

Your courier account has been created successfully!

📱 What you can do with WhatsApp:
• Receive delivery assignments
• Update order status
• Communicate with vendors
• Get delivery notifications

🌐 Next Steps:
1. Visit your dashboard: bestyy.com/courier/dashboard
2. Set your availability
3. Update your location
4. Configure delivery preferences

💡 Pro Tips:
• Keep your location updated
• Respond quickly to assignments
• Maintain good ratings

Reply with HELP anytime for assistance or DELIVERIES to see available commands.

Best regards,
Bestyy Team"""
                    else:
                        reply = f"""✅ Welcome {first_name}!

Your Bestyy account has been created successfully!

You can now place orders and enjoy delicious food delivery.

🌐 Visit your dashboard: bestyy.com/dashboard

Best regards,
Bestyy Team"""
                elif status_code == 410:
                        reply = (
                            "❌ Your verification code has expired.\n\n"
                            "Reply with: 1 to generate a new code, or NO to skip."
                        )
                        conversation.pending_verification_action = 'expired_code'
                        conversation.save()
                elif status_code == 400:
                    reply = data.get('error') or "❌ Invalid verification code. Please check the code and try again."
                else:
                    reply = "❌ Error processing verification. Please try again."

                meta_service.send_message(to=from_number, message=reply)
                return

        # --- REMOVED: VENDOR/COURIER blocking logic ---
        # All users (vendors, couriers, customers) now have equal access to chatbot, onboarding, and food ordering
        # User lookups by phone persist for all roles - each phone session maps to one User regardless of their roles/multi-role

        # --- VENDOR/COURIER receiving order/code - skip conversational flow, allow normal code delivery ---
        if user_role in ['vendor','courier'] and content.startswith('[CODE]'):
            return  # Let external logic deliver code, do NOT chatbot/onboard

        # --- VENDOR/COURIER CODE VERIFICATION COMMANDS ---
        if user_role in ['vendor', 'courier']:
            # Check for PICKUP CODE (format: PK-XXXXXX or just XXXXXX)
            if user_role == 'vendor' and (content.strip().upper().startswith('PK-') or 
                                          (len(content.strip()) == 6 and content.strip().replace('-', '').isalnum())):
                code = content.strip().upper()
                # Remove PK- prefix if present for database lookup
                lookup_code = code.replace('PK-', '') if code.startswith('PK-') else code
                
                # Check if this vendor has any orders with this pickup code
                from bestyy.restaurant_features.order.models import Order
                try:
                    # Search with and without prefix
                    order = Order.objects.filter(
                        vendor__user=user_obj,
                        pickup_code_verified=False
                    ).filter(
                        models.Q(pickup_code__iexact=code) |
                        models.Q(pickup_code__iexact=f'PK-{code}') |
                        models.Q(pickup_code__iexact=lookup_code)
                    ).first()

                    if order:
                        # Verify the pickup code (method handles prefix normalization)
                        if order.verify_pickup_code(code):
                            # Mark as verified
                            order.pickup_code_verified = True
                            order.save()
                            
                            # Trigger vendor payout
                            payout_success = order.trigger_vendor_payout()
                            
                            # Calculate payout amount
                            payouts = order.calculate_payouts()
                            vendor_amount = payouts['vendor_amount']

                            reply = (
                                f"✅ *Pickup Code Verified!*\n\n"
                                f"📦 Order: {order.order_number}\n"
                                f"💰 Your Payout: ₦{vendor_amount:,.2f}\n"
                                f"{'💸 Payment initiated!' if payout_success else '⏳ Processing payment...'}\n\n"
                                f"The courier has picked up the order.\n"
                                f"Payment will arrive in your bank account shortly."
                            )
                        else:
                            reply = "❌ Invalid pickup code. Please check and try again."
                    else:
                        reply = (
                            f"❌ No order found with code: {code}\n\n"
                            f"Please ensure:\n"
                            f"• The code is correct (format: PK-XXXXXX)\n"
                            f"• The order hasn't been verified already\n"
                            f"• The order belongs to your vendor account"
                        )

                    meta_service.send_message(to=from_number, message=reply)
                    return

                except Exception as e:
                    logger.error(f"Error verifying pickup code for vendor {user_obj}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    reply = "❌ Error processing pickup code. Please try again or contact support."
                    meta_service.send_message(to=from_number, message=reply)
                    return

            # Check for DELIVERY OTP (format: DL-XXXXXX or just XXXXXX)
            elif user_role == 'courier' and (content.strip().upper().startswith('DL-') or 
                                              (len(content.strip()) == 6 and content.strip().isdigit())):
                otp = content.strip().upper()
                # Remove DL- prefix if present for database lookup
                lookup_otp = otp.replace('DL-', '') if otp.startswith('DL-') else otp
                
                # Check if this courier has any orders with this delivery OTP
                from bestyy.restaurant_features.order.models import Order
                try:
                    # Search with and without prefix
                    order = Order.objects.filter(
                        courier__user=user_obj,
                        delivery_otp_verified=False
                    ).filter(
                        models.Q(delivery_otp__iexact=otp) |
                        models.Q(delivery_otp__iexact=f'DL-{otp}') |
                        models.Q(delivery_otp__iexact=lookup_otp)
                    ).first()

                    if order:
                        # Verify the delivery OTP (method handles prefix normalization)
                        if order.verify_delivery_otp(otp):
                            # Mark as verified
                            order.delivery_otp_verified = True
                            
                            # Mark order as delivered and trigger courier payout
                            order.mark_as_delivered()
                            payout_success = order.trigger_courier_payout()
                            
                            # Calculate payout amount
                            payouts = order.calculate_payouts()
                            courier_amount = payouts['courier_amount']

                            reply = (
                                f"✅ *Delivery Confirmed!*\n\n"
                                f"📦 Order: {order.order_number}\n"
                                f"💰 Your Payout: ₦{courier_amount:,.2f}\n"
                                f"{'💸 Payment initiated!' if payout_success else '⏳ Processing payment...'}\n\n"
                                f"Order marked as delivered.\n"
                                f"Payment will arrive in your bank account shortly."
                            )
                        else:
                            reply = "❌ Invalid delivery OTP. Please check and try again."
                    else:
                        reply = (
                            f"❌ No order found with OTP: {otp}\n\n"
                            f"Please ensure:\n"
                            f"• The OTP is correct (format: DL-XXXXXX)\n"
                            f"• The order hasn't been delivered already\n"
                            f"• The order is assigned to you"
                        )

                    meta_service.send_message(to=from_number, message=reply)
                    return

                except Exception as e:
                    logger.error(f"Error verifying delivery OTP for courier {user_obj}: {str(e)}")
                    import traceback
                    traceback.print_exc()
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

        # --- SIGNUP VERIFICATION - Check for VERIFY command with code ---
        # This handles verification codes sent during signup process
        content_lower = content.lower().strip()
        if content_lower.startswith('verify ') and len(content.split()) == 2:
            code_part = content.split()[1]
            if code_part.isdigit() and len(code_part) == 6:
                # First, check if this number has a pending signup
                try:
                    from bestyy.core_features.user.models import PendingUser
                    clean_phone = from_number.replace('+', '').replace('-', '').replace(' ', '')
                    pending = (PendingUser.objects
                              .filter(phone__icontains=clean_phone, is_verified=False)
                              .order_by('-created_at').first())
                except Exception as e:
                    logger.error(f"Lookup pending user failed: {str(e)}")
                    pending = None

                if not pending:
                    reply = (
                        "❌ Invalid verification code.\n\n"
                        "We couldn't find a pending signup for this number. "
                        "Please start the signup again from the website/app."
                    )
                    meta_service.send_message(to=from_number, message=reply)
                    return

                if pending.is_expired:
                    reply = (
                        "❌ Your verification code has expired.\n\n"
                        "Reply with: 1 to generate a new code, or NO to skip."
                    )
                    conversation.pending_verification_action = 'expired_code'
                    conversation.save()
                    meta_service.send_message(to=from_number, message=reply)
                    return

                if code_part != getattr(pending, 'verification_code', ''):
                    reply = "❌ Invalid verification code. Please check the code and try again."
                    meta_service.send_message(to=from_number, message=reply)
                    return

                # Use shared verification core (safe path)
                try:
                    from bestyy.core_features.user.api.verification_views import _process_whatsapp_signup_core
                    ok, payload, _http_status = _process_whatsapp_signup_core(from_number, code_part)
                except Exception as e:
                    logger.error(f"Verification core error: {str(e)}")
                    ok, payload = False, {'error': 'Error processing verification'}

                if ok:
                    first_name = payload.get('first_name', '')
                    primary_role = payload.get('role', 'user')

                    if primary_role == 'vendor':
                        reply = f"""✅ Welcome {first_name}!

Your vendor account has been created successfully!

📱 What you can do with WhatsApp:
• Accept and manage orders
• Send delivery updates to customers
• Receive customer inquiries
• Get order notifications

🌐 Next Steps:
1. Visit your dashboard: bestyy.com/vendor/dashboard
2. Upload your menu items
3. Set your business hours
4. Configure delivery settings

💡 Pro Tips:
• Keep your menu updated
• Respond quickly to customer messages
• Set competitive prices

Reply with HELP anytime for assistance or MENU to see available commands.

Best regards,
Bestyy Team"""
                    elif primary_role == 'courier':
                        reply = f"""✅ Welcome {first_name}!

Your courier account has been created successfully!

📱 What you can do with WhatsApp:
• Receive delivery assignments
• Update order status
• Communicate with vendors
• Get delivery notifications

🌐 Next Steps:
1. Visit your dashboard: bestyy.com/courier/dashboard
2. Set your availability
3. Update your location
4. Configure delivery preferences

💡 Pro Tips:
• Keep your location updated
• Respond quickly to assignments
• Maintain good ratings

Reply with HELP anytime for assistance or DELIVERIES to see available commands.

Best regards,
Bestyy Team"""
                    else:
                        reply = f"""✅ Welcome {first_name}!

Your Bestyy account has been created successfully!

You can now place orders and enjoy delicious food delivery.

🌐 Visit your dashboard: bestyy.com/dashboard

Best regards,
Bestyy Team"""
                else:
                    # Decide if the error was due to expired code
                    error_msg = payload.get('error', 'Invalid verification code')
                    if 'expired' in error_msg.lower():
                        reply = (
                            "❌ Your verification code has expired.\n\n"
                            "Reply with: 1 to generate a new code, or NO to skip."
                        )
                        conversation.pending_verification_action = 'expired_code'
                        conversation.save()
                    else:
                        reply = "❌ Invalid verification code. Please check the code and try again."
                if reply:
                    meta_service.send_message(to=from_number, message=reply)
                    return
            else:
                reply = "Invalid format. Please send: VERIFY 123456"
                meta_service.send_message(to=from_number, message=reply)
                return

        # --- Handle expired code follow-up responses ---
        if conversation.pending_verification_action == 'expired_code':
            if content.lower().strip() in ['yes', 'y', 'generate', 'new code']:
                # Generate new verification code for existing pending user
                try:
                    # Find the most recent pending user for this phone
                    pending_user = PendingUser.objects.filter(
                        phone=from_number,
                        is_verified=False
                    ).order_by('-created_at').first()

                    if pending_user:
                        # Generate new code
                        import secrets
                        new_code = str(secrets.randbelow(900000) + 100000)
                        pending_user.verification_code = new_code
                        pending_user.created_at = timezone.now()  # Reset expiration
                        pending_user.save()

                        reply = f"""✅ New verification code generated!

Send the following message to verify your account:

VERIFY {new_code}

This code will expire in 24 hours."""
                    else:
                        reply = "❌ No pending verification found. Please start the signup process again."

                except Exception as e:
                    logger.error(f"Error generating new verification code: {str(e)}")
                    reply = "❌ Error generating new code. Please try again later."

                # Clear the pending action
                conversation.pending_verification_action = None
                conversation.save()

                meta_service.send_message(to=from_number, message=reply)
                return

            elif content.lower().strip() in ['no', 'n', 'skip', 'cancel']:
                # User chose to skip verification
                reply = """Okay, I've skipped the verification for now.

You can still use basic features, but some advanced features may require verification.

If you change your mind, you can always verify later by starting the signup process again.

How can I help you today?"""

                # Clear the pending action
                conversation.pending_verification_action = None
                conversation.save()

                meta_service.send_message(to=from_number, message=reply)
                return

        # WhatsApp code resend logic
        if content.strip().lower() == 'resend':
            resend_endpoint = (
                getattr(settings, 'SELF_BASE_URL', '') or
                getattr(settings, 'PUBLIC_BASE_URL', '') or
                getattr(settings, 'API_BASE_URL', '') or
                'http://127.0.0.1:8000'
            ).rstrip('/') + '/api/auth/resend-verification-code/'
            try:
                resp = requests.post(resend_endpoint, json={'phone': from_number}, timeout=5)
                if resp.status_code == 200 and resp.json().get('success'):
                    meta_service.send_message(
                        to=from_number,
                        message="A new verification code has been sent to your WhatsApp. Please check and enter it!"
                    )
                else:
                    msg = resp.json().get('error', 'We could not resend the code. Please return to the website for assistance.')
                    meta_service.send_message(to=from_number, message=msg)
            except Exception as e:
                logger.error(f"Failed to resend WhatsApp code: {str(e)}")
                meta_service.send_message(to=from_number, message="Temporary error sending new code. Please try again or go to the website and click 'Resend code'.")
            return

        # --- Prevent duplicate WhatsApp inbound messages (idempotency fix) ---
        from .models import WhatsAppMessage
        whatsapp_message, created = WhatsAppMessage.objects.get_or_create(
            conversation=conversation,
            message_id=message_id,
            defaults={
                'message_type': 'text',
                'content': content,
                'direction': 'inbound',
                'timestamp': timezone.now(),
            }
        )
        if not created:
            logger.warning(f"Duplicate message_id detected: {message_id}")
            return  # Do not process again
        # (intent logic continues below)

        # --- 🚀 ENHANCED AI-FIRST PROCESSING (with spell correction, memory, and RLHF) ---
        from .ai_first_processor import integrate_ai_first_processing
        
        ai_first_context = {
            'user_exists': bool(conversation.user),
            'awaiting_address': conversation.awaiting_address,
            'conversation': conversation,
            'phone_number': from_number
        }
        
        # Try AI-first processing
        ai_first_result = integrate_ai_first_processing(content, whatsapp_message, conversation, ai_first_context)
        
        # If AI handled it (not a direct command), send response and return
        if ai_first_result and ai_first_result.get('response'):
            logger.info(f"✨ AI-first handled message with confidence {ai_first_result.get('confidence', 0):.2f}")
            meta_service.send_message(to=from_number, message=ai_first_result['response'])
            
            # Update message with AI response
            whatsapp_message.ai_response = ai_first_result['response']
            whatsapp_message.ai_confidence = ai_first_result.get('confidence', 0.0)
            whatsapp_message.is_ai_processed = True
            whatsapp_message.save()
            return
        
        # If it was a direct command or AI couldn't handle, continue with rule-based processing
        logger.info(f"🔧 Continuing with rule-based processing (handled_by: {ai_first_result.get('handled_by', 'unknown') if ai_first_result else 'none'})")

        # --- SMART INTENT DETECTION (AI-based intent classifier for ALL messages) ---
        from .ai_service import WhatsAppAIService, WhatsAppMessage
        ai_service = WhatsAppAIService()
        intent_result = ai_service.process_message(whatsapp_message, context={'user_exists': bool(conversation.user)})
        category = intent_result.get('category', None)

        # --- Handle verification intent (AI detected) ---
        if category == 'verification':
            import re
            code_part = intent_result.get('code')
            if code_part:
                try:
                    from bestyy.core_features.user.models import PendingUser
                    clean_phone = from_number.replace('+', '').replace('-', '').replace(' ', '')
                    pending = (PendingUser.objects
                              .filter(phone__icontains=clean_phone, is_verified=False)
                              .order_by('-created_at').first())
                except Exception as e:
                    logger.error(f"Lookup pending user failed: {str(e)}")
                    pending = None

                if not pending:
                    reply = (
                        "❌ Invalid verification code.\n\n"
                        "If you see this message, simply reply here on WhatsApp with anything and we will automatically verify you if your number matches our records.\n"
                        "Otherwise, please visit the website and click 'Resend code'."
                    )
                    meta_service.send_message(to=from_number, message=reply)
                    return

                if pending.is_expired:
                    reply = (
                        "❌ Your verification code has expired.\n\n"
                        "If you see this message, simply reply here on WhatsApp with anything and we will automatically verify you if your number matches our records.\n"
                        "Otherwise, please visit the website and click 'Resend code'."
                    )
                    conversation.pending_verification_action = 'expired_code'
                    conversation.save()
                    meta_service.send_message(to=from_number, message=reply)
                    return

                if code_part != getattr(pending, 'verification_code', ''):
                    reply = "❌ Invalid verification code. Please check the code and try again."
                    meta_service.send_message(to=from_number, message=reply)
                    return

                # Use shared verification core (safe path)
                try:
                    from bestyy.core_features.user.api.verification_views import _process_whatsapp_signup_core
                    ok, payload, _http_status = _process_whatsapp_signup_core(from_number, code_part)
                except Exception as e:
                    logger.error(f"Verification core error: {str(e)}")
                    ok, payload = False, {'error': 'Error processing verification'}

                if ok:
                    first_name = payload.get('first_name', '')
                    primary_role = payload.get('role', 'user')
                    if primary_role == 'vendor':
                        reply = f"""✅ Welcome {first_name}!
You are now verified as a vendor. You can start managing your store.
"""
                    elif primary_role == 'courier':
                        reply = f"""✅ Welcome {first_name}!
You are now verified as a courier. You can start delivering orders.
"""
                    else:
                        reply = f"""✅ Welcome {first_name}!
Your account is now verified. Enjoy the service!
"""
                    meta_service.send_message(to=from_number, message=reply)
                else:
                    reply = payload.get('error', 'Verification failed. Please try again.')
                    meta_service.send_message(to=from_number, message=reply)
                return
        # --- continue with food ordering/general fallback ...

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
                if existing:
                    # Determine if this WhatsApp number is already linked to any of the user's profiles
                    phone_linked = False
                    try:
                        from bestyy.core_features.user.models import UserProfile, VendorProfile, CourierProfile
                        clean_phone = from_number.replace('+','').replace('-','').replace(' ','')
                        # Check all possible profiles for the same user
                        if hasattr(existing, 'profile') and existing.profile and existing.profile.phone and clean_phone in existing.profile.phone:
                            phone_linked = True
                        if not phone_linked and hasattr(existing, 'vendor_profile') and existing.vendor_profile and existing.vendor_profile.phone and clean_phone in existing.vendor_profile.phone:
                            phone_linked = True
                        if not phone_linked and hasattr(existing, 'courier_profile') and existing.courier_profile and existing.courier_profile.phone and clean_phone in existing.courier_profile.phone:
                            phone_linked = True
                    except Exception:
                        phone_linked = False

                    if not phone_linked:
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
                    # New user: call multi-role registration endpoint to create as 'user'
                    import secrets
                    password = secrets.token_urlsafe(8)
                    try:
                        base_url = (
                            getattr(settings, 'SELF_BASE_URL', '') or
                            getattr(settings, 'PUBLIC_BASE_URL', '') or
                            getattr(settings, 'API_BASE_URL', '') or
                            getattr(settings, 'BASE_URL', '')
                        ).rstrip('/') or 'http://127.0.0.1:8000'
                        endpoint = f"{base_url}/api/user/register/multi-role/"
                        payload = {
                            'email': email,
                            'first_name': (contact_name.split()[0] if contact_name else 'WhatsApp'),
                            'last_name': (' '.join(contact_name.split()[1:]) if contact_name and len(contact_name.split()) > 1 else 'User'),
                            'phone': from_number,
                            'password': password,
                            'confirm_password': password,
                            'roles': ['user']
                        }
                        resp = requests.post(endpoint, json=payload, timeout=8)
                        if resp.status_code in (200, 201):
                            # Link conversation to the newly created/updated user
                            try:
                                from django.contrib.auth import get_user_model
                                UserModel = get_user_model()
                                user = UserModel.objects.filter(email=email).first()
                                if user:
                                    conversation.user = user
                                    conversation.onboarding_state = 'onboarded'
                                    conversation.save()
                            except Exception:
                                pass

                            # Send credentials by email
                            try:
                                from django.core.mail import send_mail
                                base_url_mail = getattr(settings, 'BASE_URL', 'https://bestyy.com')
                                logo_url = f"{base_url_mail}/static/logo.png"
                                subject = "Welcome to Bestyy - Your Account Details"
                                html_message = f"""
                                    <html><body style='font-family: Nunito Sans, Arial, sans-serif; background: #fafbfc; max-width: 640px; margin: auto;'>
                                        <div style='background: linear-gradient(90deg, #23C7B2 0%, #25AC9B 100%); padding: 24px 0; text-align: center; color: #fff;'>
                                            <img src='{logo_url}' alt='Bestyy' style='max-width: 84px; border-radius: 10px;'><br>
                                            <h1>Welcome to Bestyy!</h1>
                                        </div>
                                        <div style='background: #fff; border-radius: 12px; margin: 32px 0; padding: 32px;'>
                                            <p style='font-size: 18px;'>Hello {payload['first_name']},</p>
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
                                    fail_silently=True
                                )
                            except Exception as e:
                                logger.warning(f"Failed to send welcome email: {str(e)}")

                            # Warm, personalized welcome
                            first_name = payload['first_name']
                            meta_service.send_message(
                                to=from_number,
                                message=(
                                    f"Welcome to Bestyy, {first_name}! 🎉 Your account is ready. "
                                    "I've sent details to your email."
                                )
                            )
                            # Continue with onboarding questions immediately
                            onboarding_prompt = (
                                "Hey — I'm Bestyy 👋, your food-finding AI! I'll help you discover, order and reorder meals quickly.\n\n"
                                "Quick choices — reply with the number or type a word:\n"
                                "1. Local\n2. Fast food\n3. Western\n4. Vegetarian / Healthy\n5. Desserts & Drinks\n\n"
                                "Bestyy: I have a few quick questions so I serve you best, would you like to skip or am I allowed to ask?"
                            )
                            meta_service.send_message(to=from_number, message=onboarding_prompt)
                        else:
                            meta_service.send_message(
                                to=from_number,
                                message="Sorry, we couldn't create your account right now. Please try again in a moment."
                            )
                    except Exception as e:
                        logger.error(f"Multi-role registration call failed: {str(e)}")
                        meta_service.send_message(
                            to=from_number,
                            message="Sorry, we couldn't create your account right now. Please try again shortly."
                        )
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
            import re
            normalized = re.sub(r'[^a-z]', '', content.lower())
            if normalized in ['yes', 'y']:
                email = conversation.pending_email
                existing = User.objects.filter(email=email).first()
                if existing:
                    # Link WhatsApp number to this account via profiles
                    try:
                        from bestyy.core_features.user.models import UserProfile, VendorProfile, CourierProfile
                        # Ensure user profile exists and set phone
                        profile, _ = UserProfile.objects.get_or_create(user=existing)
                        profile.phone = from_number
                        profile.save()
                        # If vendor/courier profiles exist, optionally set phone there too
                        try:
                            if hasattr(existing, 'vendor_profile'):
                                existing.vendor_profile.phone = from_number
                                existing.vendor_profile.save()
                        except Exception:
                            pass
                        try:
                            if hasattr(existing, 'courier_profile'):
                                existing.courier_profile.phone = from_number
                                existing.courier_profile.save()
                        except Exception:
                            pass
                    except Exception:
                        pass

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
                        f"✅ Linked! Your WhatsApp number is now connected to {email}. You're all set.\n\nWhat would you like to eat today?"
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
            content_lower = content.lower().strip()
            
            # PRIORITY 0: Check if user is a vendor responding to order
            # Check both user_obj and conversation.user, OR check by phone number
            check_user = user_obj or conversation.user
            vendor_profile = None
            
            try:
                from bestyy.core_features.user.models import VendorProfile
                
                # Try to find vendor by user first
                if check_user:
                    vendor_profile = VendorProfile.objects.filter(user=check_user).first()
                
                # If not found by user, try by phone number
                if not vendor_profile and from_number:
                    clean_phone = from_number.replace('+', '').replace(' ', '')[-10:]
                    vendor_profile = VendorProfile.objects.filter(
                        phone__icontains=clean_phone,
                        is_suspended=False
                    ).first()
                    
                    if vendor_profile:
                        logger.info(f"🏪 Found vendor by phone: {vendor_profile.business_name}")
                        # Link vendor to conversation if not already linked
                        if vendor_profile.user and not conversation.user:
                            conversation.user = vendor_profile.user
                            conversation.save()
                
                if vendor_profile:
                    # This is a vendor - check for vendor-specific commands
                    logger.info(f"🏪 Detected vendor {vendor_profile.business_name} - checking for vendor commands")
                    vendor_response = _handle_vendor_order_response(content_lower, from_number, meta_service, check_user, vendor_profile)
                    if vendor_response:
                        logger.info(f"✅ Vendor command processed: {content_lower[:20]}")
                        meta_service.send_message(to=from_number, message=vendor_response)
                        return
                    else:
                        logger.info(f"ℹ️ Not a vendor command, continuing normal flow")
            except Exception as e:
                logger.error(f"Error handling vendor response: {str(e)}")
                import traceback
                traceback.print_exc()
            
            # PRIORITY 0.5: Handle order conflict resolution (YES/NO after preference warning)
            if conversation.context_data.get('order_conflict'):
                if content_lower in ['yes', 'y', 'continue', 'proceed']:
                    # User confirms they want to order despite disliking it
                    conflict_data = conversation.context_data['order_conflict']
                    pending = conflict_data.get('pending_dish')
                    order_id = conflict_data.get('order_id')
                    
                    if pending and order_id:
                        try:
                            from bestyy.restaurant_features.order.models import Order, OrderItem
                            from bestyy.restaurant_features.product.models import Product
                            from decimal import Decimal
                            
                            order = Order.objects.get(id=order_id)
                            product = Product.objects.get(id=pending['product_id'])
                            
                            # Create the OrderItem
                            OrderItem.objects.create(
                                order=order,
                                product=product,
                                quantity=1,
                                price=Decimal(pending['price'])
                            )
                            
                            # Update total
                            order.total_amount = Decimal(sum(item.price * item.quantity for item in order.items.all()))
                            order.save()
                            
                            # Clear conflict and pending dish
                            conversation.context_data.pop('order_conflict', None)
                            conversation.context_data.pop('pending_dish', None)
                            conversation.save()
                            
                            response = f"✅ Got it! I've added *{pending['dish_name']}* to your order.\n\n"
                            response += "Anything else you'd like to add? Reply 'DONE' when ready!"
                            meta_service.send_message(to=from_number, message=response)
                            return
                        except Exception as e:
                            logger.error(f"Error adding conflicting item: {str(e)}")
                
                elif content_lower in ['no', 'n', 'cancel', 'nope', 'stop']:
                    # User cancels the conflicting item
                    conflict_data = conversation.context_data['order_conflict']
                    item_name = conflict_data.get('item', 'that item')
                    
                    # Clear conflict and pending dish
                    conversation.context_data.pop('order_conflict', None)
                    conversation.context_data.pop('pending_dish', None)
                    conversation.save()
                    
                    response = f"👍 No problem! I won't add *{item_name}*.\n\n"
                    response += "What would you like to order instead? 😊"
                    meta_service.send_message(to=from_number, message=response)
                    return
            
            # PRIORITY 0.75: Handle "MORE" for vendor pagination
            if content_lower == 'more':
                vendor_search_result = _handle_more_vendors(conversation, from_number, meta_service)
                if vendor_search_result:
                    meta_service.send_message(to=from_number, message=vendor_search_result)
                    return
            
            # PRIORITY 0.8: Handle vendor selection by number
            if content_lower.isdigit() and conversation.context_data.get('vendor_selection_active'):
                vendor_selection_result = _handle_vendor_selection(
                    int(content_lower), 
                    conversation, 
                    from_number, 
                    meta_service,
                    user_obj
                )
                if vendor_selection_result:
                    meta_service.send_message(to=from_number, message=vendor_selection_result)
                    return
            
            # PRIORITY 1: Check for saved address references
            saved_address_ref = _detect_saved_address_reference(content_lower)
            if saved_address_ref:
                try:
                    address_message = _handle_saved_address_order(saved_address_ref, content, from_number, meta_service, user_obj)
                    if address_message:
                        meta_service.send_message(to=from_number, message=address_message)
                        return
                except Exception as e:
                    logger.error(f"Error handling saved address order: {str(e)}")

            # PRIORITY 2: Check for address saving requests
            if content_lower.startswith('save '):
                try:
                    save_message = _handle_address_save_request(content, from_number, meta_service, user_obj)
                    if save_message:
                        meta_service.send_message(to=from_number, message=save_message)
                        return
                except Exception as e:
                    logger.error(f"Error handling address save: {str(e)}")

            # PRIORITY 3: Check if we're explicitly awaiting a delivery address
            # If awaiting_address is True, treat ANY non-command message as an address
            if conversation.awaiting_address:
                # Skip obvious commands or very short responses
                skip_words = ['yes', 'no', 'done', 'more', 'cancel', 'help', 'menu', 'paid', 'status', 'payment done', 'transferred', 'sent']
                if content_lower not in skip_words and len(content.strip()) > 5:
                    try:
                        logger.info(f"Processing message as address because awaiting_address=True: '{content}'")
                        address_message = _process_delivery_address(content, from_number, meta_service, user_obj, conversation)
                        if address_message:
                            meta_service.send_message(to=from_number, message=address_message)
                            return
                    except Exception as e:
                        logger.error(f"Error processing awaited delivery address: {str(e)}")

            # PRIORITY 4: Check for delivery address responses (any message that looks like an address)
            from .utils import looks_like_address
            if looks_like_address(content):
                try:
                    address_message = _process_delivery_address(content, from_number, meta_service, user_obj, conversation)
                    if address_message:
                        meta_service.send_message(to=from_number, message=address_message)
                        return
                except Exception as e:
                    logger.error(f"Error processing delivery address: {str(e)}")

            # PRIORITY 4.5: Check for order status requests
            if content_lower in ['status', 'order status', 'check status', 'my order', 'where is my order']:
                try:
                    status_message = _check_order_status(from_number, user_obj, conversation)
                    if status_message:
                        meta_service.send_message(to=from_number, message=status_message)
                        return
                except Exception as e:
                    logger.error(f"Error checking order status: {str(e)}")

            # PRIORITY 4.6: Check for PAID confirmation (skip payment verification for testing)
            if content_lower in ['paid', 'payment done', 'transferred', 'sent', 'i paid', 'done paying']:
                try:
                    paid_message = _handle_paid_confirmation(from_number, meta_service, user_obj, conversation)
                    if paid_message:
                        meta_service.send_message(to=from_number, message=paid_message)
                        return
                except Exception as e:
                    logger.error(f"Error handling paid confirmation: {str(e)}")

            # PRIORITY 5: Check for order completion responses (YES/DONE vs NO/MORE)
            if content_lower in ['yes', 'done', 'complete', 'finish', 'all done', 'thats all', 'no', 'more', 'add', 'something else', 'another']:
                try:
                    completion_message = _handle_order_completion_response(content, from_number, meta_service, user_obj, conversation)
                    if completion_message:
                        meta_service.send_message(to=from_number, message=completion_message)
                        return
                except Exception as e:
                    logger.error(f"Error handling order completion: {str(e)}")

            # PRIORITY 5: Check for order confirmation responses
            if content_lower in ['confirm', '1', 'okay', 'ok', 'sure', 'yes please', 'confirm order']:
                try:
                    confirmation_message = _process_order_confirmation(from_number, meta_service, user_obj)
                    if confirmation_message:
                        meta_service.send_message(to=from_number, message=confirmation_message)
                        return
                except Exception as e:
                    logger.error(f"Error processing order confirmation: {str(e)}")

            # PRIORITY 3: Check for ordering intents from current menu context
            ordering_intent = _detect_menu_ordering_intent(content)
            if ordering_intent:
                try:
                    order_message = _process_menu_order(ordering_intent, from_number, meta_service, user_obj)
                    if order_message:
                        meta_service.send_message(to=from_number, message=order_message)
                        return
                except Exception as e:
                    logger.error(f"Error processing menu order: {str(e)}")

            # PRIORITY 4: Check if user is selecting a restaurant by number (1, 2, 3, etc.)
            content_stripped = content.strip()
            if content_stripped.isdigit() and len(content_stripped) == 1:
                selection_number = int(content_stripped)
                if 1 <= selection_number <= 9:
                    # User is selecting a restaurant - fetch vendor menu
                    try:
                        menu_message = _get_vendor_menu_by_selection(selection_number, from_number, meta_service)
                        if menu_message:  # Only send if there's a text message to send
                            meta_service.send_message(to=from_number, message=menu_message)
                            return
                        else:  # Function sent multiple messages including images
                            return
                    except Exception as e:
                        logger.error(f"Error getting vendor menu for selection {selection_number}: {str(e)}")

            # PRIORITY 5: Check for direct food ordering requests (with vendor recommendation)
            food_intent = _detect_food_ordering_intent(content)
            if food_intent:
                try:
                    # Extract vendor name and dish from message
                    dish_name, vendor_name = _extract_vendor_and_dish(content)
                    
                    # Use new vendor recommendation service
                    recommendation_message = _handle_vendor_recommendation(
                        dish_name=dish_name,
                        vendor_name=vendor_name,
                        conversation=conversation,
                        phone_number=from_number,
                        meta_service=meta_service,
                        user=user_obj
                    )
                    
                    meta_service.send_message(to=from_number, message=recommendation_message)
                    return
                except Exception as e:
                    logger.error(f"Error in vendor recommendation for {food_intent}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    # Fallback to generic food message
                    fallback_message = _get_food_restaurants_text(food_intent)
                    meta_service.send_message(to=from_number, message=fallback_message)
                    return
            # Recommendation, budget, or "I'm hungry" assistance
            lowered = content.lower()
            recommendation_triggers = ['recommend', 'suggest', "i'm hungry", 'im hungry', 'hungry', 'where can i eat', 'what should i eat']
            if any(trigger in lowered for trigger in recommendation_triggers) or 'budget' in lowered:
                try:
                    # Extract budget if present (e.g., ₦2000, 2000, 2k)
                    import re
                    budget = None
                    m = re.search(r"(?:₦|ngn|n)?\s*([0-9]{3,6})(?:\s*naira|\s*ngn)?", lowered)
                    if not m:
                        m = re.search(r"([0-9]+)\s*k\b", lowered)  # e.g., 2k
                        if m:
                            budget = int(m.group(1)) * 1000
                    elif m:
                        budget = int(m.group(1))

                    # Offer category-based quick picks
                    categories_message = (
                        (f"Got it! Budget noted: ₦{budget:,.0f}. " if budget else "Got it! ") +
                        "Here are quick options. Reply with a number or tell me a dish:\n\n"
                        "1. Local\n2. Fast food\n3. Western\n4. Vegetarian / Healthy\n5. Desserts & Drinks\n\n"
                        "You can also say things like 'pizza under ₦3000' or 'cheap jollof'."
                    )
                    meta_service.send_message(to=from_number, message=categories_message)
                    return
                except Exception as e:
                    logger.error(f"Recommendation assist failed: {str(e)}")

            # For non-food ordering messages, use normal AI service
            try:
                ai_service = WhatsAppAIService()
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

def _format_phone_for_paystack(phone_number: str) -> str:
    """
    Format phone number for Paystack API (international format required)
    """
    if not phone_number:
        return phone_number

    # Remove all non-digit characters
    cleaned = ''.join(filter(str.isdigit, phone_number))

    # Handle different Nigerian phone number formats
    if cleaned.startswith('0') and len(cleaned) == 11:
        # Convert 08012345678 to +2348012345678
        cleaned = '+234' + cleaned[1:]
    elif len(cleaned) == 10 and not cleaned.startswith('234'):
        # Convert 8012345678 to +2348012345678
        cleaned = '+234' + cleaned
    elif cleaned.startswith('234') and len(cleaned) == 13:
        # Already in correct format: 2348012345678 -> +2348012345678
        cleaned = '+' + cleaned
    elif not cleaned.startswith('+234') and len(cleaned) == 13 and cleaned.startswith('234'):
        # Handle 2348012345678 -> +2348012345678
        cleaned = '+' + cleaned

    # Ensure it's in +234XXXXXXXXXX format
    if not cleaned.startswith('+234'):
        logger.warning(f"Phone number {cleaned} doesn't match expected Nigerian format")
        # Try to force it into +234 format if it looks like a Nigerian number
        if len(cleaned) >= 10:
            # Take last 10 digits and add +234
            cleaned = '+234' + cleaned[-10:]

    logger.info(f"Formatted phone number: {phone_number} -> {cleaned}")
    return cleaned


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def _detect_menu_ordering_intent(content):
    """Detect if user wants to order from the current menu context"""
    content_lower = content.lower().strip()

    # Ordering patterns that indicate intent to order from current menu
    ordering_patterns = [
        'i want', 'i\'ll take', 'i would like', 'can i get', 'can i have',
        'i need', 'order', 'get me', 'give me', 'i\'d like', 'i want the',
        'i want a', 'i want some', 'i\'ll have', 'i\'ll get'
    ]

    # Check if it's an ordering request
    is_ordering = any(pattern in content_lower for pattern in ordering_patterns)

    if not is_ordering:
        return None

    # Extract the dish name from ordering phrases
    import re
    patterns = [
        r"i\s*(?:want|would like|wanna|need|\'ll take|\'ll have|\'ll get)\s*(?:the|a|some|)\s*(.+)",
        r"can\s*i\s*(?:get|have|order)\s*(?:the|a|some|)\s*(.+)",
        r"order\s*(?:the|a|)\s*(.+)",
        r"get\s*me\s*(?:the|a|)\s*(.+)",
        r"give\s*me\s*(?:the|a|)\s*(.+)",
    ]

    for pat in patterns:
        m = re.search(pat, content_lower)
        if m:
            dish_name = m.group(1).strip()
            # Clean up the dish name
            dish_name = re.sub(r'[^\w\s]', '', dish_name)  # Remove punctuation
            dish_name = re.sub(r'\s+', ' ', dish_name)  # Normalize spaces
            if dish_name and len(dish_name) > 2:  # Must be at least 3 chars
                return dish_name.lower()

    return None


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

    # Try Nigerian dishes knowledge base (e.g., abacha, egusi, efo riro, etc.)
    try:
        from .nigerian_dishes_kb import find_nigerian_dish
        kb_match = find_nigerian_dish(content)
        if kb_match:
            return kb_match
    except Exception:
        pass

    # Heuristic fallback: extract likely food phrase after intent verbs (works for foods not in lists)
    try:
        import re
        # Common ordering phrases followed by the dish name
        patterns = [
            r"i\s*(?:want|would like|wanna|need)\s*(?:to\s*order|)\s*(.+)",
            r"can\s*i\s*(?:get|have|order)\s*(.+)",
            r"order\s*(.+)",
            r"get\s*me\s*(.+)",
        ]
        for pat in patterns:
            m = re.search(pat, content_lower)
            if m:
                candidate = m.group(1).strip()
                # Trim trailing polite phrases
                candidate = re.sub(r"\b(please|now|today|for me)\b", "", candidate).strip()
                # Keep up to first 4 words to avoid overlong queries
                words = candidate.split()
                if words:
                    return " ".join(words[:4])
    except Exception:
        pass

    return None


def _get_food_recommendations_with_api(food_type, user=None):
    """Get food recommendations by calling the actual API endpoints with time-based suggestions - ONLY show real backend data"""
    try:
        # Get base URL from settings
        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
        
        # Get current time for time-based recommendations
        current_hour = timezone.now().hour
        
        # Try unified recommendations API first
        try:
            api_url = f"{base_url}/api/user/vendors/recommendations/"
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
            api_url = f"{base_url}/api/user/vendors/search/"
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
    """Format recommendations from the unified API into a WhatsApp message with rich details and images"""
    emoji = _get_food_emoji(food_type)
    message = f"{emoji} Great choice! Here are our top {food_type} recommendations:\n\n"

    for i, rec in enumerate(recommendations[:3], 1):  # Show top 3 for better readability
        vendor_name = rec.get('business_name', 'Restaurant')  # Note: API might use 'business_name' not 'vendor_name'
        rating = rec.get('rating', 0)
        delivery_time = rec.get('delivery_time', '30-45 min')
        total_reviews = rec.get('total_reviews', 0)

        # Sample menu item with image (if available)
        food_images = rec.get('food_images', [])
        if food_images and len(food_images) > 0:
            sample_item = food_images[0]  # First item is usually featured
            item_name = sample_item.get('dish_name', 'Signature dish')
            item_price = sample_item.get('price', 0)
            image_url = sample_item.get('image', '')

            # Send actual image message if available (will display inline in WhatsApp)
            if image_url:
                try:
                    # Send image as separate message with caption
                    image_caption = f"{item_name} - ₦{item_price:,}"
                    image_result = meta_service.send_message(
                        to=from_number,
                        message=image_url,
                        message_type='image',
                        caption=image_caption
                    )
                    if image_result.get('success'):
                        logger.info(f"Food image sent successfully for {vendor_name}")
                    else:
                        logger.warning(f"Failed to send food image for {vendor_name}: {image_result.get('message')}")
                except Exception as e:
                    logger.error(f"Error sending food image for {vendor_name}: {str(e)}")

        # Restaurant name and rating
        message += f"{i}. {vendor_name}"
        if rating > 0:
            message += f" ⭐ {rating}/5"
            if total_reviews > 0:
                message += f" ({total_reviews} reviews)"
        message += f"\n"

        # Delivery time
        message += f"   🚀 {delivery_time}\n"

        # Add menu item details if available
        if food_images and len(food_images) > 0:
            sample_item = food_images[0]
            item_name = sample_item.get('dish_name', 'Signature dish')
            item_price = sample_item.get('price', 0)
            if item_price > 0:
                message += f"   🍽️ {item_name} - ₦{item_price:,}\n"

        message += "\n"  # Extra spacing between restaurants

    message += f"Which restaurant would you like to order {food_type} from? Just tell me the number!"
    return message


def _format_vendors_message(food_type, vendors):
    """Format vendors from the search API into a WhatsApp message with rich details and images"""
    emoji = _get_food_emoji(food_type)
    message = f"{emoji} Here are great {food_type} restaurants:\n\n"

    for i, vendor in enumerate(vendors[:3], 1):  # Show top 3 for better readability
        name = vendor.get('business_name', 'Restaurant')
        rating = vendor.get('rating', 0)
        delivery_time = vendor.get('delivery_time', '30-45 min')
        logo_url = vendor.get('logo', '')
        price_range = vendor.get('price_range', {})
        total_reviews = vendor.get('total_reviews', 0)

        # Sample menu item with image (if available)
        food_images = vendor.get('food_images', [])
        if food_images and len(food_images) > 0:
            sample_item = food_images[0]  # First item is usually featured
            item_name = sample_item.get('dish_name', 'Signature dish')
            item_price = sample_item.get('price', 0)
            image_url = sample_item.get('image', '')

            # Send actual image message if available (will display inline in WhatsApp)
            if image_url:
                try:
                    # Send image as separate message with caption
                    image_caption = f"{item_name} - ₦{item_price:,}"
                    image_result = meta_service.send_message(
                        to=from_number,
                        message=image_url,
                        message_type='image',
                        caption=image_caption
                    )
                    if image_result.get('success'):
                        logger.info(f"Food image sent successfully for {vendor_name}")
                    else:
                        logger.warning(f"Failed to send food image for {vendor_name}: {image_result.get('message')}")
                except Exception as e:
                    logger.error(f"Error sending food image for {vendor_name}: {str(e)}")

        # Restaurant name and rating
        message += f"{i}. {name}"
        if rating > 0:
            message += f" ⭐ {rating}/5"
            if total_reviews > 0:
                message += f" ({total_reviews} reviews)"
        message += f"\n"

        # Delivery time
        message += f"   🚀 {delivery_time}\n"

        # Price range if available
        if price_range and isinstance(price_range, dict):
            min_price = price_range.get('min')
            max_price = price_range.get('max')
            currency = price_range.get('currency', 'NGN')
            if min_price is not None and max_price is not None:
                message += f"   💰 ₦{min_price:,} - ₦{max_price:,}\n"

        # Sample menu item details
        if food_images and len(food_images) > 0:
            sample_item = food_images[0]
            item_name = sample_item.get('dish_name', 'Signature dish')
            item_price = sample_item.get('price', 0)
            if item_price > 0:
                message += f"   🍽️ {item_name} - ₦{item_price:,}\n"

        message += "\n"  # Extra spacing between restaurants

    message += f"Which restaurant would you like to order {food_type} from? Just tell me the number!"
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
    """Get intelligent fallback message when requested food type is not available - MULTI-LEVEL FALLBACK STRATEGY"""
    try:
        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
        emoji = _get_food_emoji(food_type)

        # LEVEL 1: Try to find ANY vendors with ANY food (most inclusive)
        try:
            api_url = f"{base_url}/api/user/vendors/search/"
            response = requests.get(api_url, params={'q': '', 'page_size': 6}, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('vendors') and len(data.get('vendors', [])) > 0:
                    vendors = data['vendors']

                    # Extract unique food categories from available vendors
                    available_categories = set()
                    for vendor in vendors:
                        if vendor.get('business_category'):
                            # Split categories by common separators
                            categories = vendor['business_category'].replace(',', '|').replace(';', '|').replace('/', '|').split('|')
                            for cat in categories:
                                cat = cat.strip().lower()
                                if cat and len(cat) > 2:  # Avoid very short categories
                                    available_categories.add(cat)

                    if available_categories:
                        # Determine current time category for better suggestions
                        current_category = None
                        time_range = ""
                        if 6 <= current_hour < 11:
                            current_category = 'morning'
                            time_range = 'breakfast time'
                        elif 11 <= current_hour < 17:
                            current_category = 'afternoon'
                            time_range = 'lunch time'
                        elif 17 <= current_hour < 21:
                            current_category = 'evening'
                            time_range = 'dinner time'
                        else:
                            current_category = 'night'
                            time_range = 'late night'

                        message = f"{emoji} Sorry, we don't currently have {food_type} available.\n\n"
                        message += f"🌅 Since it's {time_range}, here are some delicious options we have:\n\n"

                        # Show up to 4 available categories
                        for i, category in enumerate(sorted(list(available_categories))[:4], 1):
                            cat_emoji = _get_food_emoji(category)
                            message += f"{i}. {cat_emoji} {category.title()}\n"

                        message += f"\nWould you like to explore any of these options? Just tell me which one!"
                        return message

        except Exception as e:
            logger.warning(f"Level 1 fallback failed: {str(e)}")

        # LEVEL 2: Try recommendations API for broader suggestions
        try:
            api_url = f"{base_url}/api/user/recommendations/"
            response = requests.get(api_url, params={'limit': 3}, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('recommendations') and len(data.get('recommendations', [])) > 0:
                    recommendations = data['recommendations']

                    message = f"{emoji} Sorry, we don't have {food_type} right now.\n\n"
                    message += f"🍽️ But here are some great restaurants we recommend:\n\n"

                    for i, rec in enumerate(recommendations[:3], 1):
                        vendor_name = rec.get('business_name', 'Restaurant')
                        category = rec.get('business_category', 'Food')
                        delivery_time = rec.get('delivery_time', '30-45 min')

                        message += f"{i}. {vendor_name} ({category}) - {delivery_time}\n"

                    message += f"\nWould you like to see what they offer? Just tell me the number!"
                    return message

        except Exception as e:
            logger.warning(f"Level 2 fallback failed: {str(e)}")

        # LEVEL 3: Ultimate fallback - hardcoded but time-appropriate suggestions
        current_category = None
        time_range = ""
        if 6 <= current_hour < 11:
            current_category = 'morning'
            time_range = 'breakfast time'
            suggestions = ['breakfast', 'coffee', 'tea', 'local cuisine']
        elif 11 <= current_hour < 17:
            current_category = 'afternoon'
            time_range = 'lunch time'
            suggestions = ['lunch', 'rice', 'pasta', 'sandwich', 'local cuisine']
        elif 17 <= current_hour < 21:
            current_category = 'evening'
            time_range = 'dinner time'
            suggestions = ['dinner', 'grilled', 'traditional', 'fast food']
        else:
            current_category = 'night'
            time_range = 'late night'
            suggestions = ['snack', 'soup', 'light meal', 'beverages']

        message = f"{emoji} Sorry, we don't currently have {food_type} available.\n\n"
        message += f"🌅 Since it's {time_range}, here are some great options:\n\n"

        for i, suggestion in enumerate(suggestions[:4], 1):
            sugg_emoji = _get_food_emoji(suggestion)
            message += f"{i}. {sugg_emoji} {suggestion.title()}\n"

        message += f"\nWould you like to try any of these instead?"
        return message

    except Exception as e:
        logger.error(f"Error in _get_time_based_no_food_message: {str(e)}")
        emoji = _get_food_emoji(food_type)
        return f"{emoji} Sorry, we don't currently have {food_type} available in our system. Please try again later or contact support."


def _get_available_food_types():
    """Get available food types from the backend - IMPROVED VERSION"""
    try:
        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')

        # Try to get available cuisines from the search API with parameters that trigger a search
        try:
            api_url = f"{base_url}/api/user/vendors/search/"
            # Get vendors without specific filters to get as many as possible
            response = requests.get(api_url, params={'q': ''}, timeout=5)  # Empty query to get all vendors

            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('vendors') and len(data.get('vendors', [])) > 0:
                    # Extract unique cuisines from vendors
                    cuisines = set()
                    for vendor in data['vendors']:
                        if vendor.get('business_category') and vendor['business_category'].strip():
                            cuisines.add(vendor['business_category'].strip().lower())
                    if cuisines:  # Only return if we found some cuisines
                        return list(cuisines)[:6]  # Return up to 6 cuisines
        except Exception as e:
            logger.warning(f"Could not fetch available cuisines: {str(e)}")

        # Fallback: return some common food types that might be in the system
        logger.warning("Could not fetch food types from backend, using fallback")
        return ['local cuisine', 'fast food', 'restaurant', 'food']

    except Exception as e:
        logger.error(f"Error getting available food types: {str(e)}")
        # Return fallback instead of empty list to prevent the error
        return ['local cuisine', 'fast food', 'restaurant', 'food']


def _process_order_confirmation(phone_number, meta_service, user=None):
    """Process order confirmation - create order if confirming dish selection, or ask about completion"""
    try:
        from bestyy.restaurant_features.order.models import Order, OrderItem
        from bestyy.restaurant_features.product.models import Product
        from bestyy.communication.whatsapp.models import WhatsAppConversation
        from decimal import Decimal
        import logging
        logger = logging.getLogger(__name__)

        # Get conversation to access pending dish
        conversation = WhatsAppConversation.objects.filter(phone_number=phone_number).first()

        # Look for recent awaiting orders
        thirty_minutes_ago = timezone.now() - timedelta(minutes=30)
        recent_order = Order.objects.filter(
            status='awaiting',
            created_at__gte=thirty_minutes_ago
        ).order_by('-created_at').first()

        if recent_order:
            # Add pending dish to existing order if available
            if conversation and conversation.context_data.get('pending_dish'):
                pending = conversation.context_data['pending_dish']
                
                # Check for order conflicts with user preferences
                try:
                    from .ai_first_processor import AIFirstMessageProcessor
                    processor = AIFirstMessageProcessor(
                        conversation.id,
                        user_id=str(user.id) if user else None,
                        user_name=user.get_full_name() if user and hasattr(user, 'get_full_name') else None
                    )
                    conflict_warning = processor.check_order_for_conflicts([pending['dish_name']])
                    
                    if conflict_warning:
                        # Store conflict state in context
                        conversation.context_data['order_conflict'] = {
                            'item': pending['dish_name'],
                            'order_id': recent_order.id,
                            'pending_dish': pending
                        }
                        conversation.save()
                        return conflict_warning
                except Exception as e:
                    logger.warning(f"Could not check order conflicts: {str(e)}")
                
                try:
                    product = Product.objects.get(id=pending['product_id'])
                    # Create OrderItem
                    OrderItem.objects.create(
                        order=recent_order,
                        product=product,
                        quantity=1,
                        price=Decimal(pending['price'])
                    )
                    logger.info(f"Added OrderItem {pending['dish_name']} to order {recent_order.id}")
                    
                    # Update order total
                    from decimal import Decimal
                    recent_order.total_amount = Decimal(sum(item.price * item.quantity for item in recent_order.items.all()))
                    recent_order.save()
                    
                    # Clear pending dish
                    conversation.context_data.pop('pending_dish', None)
                    conversation.save()
                except Product.DoesNotExist:
                    logger.error(f"Product {pending['product_id']} not found")
            
            # There is an order to confirm - ask if they want anything else
            confirmation_message = f"🍽️ Got it! I've added that to your order.\n\n"
            confirmation_message += f"❓ Is this all you want, or would you like to order something else?\n\n"
            confirmation_message += f"💬 Reply:\n"
            confirmation_message += f"• 'YES' or 'DONE' - Complete order\n"
            confirmation_message += f"• 'NO' or 'MORE' - Add more items\n"
            confirmation_message += f"• Tell me what else you'd like!"

            return confirmation_message
        else:
            # No existing order - create new order with the pending dish
            if not conversation or not conversation.context_data.get('pending_dish'):
                # No pending dish - can't create order
                return "I don't see a dish selected. Please tell me what you'd like to order!"
            
            pending = conversation.context_data['pending_dish']
            from bestyy.core_features.user.models import VendorProfile
            
            try:
                vendor = VendorProfile.objects.get(id=pending['vendor_id'])
                product = Product.objects.get(id=pending['product_id'])
                
                # Create order with the selected dish
                order = Order.objects.create(
                    customer=user,
                    vendor=vendor,
                    status='awaiting',
                    total_amount=Decimal(pending['price']),
                )
                
                # Create OrderItem
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=1,
                    price=Decimal(pending['price'])
                )
                
                logger.info(f"Created order {order.id} with item {pending['dish_name']} for user {user}, phone {phone_number}")
                
                # Clear pending dish
                conversation.context_data.pop('pending_dish', None)
                conversation.save()

                # Now ask if they want anything else
                confirmation_message = f"🍽️ Perfect! I've created your order with {vendor.business_name}.\n\n"
                confirmation_message += f"❓ Is this all you want, or would you like to order something else?\n\n"
                confirmation_message += f"💬 Reply:\n"
                confirmation_message += f"• 'YES' or 'DONE' - Complete order\n"
                confirmation_message += f"• 'NO' or 'MORE' - Add more items\n"
                confirmation_message += f"• Tell me what else you'd like!"

                return confirmation_message
                
            except (VendorProfile.DoesNotExist, Product.DoesNotExist) as e:
                logger.error(f"Error creating order: {str(e)}")
                return "Sorry, there was an issue with the selected dish. Please try selecting again."

    except Exception as e:
        logger.error(f"Error processing order confirmation: {str(e)}")
        return "Sorry, there was an error processing your order. Please try again or contact support."


def _handle_vendor_order_response(content, phone_number, meta_service, user, vendor_profile):
    """Handle vendor responses to order notifications (ACCEPT/REJECT/READY)"""
    import logging
    import re
    logger = logging.getLogger(__name__)
    
    try:
        from bestyy.restaurant_features.order.models import Order
        from bestyy.core_features.user.services.vendor_ready_service import VendorReadyService
        from bestyy.core_features.user.utils.websocket_notifications import send_vendor_notification
        
        logger.info(f"🔍 Checking vendor command: '{content}' for vendor {vendor_profile.business_name}")
        
        # Check for ACCEPT/REJECT responses
        if re.search(r'\b(accept|yes|okay|ok|confirm|take)\b', content):
            logger.info(f"✅ Detected ACCEPT command")
            # Vendor accepts order - find most recent pending order
            pending_order = Order.objects.filter(
                vendor=vendor_profile,
                status='confirmed',
                payment_status=True
            ).order_by('-created_at').first()
            
            if not pending_order:
                return None  # No pending order, let normal flow handle it
            
            # Mark order as accepted/preparing
            pending_order.status = 'preparing'
            pending_order.preparing_at = timezone.now()
            pending_order.save()
            
            logger.info(f"✅ Vendor {vendor_profile.id} accepted order {pending_order.id}")
            
            # Notify customer
            if pending_order.customer:
                customer_phone = _get_customer_phone(pending_order.customer)
                if customer_phone:
                    customer_msg = f"✅ *Order Accepted!*\n\n"
                    customer_msg += f"📦 Order #{pending_order.order_number}\n"
                    customer_msg += f"🏪 {vendor_profile.business_name} is preparing your order!\n\n"
                    customer_msg += f"👨‍🍳 Estimated time: 30-45 minutes\n"
                    customer_msg += f"🚗 You'll be notified when courier is assigned.\n\n"
                    customer_msg += f"💬 Reply 'STATUS' to check progress."
                    
                    try:
                        meta_service.send_message(to=customer_phone, message=customer_msg)
                        logger.info(f"✅ Customer notified of order acceptance")
                    except Exception as e:
                        logger.error(f"Error notifying customer: {str(e)}")
            
            # Send websocket update
            try:
                send_vendor_notification(
                    vendor_id=vendor_profile.id,
                    notification_type='order_accepted',
                    data={'order_id': str(pending_order.id), 'order_number': pending_order.order_number}
                )
            except Exception as e:
                logger.error(f"Error sending websocket: {str(e)}")
            
            return f"""✅ *Order Accepted!*

📦 Order #{pending_order.order_number}
💰 Total: ₦{pending_order.total_amount:,.0f}

🧑‍🍳 Please start preparing the order.

When food is ready, reply:
*READY* or *ORDER READY*

This will:
• Notify the customer
• Assign nearest courier automatically
• Send pickup code to courier

⏰ Target: 30-45 minutes"""

        elif re.search(r'\b(reject|no|cant|cannot|unable|decline)\b', content):
            logger.info(f"❌ Detected REJECT command")
            # Vendor rejects order
            pending_order = Order.objects.filter(
                vendor=vendor_profile,
                status='confirmed',
                payment_status=True
            ).order_by('-created_at').first()
            
            if not pending_order:
                return None
            
            # Mark as cancelled
            pending_order.status = 'cancelled'
            pending_order.cancelled_at = timezone.now()
            pending_order.save()
            
            logger.warning(f"⚠️ Vendor {vendor_profile.id} rejected order {pending_order.id}")
            
            # Notify customer
            if pending_order.customer:
                customer_phone = _get_customer_phone(pending_order.customer)
                if customer_phone:
                    customer_msg = f"❌ *Order Update*\n\n"
                    customer_msg += f"📦 Order #{pending_order.order_number}\n\n"
                    customer_msg += f"Unfortunately, {vendor_profile.business_name} cannot fulfill your order at this time.\n\n"
                    customer_msg += f"💰 Refund: ₦{pending_order.total_amount:,.0f}\n"
                    customer_msg += f"Your payment will be refunded within 24 hours.\n\n"
                    customer_msg += f"💬 We apologize for the inconvenience!"
                    
                    try:
                        meta_service.send_message(to=customer_phone, message=customer_msg)
                    except Exception as e:
                        logger.error(f"Error notifying customer: {str(e)}")
            
            return f"❌ Order rejected. Customer has been notified and will be refunded."

        elif re.search(r'\b(ready|order ready|done|prepared|finished)\b', content):
            logger.info(f"🎉 Detected READY command")
            # Order is ready - assign courier
            ready_order = Order.objects.filter(
                vendor=vendor_profile,
                status='preparing'
            ).order_by('-preparing_at').first()
            
            if not ready_order:
                return "⚠️ No preparing orders found. Please accept an order first."
            
            # Mark as ready
            ready_order.status = 'ready'
            ready_order.ready_at = timezone.now()
            ready_order.save()
            
            logger.info(f"✅ Order {ready_order.id} marked as ready by vendor")
            
            # Assign courier
            try:
                ready_service = VendorReadyService()
                assignment_result = ready_service._assign_courier_to_order(ready_order, vendor_profile)
                
                if assignment_result.get('success'):
                    courier_name = assignment_result.get('courier_name', 'Courier')
                    
                    # Notify customer
                    if ready_order.customer:
                        customer_phone = _get_customer_phone(ready_order.customer)
                        if customer_phone:
                            customer_msg = f"🎉 *Order Ready!*\n\n"
                            customer_msg += f"📦 Order #{ready_order.order_number}\n"
                            customer_msg += f"🏪 {vendor_profile.business_name}\n\n"
                            customer_msg += f"🚗 Courier assigned: {courier_name}\n"
                            customer_msg += f"📍 Your order is on the way!\n\n"
                            customer_msg += f"⏰ Est. delivery: 15-20 minutes"
                            
                            try:
                                meta_service.send_message(to=customer_phone, message=customer_msg)
                            except Exception as e:
                                logger.error(f"Error notifying customer: {str(e)}")
                    
                    return f"""🎉 *Order Marked as Ready!*

📦 Order #{ready_order.order_number}

✅ Courier assigned: {courier_name}
🔐 Pickup Code: *{ready_order.pickup_code}*

The courier will arrive shortly to collect the order.
Please verify the pickup code before handing over."""

                else:
                    return f"""✅ Order marked as ready!

⚠️ No courier available at the moment.
We're finding the nearest courier.

🔐 Pickup Code: *{ready_order.pickup_code}*

You'll be notified when courier is assigned."""
                    
            except Exception as e:
                logger.error(f"Error assigning courier: {str(e)}")
                return f"✅ Order ready! Pickup code: *{ready_order.pickup_code}*\n\n⚠️ Courier assignment in progress..."
        
        # Not a vendor command, return None to continue normal flow
        logger.info(f"ℹ️ Message '{content}' is not a vendor command (ACCEPT/REJECT/READY)")
        return None
        
    except Exception as e:
        logger.error(f"Error handling vendor order response: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def _get_customer_phone(customer):
    """Get customer's WhatsApp phone number"""
    try:
        from bestyy.communication.whatsapp.models import WhatsAppConversation
        conv = WhatsAppConversation.objects.filter(user=customer).first()
        if conv:
            return conv.phone_number
        # Try to get from user profile
        if hasattr(customer, 'profile') and customer.profile.phone:
            return customer.profile.phone
    except Exception:
        pass
    return None


def _check_order_status(phone_number, user=None, conversation=None):
    """Check the status of the current or most recent order"""
    try:
        from bestyy.restaurant_features.order.models import Order
        import logging
        logger = logging.getLogger(__name__)

        # Try to get order from conversation context first
        order = None
        if conversation and conversation.context_data.get('current_order_id'):
            try:
                order = Order.objects.get(id=conversation.context_data['current_order_id'])
            except Order.DoesNotExist:
                pass
        
        # If no order in context, get most recent order for user
        if not order and user:
            order = Order.objects.filter(customer=user).order_by('-created_at').first()
        
        if not order:
            return "📦 You don't have any orders yet.\n\n💬 Say 'I want jollof rice' to start ordering!"
        
        # Format status message
        status_emojis = {
            'awaiting': '⏳',
            'pending': '⏳',
            'confirmed': '✅',
            'preparing': '🧑‍🍳',
            'ready': '🎉',
            'out_for_delivery': '🚗',
            'delivered': '✅',
            'cancelled': '❌'
        }
        
        emoji = status_emojis.get(order.status, '📦')
        
        status_msg = f"{emoji} *Order Status*\n\n"
        status_msg += f"📦 Order #{order.order_number}\n"
        status_msg += f"🏪 {order.vendor.business_name if order.vendor else 'Restaurant'}\n"
        status_msg += f"💰 Total: ₦{float(order.total_amount):,.0f}\n"
        status_msg += f"📍 Deliver to: {order.delivery_address or 'Pending address'}\n\n"
        
        # Status-specific messages
        if order.status == 'awaiting':
            status_msg += f"⏳ *Status:* Awaiting Payment\n"
            status_msg += f"💳 Please complete payment to confirm your order."
        elif order.status == 'pending':
            status_msg += f"⏳ *Status:* Pending Confirmation\n"
            status_msg += f"💬 Reply 'PAID' once you've made the transfer."
        elif order.status == 'confirmed':
            status_msg += f"✅ *Status:* Order Confirmed\n"
            if order.pickup_code:
                status_msg += f"🔐 Pickup Code: {order.pickup_code}\n"
            status_msg += f"🧑‍🍳 Your food is being prepared!"
        elif order.status == 'preparing':
            status_msg += f"🧑‍🍳 *Status:* Being Prepared\n"
            status_msg += f"👨‍🍳 The chef is working on your order!"
        elif order.status == 'ready':
            status_msg += f"🎉 *Status:* Ready for Pickup\n"
            status_msg += f"🚗 Waiting for courier assignment."
        elif order.status == 'out_for_delivery':
            status_msg += f"🚗 *Status:* Out for Delivery\n"
            if order.courier:
                status_msg += f"🚴 Courier: {order.courier.user.get_full_name()}\n"
            status_msg += f"📍 Your order is on the way!"
        elif order.status == 'delivered':
            status_msg += f"✅ *Status:* Delivered\n"
            status_msg += f"🎉 Thanks for using Bestyy!"
        elif order.status == 'cancelled':
            status_msg += f"❌ *Status:* Cancelled\n"
        
        # Add estimated time if not delivered
        if order.status not in ['delivered', 'cancelled']:
            status_msg += f"\n⏰ Est. time: 30-45 minutes"
        
        return status_msg
        
    except Exception as e:
        logger.error(f"Error checking order status: {str(e)}")
        return "❌ Error checking status. Please try again."


def _handle_paid_confirmation(phone_number, meta_service, user=None, conversation=None):
    """Handle PAID confirmation - skip payment verification for testing"""
    try:
        from bestyy.restaurant_features.order.models import Order
        import logging
        import random
        logger = logging.getLogger(__name__)

        # Get the order from conversation context
        if not conversation or not conversation.context_data.get('current_order_id'):
            return "❌ I couldn't find your order. Please try placing a new order."
        
        order_id = conversation.context_data['current_order_id']
        
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            logger.error(f"Order {order_id} not found for paid confirmation")
            return "❌ Order not found. Please contact support."
        
        # Check if already paid
        if order.payment_status:
            return f"✅ This order was already confirmed!\n\nOrder #{order.order_number} is being prepared."
        
        # Mark order as paid (skip actual payment verification)
        logger.info(f"🧪 TEST MODE: Auto-confirming payment for order {order.id}")
        
        order.payment_status = True
        order.payment_confirmed = True
        order.payment_confirmed_at = timezone.now()
        order.status = 'confirmed'
        order.confirmed_at = timezone.now()
        
        # Generate pickup OTP for courier
        pickup_otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        order.pickup_code = pickup_otp
        order.save()
        
        logger.info(f"✅ Order {order.id} confirmed with pickup code {pickup_otp}")
        
        # Notify vendor about new order
        try:
            from bestyy.core_features.user.services.vendor_order_notification_service import VendorOrderNotificationService
            vendor_notified = VendorOrderNotificationService.notify_vendor_new_order(order)
            if vendor_notified:
                logger.info(f"✅ Vendor notified for order {order.id}")
            else:
                logger.warning(f"⚠️ Failed to notify vendor for order {order.id}")
        except Exception as e:
            logger.error(f"❌ Error notifying vendor: {str(e)}")
        
        # Send websocket notification to vendor
        try:
            from bestyy.core_features.user.utils.websocket_notifications import send_vendor_notification
            if order.vendor:
                send_vendor_notification(
                    vendor_id=order.vendor.id,
                    notification_type='new_order',
                    data={
                        'order_id': str(order.id),
                        'order_number': order.order_number,
                        'customer_name': user.get_full_name() if user else 'Customer',
                        'total_amount': float(order.total_amount),
                        'items_count': order.items.count(),
                        'delivery_address': order.delivery_address,
                        'created_at': order.created_at.isoformat()
                    }
                )
                logger.info(f"✅ Websocket notification sent to vendor for order {order.id}")
        except Exception as e:
            logger.error(f"❌ Error sending websocket to vendor: {str(e)}")
        
        # Try to assign courier (if vendor auto-accepts or system auto-assigns)
        try:
            from bestyy.core_features.user.services.vendor_ready_service import VendorReadyService
            ready_service = VendorReadyService()
            # This will check if courier assignment is needed and assign
            assignment_result = ready_service._assign_courier_to_order(order, order.vendor)
            if assignment_result.get('success'):
                logger.info(f"✅ Courier assigned for order {order.id}: {assignment_result.get('courier_name')}")
            else:
                logger.info(f"ℹ️ Courier assignment pending for order {order.id}")
        except Exception as e:
            logger.error(f"❌ Error assigning courier: {str(e)}")
        
        # Generate beautiful receipt
        receipt_msg = "🎉 *Payment Successful!*\n\n"
        receipt_msg += f"*Order #{order.order_number}*\n"
        receipt_msg += f"📅 {order.created_at.strftime('%B %d, %Y at %I:%M %p')}\n"
        receipt_msg += f"🏪 *{order.vendor.business_name if order.vendor else 'Restaurant'}*\n\n"
        
        # Items list
        receipt_msg += "*Items Ordered:*\n"
        order_items = order.items.all()
        if order_items.exists():
            for item in order_items:
                item_total = float(item.price) * item.quantity
                if item.quantity > 1:
                    receipt_msg += f"• {item.quantity}x {item.product.name if item.product else item.item_name} - ₦{item_total:,.2f}\n"
                else:
                    receipt_msg += f"• {item.product.name if item.product else item.item_name} - ₦{item_total:,.2f}\n"
        else:
            receipt_msg += f"• Order Total - ₦{float(order.total_amount):,.2f}\n"
        
        receipt_msg += "\n"
        receipt_msg += f"*Subtotal:* ₦{float(order.subtotal or order.total_amount):,.2f}\n"
        if order.delivery_fee:
            receipt_msg += f"*Delivery Fee:* ₦{float(order.delivery_fee):,.2f}\n"
        receipt_msg += f"💰 *Total: ₦{float(order.total_amount):,.2f}*\n\n"
        
        receipt_msg += f"💳 *Paid via Bank Transfer*\n\n"
        
        # Delivery address
        receipt_msg += "*📍 Delivery Address:*\n"
        receipt_msg += f"{order.delivery_address}\n\n"
        
        # Pickup code
        receipt_msg += f"🔐 *Pickup Code:* {pickup_otp}\n"
        receipt_msg += f"_(Share this with courier on delivery)_\n\n"
        
        # Status info
        receipt_msg += "━━━━━━━━━━━━━━━━━━\n\n"
        receipt_msg += "🧑‍🍳 *Your order is being prepared!*\n"
        receipt_msg += "⏱️ Estimated time: 30-45 minutes\n"
        receipt_msg += "🚗 We'll notify you when courier is assigned\n\n"
        receipt_msg += "💬 Reply *STATUS* to check order status\n\n"
        receipt_msg += "_Thank you for choosing Bestyy!_ 🚀"
        
        return receipt_msg
        
    except Exception as e:
        logger.error(f"Error handling paid confirmation: {str(e)}")
        return "❌ Error confirming payment. Please try again or contact support."


def _handle_order_completion_response(content, phone_number, meta_service, user=None, conversation=None):
    """Handle responses to 'Is this all?' question"""
    content_lower = content.lower().strip()

    if content_lower in ['yes', 'done', 'complete', 'finish', 'all done', 'thats all']:
        # User wants to complete the order
        return _finalize_order(conversation, phone_number, meta_service, user)
    elif content_lower in ['no', 'more', 'add', 'something else', 'another']:
        # User wants to add more items
        more_message = f"🍽️ What else would you like to order?\n\n"
        more_message += f"💬 Tell me what you're craving! For example:\n"
        more_message += f"• 'I want pizza'\n"
        more_message += f"• 'Burger and fries'\n"
        more_message += f"• 'Chicken soup'\n\n"
        more_message += f"Or reply 'DONE' when you're finished!"
        return more_message
    else:
        # User specified another item - treat as new order request
        return _process_additional_order_item(content, phone_number, meta_service, user)


def _finalize_order(conversation, phone_number, meta_service, user=None):
    """Finalize the complete order - collect address FIRST to calculate delivery fee"""
    try:
        from bestyy.restaurant_features.order.models import Order
        from bestyy.restaurant_features.product.models import Product as MenuItem
        import logging
        logger = logging.getLogger(__name__)

        # Check if an order already exists for this session (check both awaiting and recent pending)
        thirty_minutes_ago = timezone.now() - timedelta(minutes=30)
        existing_order = Order.objects.filter(
            status__in=['awaiting', 'pending'],
            created_at__gte=thirty_minutes_ago
        ).order_by('-created_at').first()
        
        # If we found a pending order, reset it to awaiting so we can update it with address
        if existing_order and existing_order.status == 'pending' and not existing_order.delivery_address:
            existing_order.status = 'awaiting'
            existing_order.save()
            logger.info(f"Reset order {existing_order.id} from pending to awaiting for address collection")

        if not existing_order:
            # No order found - user needs to select dishes first
            logger.error(f"No order found for user {user}, phone {phone_number}")
            return "I don't see any items in your order yet. Please tell me what you'd like to order!"
        
        order = existing_order
        logger.info(f"Using existing order {order.id} for user {user}, phone {phone_number}")
        
        # Recalculate total from OrderItems
        if order.items.exists():
            from decimal import Decimal
            order.total_amount = Decimal(sum(item.price * item.quantity for item in order.items.all()))
            order.save()
            logger.info(f"Recalculated order {order.id} total: ₦{order.total_amount}")

        # Store order reference in conversation for later retrieval
        if not conversation:
            # Create or get conversation if it doesn't exist
            from bestyy.communication.whatsapp.models import WhatsAppConversation
            conversation, _ = WhatsAppConversation.objects.get_or_create(
                phone_number=phone_number,
                defaults={'user': user, 'state': 'onboarded'}
            )
        
        conversation.context_data = conversation.context_data or {}
        conversation.context_data['current_order_id'] = str(order.id)
        conversation.awaiting_address = True
        conversation.save()
        logger.info(f"Stored order {order.id} in conversation {conversation.id}, awaiting address")
        
        # ASK FOR ADDRESS FIRST (before showing order summary)
        # This allows us to calculate delivery fee accurately

        address_message = f"📍 *Almost there!* To calculate your delivery fee and show the final total, I need your delivery address.\n\n"
        address_message += f"🏠 *Please provide your full delivery address:*\n\n"
        address_message += f"💡 Example: '123 Lagos Street, Ikeja, Lagos' or 'Victoria Island, Lagos'\n\n"
        address_message += f"🔍 I'll calculate accurate delivery fees based on your location!"

        return address_message

    except Exception as e:
        logger.error(f"Error starting order finalization: {str(e)}")
        return "Sorry, there was an error processing your order. Please try again."


def _process_delivery_address(address_text, phone_number, meta_service, user=None, conversation=None):
    """Process and validate delivery address using Google Maps"""
    print(f"DEBUG: Processing delivery address: '{address_text}'")
    print(f"DEBUG: User: {user}, Conversation: {conversation}, Phone: {phone_number}")

    try:
        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')

        # Validate address using location services API
        geocode_url = f"{base_url}/api/user/location/geocode/"
        print(f"DEBUG: Calling geocode API: {geocode_url}")

        response = requests.post(geocode_url, json={'address': address_text}, timeout=10)
        print(f"DEBUG: Geocode API response status: {response.status_code}")

        if response.status_code == 200:
            location_data = response.json()
            print(f"DEBUG: Geocode API response: {location_data}")

            if location_data.get('success'):
                # Address validated successfully - extract from location object
                location_info = location_data.get('location', {})
                validated_address = location_info.get('formatted_address', address_text)
                latitude = location_info.get('latitude')
                longitude = location_info.get('longitude')

                print(f"DEBUG: Address validated: {validated_address}, lat: {latitude}, lng: {longitude}")

                # Clear awaiting_address state since we successfully processed the address
                if conversation:
                    conversation.awaiting_address = False
                    conversation.save()

                # Now calculate delivery and show order summary with payment
                return _show_order_summary_with_payment(validated_address, latitude, longitude, phone_number, meta_service, user, conversation)
            else:
                # Address validation failed
                error_msg = location_data.get('error', 'Unknown error')
                print(f"DEBUG: Address validation failed: {error_msg}")

                error_message = f"❌ I couldn't verify that address. {error_msg}\n\n"
                error_message += f"💡 Please try:\n"
                error_message += f"• Using a more complete address\n"
                error_message += f"• Including landmarks or LGA\n"
                error_message += f"• Example: 'Plot 123, Lagos Street, Ikeja, Lagos'\n\n"
                error_message += f"Please provide a different address!"
                return error_message
        else:
            # API call failed - fallback to basic validation
            print(f"DEBUG: Geocode API failed with status {response.status_code}, falling back to basic validation")

            # Clear awaiting_address state since we're proceeding with the address
            if conversation:
                conversation.awaiting_address = False
                conversation.save()

            return _show_order_summary_with_payment(address_text, None, None, phone_number, meta_service, user, conversation)

    except Exception as e:
        logger.error(f"Error processing delivery address: {str(e)}")
        print(f"DEBUG: Exception in address processing: {str(e)}")

        # Clear awaiting_address state since we're proceeding with the address despite the error
        if conversation:
            conversation.awaiting_address = False
            conversation.save()

        # Fallback - proceed without validation
        return _show_order_summary_with_payment(address_text, None, None, phone_number, meta_service, user, conversation)


def _show_order_summary_with_payment(validated_address, latitude, longitude, phone_number, meta_service, user=None, conversation=None):
    """Show complete order summary with calculated delivery fees and Paystack PwT payment details"""
    print(f"DEBUG: Showing order summary for address: '{validated_address}', lat: {latitude}, lng: {longitude}")
    print(f"DEBUG: Conversation: {conversation}, User: {user}, Phone: {phone_number}")
    try:
        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')

        # Find the most recent awaiting order for this user or phone number
        from bestyy.restaurant_features.order.models import Order
        import logging
        logger = logging.getLogger(__name__)

        print(f"DEBUG: Looking for order - user: {user}, phone: {phone_number}")

        # Try to get order from conversation context first (MOST RELIABLE)
        awaiting_order = None
        
        if conversation and conversation.context_data and 'current_order_id' in conversation.context_data:
            order_id = conversation.context_data['current_order_id']
            print(f"DEBUG: Found order ID in conversation context: {order_id}")
            try:
                # Check for both 'awaiting' and 'pending' status since order might have been updated
                awaiting_order = Order.objects.filter(
                    id=order_id,
                    status__in=['awaiting', 'pending']
                ).first()
                if awaiting_order:
                    print(f"DEBUG: Successfully retrieved order from context: {awaiting_order} (status: {awaiting_order.status})")
                else:
                    logger.error(f"Order {order_id} from context not found")
                    print(f"DEBUG: Order {order_id} not found")
            except Exception as e:
                logger.error(f"Error retrieving order {order_id}: {str(e)}")
                print(f"DEBUG: Error retrieving order: {str(e)}")
        
        # Fallback: try to find by user if available - check both awaiting and recent pending
        if not awaiting_order and user:
            awaiting_order = Order.objects.filter(
                customer=user,
                status__in=['awaiting', 'pending'],
                delivery_address__isnull=True  # Only orders without address yet
            ).order_by('-created_at').first()
            print(f"DEBUG: Found order by user {user}: {awaiting_order}")

        # If no user-specific order found, try to find recent orders that might belong to this conversation
        if not awaiting_order:
            # Look for recent orders (within last 30 minutes) that might be from this session
            thirty_minutes_ago = timezone.now() - timedelta(minutes=30)
            awaiting_order = Order.objects.filter(
                status__in=['awaiting', 'pending'],
                delivery_address__isnull=True,  # Only orders without address yet
                created_at__gte=thirty_minutes_ago
            ).order_by('-created_at').first()
            print(f"DEBUG: Found recent order: {awaiting_order}")

        # Debug: Check what orders exist
        if not awaiting_order:
            recent_orders = Order.objects.filter(
                created_at__gte=timezone.now() - timedelta(minutes=60)
            ).order_by('-created_at')[:5]
            print(f"DEBUG: Recent orders in last 60 min: {[(f'{o.id} ({o.status}) - {o.customer} to {o.vendor}') for o in recent_orders]}")

        if not awaiting_order:
            logger.warning(f"No awaiting order found for user {user}, phone {phone_number}")
            # Debug: Check what orders exist
            recent_orders = Order.objects.filter(
                created_at__gte=timezone.now() - timedelta(minutes=60)
            ).order_by('-created_at')[:5]
            logger.warning(f"Recent orders in last 60 min: {[f'{o.id} ({o.status}) - {o.customer} to {o.vendor}' for o in recent_orders]}")

        if awaiting_order:
            # Update order with delivery address but keep status as awaiting until payment
            awaiting_order.delivery_address = validated_address
            awaiting_order.save()

            logger.info(f"Updated order {awaiting_order.id} with address: {validated_address} (keeping status as {awaiting_order.status})")

            order_id = awaiting_order.id
            subtotal = float(awaiting_order.total_amount or 6000)

            # Calculate delivery fee based on distance using Google Maps
            delivery_fee = 800  # Default fallback fee
            delivery_duration = "45-60 minutes"
            if latitude and longitude and awaiting_order.vendor:
                try:
                    # Get vendor location - check if vendor has lat/lng attributes
                    vendor_lat = getattr(awaiting_order.vendor, 'latitude', None)
                    vendor_lng = getattr(awaiting_order.vendor, 'longitude', None)

                    # If vendor doesn't have coordinates, try geocoding the business address
                    if not vendor_lat or not vendor_lng:
                        logger.info(f"Vendor {awaiting_order.vendor.id} has no coordinates, using default delivery fee")
                        # Use default delivery fee
                    elif vendor_lat and vendor_lng:
                        # Calculate distance and delivery price using Google Maps
                        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
                        distance_url = f"{base_url}/api/user/location/distance/"

                        distance_payload = {
                            'origin': f"{vendor_lat},{vendor_lng}",
                            'destination': f"{latitude},{longitude}"
                        }

                        distance_response = requests.post(distance_url, json=distance_payload, timeout=10)

                        if distance_response.status_code == 200:
                            distance_data = distance_response.json()
                            if distance_data.get('success'):
                                delivery_fee = distance_data.get('delivery_price', 800)
                                distance_km = distance_data.get('distance', {}).get('km', 0)
                                delivery_duration = distance_data.get('duration', {}).get('text', '45-60 minutes')

                                logger.info(f"Calculated delivery: {distance_km}km, fee: ₦{delivery_fee}, duration: {delivery_duration}")
                            else:
                                logger.warning(f"Distance calculation failed: {distance_data.get('error')}")
                        else:
                            logger.warning(f"Distance API failed with status {distance_response.status_code}")
                    else:
                        logger.warning(f"Vendor {awaiting_order.vendor.id} has no coordinates")
                except Exception as e:
                    logger.error(f"Error calculating delivery fee: {str(e)}")
                    # Keep default delivery fee

            total = subtotal + delivery_fee

            summary_message = f"✅ *Address Confirmed!*\n{validated_address}\n\n"
            summary_message += f"━━━━━━━━━━━━━━━━━━━\n"
            summary_message += f"🛒 *ORDER SUMMARY*\n"
            summary_message += f"━━━━━━━━━━━━━━━━━━━\n\n"
            summary_message += f"🏪 *Vendor:* {awaiting_order.vendor.business_name}\n"
            summary_message += f"📦 *Order #:* {order_id}\n\n"
            
            # Show actual order items if they exist
            order_items = awaiting_order.items.all()
            summary_message += f"*Items Ordered:*\n"
            if order_items.exists():
                for item in order_items:
                    # OrderItem has product FK, Product has 'name' field (or 'dish_name' in API responses)
                    item_name = item.product.name if item.product else 'Item'
                    summary_message += f"• {item_name} x{item.quantity} - ₦{float(item.price * item.quantity):,.0f}\n"
            else:
                # No items in order - should not happen if order was created properly
                logger.error(f"Order {awaiting_order.id} has no items!")
                summary_message += f"⚠️ No items in your order. Please try ordering again.\n"

            summary_message += f"\n━━━━━━━━━━━━━━━━━━━\n"
            summary_message += f"💰 Subtotal: ₦{subtotal:,.0f}\n"
            summary_message += f"🚚 Delivery: ₦{delivery_fee:,}\n"
            summary_message += f"━━━━━━━━━━━━━━━━━━━\n"
            summary_message += f"💳 *TOTAL: ₦{total:,.0f}*\n"
            summary_message += f"━━━━━━━━━━━━━━━━━━━\n\n"

            # Generate Paystack PwT (Pay with Transfer)
            try:
                pwt_details = _generate_paystack_pwt(total, order_id, user)
                
                if pwt_details and pwt_details.get('account_number') and pwt_details.get('bank_name'):
                    summary_message += f"🏦 *Paystack Payment Details:*\n"
                    summary_message += f"Bank: {pwt_details.get('bank_name')}\n"
                    summary_message += f"Account: {pwt_details.get('account_number')}\n"
                    summary_message += f"Name: {pwt_details.get('account_name')}\n"
                    summary_message += f"Amount: ₦{total:,.0f}\n\n"
                    summary_message += f"📱 Transfer the exact amount and reply 'PAID' when done!\n"
                    summary_message += f"⏰ Estimated delivery: {delivery_duration} after payment confirmation.\n\n"
                    
                    # Ask about saving address
                    summary_message += f"💾 Would you like to save this address for future orders?\n"
                    summary_message += f"Reply 'SAVE HOME' or 'SAVE OFFICE' or 'SAVE [label]' to save it!"
                else:
                    logger.error(f"PwT returned invalid details for order {order_id}")
                    summary_message += f"❌ Payment setup failed - invalid response from payment service.\n\n"
                    summary_message += f"💡 Please try again or contact support."
                    
            except Exception as e:
                logger.error(f"Exception generating PwT for order {order_id}: {str(e)}")
                summary_message += f"❌ Payment system unavailable. Please try again later.\n\n"
                summary_message += f"Error: {str(e)[:100]}\n\n"
                summary_message += f"💡 Contact support if this continues."

            return summary_message
        else:
            # No order found - guide user back to proper flow
            logger.warning(f"No order found for address processing - user: {user}, phone: {phone_number}")
            return "❌ I don't see any order in progress. Let's start fresh!\n\nWhat would you like to order? For example:\n• 'I want pizza'\n• 'Jollof rice'\n• 'Burger and fries'\n\nJust tell me what you're craving! 🍽️"

    except Exception as e:
        logger.error(f"Error showing order summary: {str(e)}")
        return "Sorry, there was an error preparing your order summary. Please try again."


def _generate_paystack_pwt(amount, order_id, user=None):
    """Generate Paystack Pay with Transfer for payment"""
    try:
        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
        pwt_url = f"{base_url}/api/user/payments/paystack/initialize/"
        
        payload = {
            'amount': amount,
            'order_id': str(order_id),
            'customer_email': user.email if user and hasattr(user, 'email') else f"whatsapp_{order_id}@temp.bestyy.com"
        }
        
        logger.info(f"Calling Paystack PwT API for order {order_id}, amount: ₦{amount}")
        logger.info(f"Paystack API endpoint: {pwt_url}")
        
        response = requests.post(pwt_url, json=payload, timeout=30)
        
        logger.info(f"Paystack API response status: {response.status_code}")
        logger.info(f"Paystack API response: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                logger.info(f"✅ Paystack PwT created successfully for order {order_id}")
                return {
                    'account_number': data.get('account_number'),
                    'account_name': data.get('account_name'),
                    'bank_name': data.get('bank_name', 'Wema Bank'),
                    'reference': data.get('reference')
                }
            else:
                logger.error(f"❌ Paystack API returned success=False: {data.get('error')}")
        else:
            logger.error(f"❌ Paystack API error {response.status_code}: {response.text[:500]}")
        
        # If Paystack fails, raise exception instead of falling back to mock data
        raise Exception(f"Paystack API failed: {response.status_code} - {response.text[:200]}")

    except Exception as e:
        logger.error(f"❌ Error generating Paystack PwT: {str(e)}")
        # Re-raise the exception so caller knows it failed
        raise


def _handle_address_save_request(content, phone_number, meta_service, user=None):
    """Handle requests to save delivery addresses with labels"""
    content_lower = content.lower().strip()

    if content_lower.startswith('save '):
        label = content_lower[5:].strip()  # Remove 'save ' prefix

        if label:
            try:
                base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')

                # Save address via API (assuming we have the last validated address)
                # In a real implementation, we'd store the last validated address in session/context

                save_message = f"✅ Address saved as '{label.title()}'!\n\n"
                save_message += f"📍 For future orders, just say:\n"
                save_message += f"• 'Deliver to my {label}'\n"
                save_message += f"• 'Send to {label}'\n"
                save_message += f"• 'To {label}'\n\n"
                save_message += f"What would you like to do next?"

                return save_message

            except Exception as e:
                logger.error(f"Error saving address: {str(e)}")
                return "Sorry, I couldn't save that address right now. You can still place orders with new addresses!"
        else:
            return "Please specify a label for your address. For example: 'SAVE HOME' or 'SAVE OFFICE'"

    return None


def _detect_saved_address_reference(text):
    """Check if user is referencing a saved address"""
    text_lower = text.lower().strip()

    # Patterns for saved address references
    saved_address_patterns = [
        r'\bto my (\w+)\b',  # "to my home", "to my office"
        r'\bdeliver to my (\w+)\b',  # "deliver to my home"
        r'\bsend to (\w+)\b',  # "send to home", "send to office"
        r'\bmy (\w+) address\b',  # "my home address"
        r'\bdeliver to (\w+)\b',  # "deliver to home"
    ]

    for pattern in saved_address_patterns:
        match = re.search(pattern, text_lower)
        if match:
            address_label = match.group(1)
            # Common address labels
            if address_label in ['home', 'office', 'work', 'house', 'apartment']:
                return address_label

    return None


def _handle_saved_address_order(address_label, full_content, phone_number, meta_service, user=None):
    """Handle order with saved address reference"""
    try:
        # Extract the food order from the message
        food_intent = _detect_food_ordering_intent(full_content) or _detect_menu_ordering_intent(full_content)

        if food_intent:
            # Process the food order with saved address
            order_message = f"🍽️ Got it! I'll deliver to your {address_label}.\n\n"
            order_message += f"What would you like to order?"

            # In a real implementation, we'd:
            # 1. Retrieve the saved address from user's profile
            # 2. Use it for delivery calculation
            # 3. Proceed with order placement

            return order_message
        else:
            return f"I'd be happy to deliver to your {address_label}! What would you like to order?"

    except Exception as e:
        logger.error(f"Error handling saved address order: {str(e)}")
        return f"Sorry, I couldn't process your order with the saved {address_label} address. Please try again."




def _process_additional_order_item(content, phone_number, meta_service, user=None):
    """Process additional items in the order"""
    # Extract the food item from the message
    food_intent = _detect_food_ordering_intent(content) or _detect_menu_ordering_intent(content)

    if food_intent:
        try:
            # Search for the additional item
            recommendation_message = _get_food_recommendations_with_api(food_intent, user)
            return recommendation_message
        except Exception as e:
            logger.error(f"Error processing additional order item: {str(e)}")
            return f"I couldn't find '{content}' right now. Would you like to try something else or complete your order?"
    else:
        return f"I didn't understand what you'd like to order. Could you tell me the food item name? Or reply 'DONE' to complete your order."


def _process_menu_order(dish_name, phone_number, meta_service, user=None):
    """Process an order request from the current menu context - WITH IMAGES"""
    try:
        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')

        # For now, search across all vendors for the dish (in a real implementation,
        # we'd remember which vendor's menu was last shown)
        search_url = f"{base_url}/api/user/vendors/search/"
        response = requests.get(search_url, params={'q': '', 'page_size': 20}, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('vendors'):
                vendors = data['vendors']

                # Search through vendors and their menus for the requested dish
                for vendor in vendors[:5]:  # Check top 5 vendors
                    vendor_id = vendor.get('id')
                    if not vendor_id:
                        continue

                    # Get vendor menu
                    menu_url = f"{base_url}/api/user/vendors/{vendor_id}/menu/"
                    menu_response = requests.get(menu_url, timeout=5)

                    if menu_response.status_code == 200:
                        menu_data = menu_response.json()
                        if menu_data.get('success') and menu_data.get('menu_items'):
                            menu_items = menu_data['menu_items']

                            # Look for the requested dish (fuzzy matching)
                            for item in menu_items:
                                item_name = item.get('dish_name', '').lower()
                                if dish_name in item_name or item_name in dish_name:
                                    # Found the dish! Store it in conversation context
                                    from bestyy.communication.whatsapp.models import WhatsAppConversation
                                    conversation, _ = WhatsAppConversation.objects.get_or_create(
                                        phone_number=phone_number,
                                        defaults={'user': user, 'state': 'onboarded'}
                                    )
                                    
                                    # Store the selected dish details for order creation
                                    conversation.context_data = conversation.context_data or {}
                                    conversation.context_data['pending_dish'] = {
                                        'product_id': item.get('id'),
                                        'dish_name': item.get('dish_name'),
                                        'price': str(item.get('price', 0)),  # Convert Decimal to string for JSON
                                        'vendor_id': vendor_id,
                                        'vendor_name': vendor.get('business_name')
                                    }
                                    conversation.save()
                                    logger.info(f"Stored pending dish {item.get('dish_name')} for user {user}, phone {phone_number}")
                                    
                                    # Now prepare the order confirmation message
                                    vendor_name = vendor.get('business_name', 'Restaurant')
                                    item_name = item.get('dish_name', 'Menu Item')
                                    price = item.get('price', 0)
                                    description = item.get('description', '')
                                    image_url = item.get('image', '')
                                    rating = item.get('rating', 0)

                                    # Send food image first if available (no caption)
                                    if image_url:
                                        try:
                                            image_result = meta_service.send_message(
                                                to=phone_number,
                                                message=image_url,
                                                message_type='image'
                                            )
                                            if image_result.get('success'):
                                                logger.info(f"Order confirmation image sent for {item_name}")
                                        except Exception as e:
                                            logger.error(f"Error sending order confirmation image for {item_name}: {str(e)}")

                                    # Send order details message with proper formatting
                                    stars = "⭐" * min(5, max(1, int(rating))) if rating > 0 else ""

                                    order_msg = f"📍 {vendor_name}\n\n"
                                    order_msg += f"🍛 {item_name}\n"
                                    if stars:
                                        order_msg += f"{stars}\n"
                                    if description:
                                        order_msg += f"📝 {description}\n"
                                    order_msg += f"💰 ₦{price:,}\n\n"

                                    order_msg += f"Would you like to:\n"
                                    order_msg += f"1. ✅ Confirm order\n"
                                    order_msg += f"2. ➕ Add customizations\n"
                                    order_msg += f"3. 🔄 Choose different dish\n"
                                    order_msg += f"4. ❌ Cancel\n\n"
                                    order_msg += f"Reply with the number or just say 'confirm'!"

                                    return order_msg

        # If we can't find the specific dish, offer alternatives
        return f"I couldn't find '{dish_name}' in our current menus. Would you like me to show you some similar options or help you find something else?"

    except Exception as e:
        logger.error(f"Error processing menu order for {dish_name}: {str(e)}")
        return "I'd be happy to help you place an order! Could you please tell me what you'd like to order from our menu?"


def _get_vendor_menu_by_selection(selection_number, phone_number, meta_service):
    """Get vendor menu when user selects a restaurant by number - RICH MENU DISPLAY"""
    try:
        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')

        # For now, fetch some popular vendors and assume user is selecting from top results
        # In a more sophisticated implementation, we'd store the exact vendors shown
        api_url = f"{base_url}/api/user/vendors/search/"
        response = requests.get(api_url, params={'q': '', 'page_size': 10}, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('vendors'):
                vendors = data['vendors']
                if 1 <= selection_number <= len(vendors):
                    selected_vendor = vendors[selection_number - 1]
                    vendor_id = selected_vendor.get('id')
                    vendor_name = selected_vendor.get('business_name', 'Restaurant')

                    # Fetch vendor menu
                    menu_url = f"{base_url}/api/user/vendors/{vendor_id}/menu/"
                    menu_response = requests.get(menu_url, timeout=5)

                    if menu_response.status_code == 200:
                        menu_data = menu_response.json()
                        if menu_data.get('success') and menu_data.get('menu_items'):
                            menu_items = menu_data['menu_items'][:6]  # Show up to 6 items for better UX

                            # Send welcome message first
                            welcome_msg = f"🍽️ Welcome to {vendor_name}!\n\nHere are our featured dishes:"
                            meta_service.send_message(to=phone_number, message=welcome_msg)

                            # Send each menu item as a rich image + details
                            for i, item in enumerate(menu_items, 1):
                                name = item.get('dish_name', 'Menu Item')
                                price = item.get('price', 0)
                                description = item.get('description', '')
                                rating = item.get('rating', 0)
                                image_url = item.get('image', '')

                                # Send image if available
                                if image_url:
                                    try:
                                        # Create rich caption with all details
                                        stars = "⭐" * min(5, max(1, int(rating))) if rating > 0 else ""
                                        caption = f"{name}\n{'⭐' * min(5, max(1, int(rating))) if rating > 0 else ''}\n"
                                        if description:
                                            caption += f"{description[:80]}{'...' if len(description) > 80 else ''}\n"
                                        caption += f"₦{price:,}"

                                        image_result = meta_service.send_message(
                                            to=phone_number,
                                            message=image_url,
                                            message_type='image',
                                            caption=caption
                                        )
                                        if image_result.get('success'):
                                            logger.info(f"Menu item image sent for {name}")
                                    except Exception as e:
                                        logger.error(f"Error sending menu item image for {name}: {str(e)}")

                            # Send final instruction message
                            instruction_msg = "\n".join([
                                f"📋 Reply with the dish name or number to order!",
                                f"💬 Example: 'I want the Jollof Rice' or 'Order #1'",
                                f"❓ Need help? Just ask!"
                            ])
                            meta_service.send_message(to=phone_number, message=instruction_msg)
                            return None  # Return None since we sent multiple messages

        # Fallback if we can't get the specific menu
        return f"Great choice! Let me show you the menu for restaurant #{selection_number}.\n\nI'd be happy to help you place an order! Could you please tell me what you'd like to order from our menu?"

    except Exception as e:
        logger.error(f"Error getting vendor menu for selection {selection_number}: {str(e)}")
        return "I'd be happy to help you place an order! Could you please tell me what you'd like to order from our menu?"


def _handle_vendor_recommendation(dish_name: str, vendor_name: str, conversation, phone_number: str, meta_service, user=None):
    """Handle vendor recommendation with featured priority"""
    from .vendor_recommendation_service import VendorRecommendationService
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        recommender = VendorRecommendationService(user=user)
        result = recommender.search_vendors_for_dish(
            dish_name=dish_name,
            preferred_vendor_name=vendor_name if vendor_name else None,
            page=1
        )
        
        if result['total_vendors'] > 0:
            conversation.context_data = conversation.context_data or {}
            conversation.context_data['vendor_search'] = {
                'dish_name': dish_name,
                'preferred_vendor': vendor_name,
                'current_page': 1,
                'total_vendors': result['total_vendors']
            }
            conversation.context_data['vendor_selection_active'] = True
            conversation.context_data['vendor_options'] = [
                {
                    'vendor_id': v['vendor_id'],
                    'product_id': v['product_id'],
                    'vendor_name': v['vendor_name'],
                    'product_name': v['product_name'],
                    'price': str(v['price'])
                }
                for v in result['recommended_vendors']
            ]
            conversation.save()
            logger.info(f"Stored {len(result['recommended_vendors'])} vendor options for {dish_name}")
        
        return result['message']
    except Exception as e:
        logger.error(f"Error in vendor recommendation: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Sorry, I had trouble finding vendors for {dish_name}. Please try again!"


def _handle_more_vendors(conversation, phone_number: str, meta_service):
    """Handle MORE pagination for vendor recommendations"""
    from .vendor_recommendation_service import VendorRecommendationService
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        vendor_search = conversation.context_data.get('vendor_search')
        if not vendor_search:
            return None
        
        current_page = vendor_search.get('current_page', 1)
        next_page = current_page + 1
        
        recommender = VendorRecommendationService(user=conversation.user)
        result = recommender.search_vendors_for_dish(
            dish_name=vendor_search['dish_name'],
            preferred_vendor_name=vendor_search.get('preferred_vendor'),
            page=next_page
        )
        
        if result['recommended_vendors']:
            conversation.context_data['vendor_search']['current_page'] = next_page
            conversation.context_data['vendor_options'] = [
                {
                    'vendor_id': v['vendor_id'],
                    'product_id': v['product_id'],
                    'vendor_name': v['vendor_name'],
                    'product_name': v['product_name'],
                    'price': str(v['price'])
                }
                for v in result['recommended_vendors']
            ]
            conversation.save()
            logger.info(f"Showing page {next_page} of vendor results")
            return result['message']
        else:
            return "That's all the vendors we have! Reply with a number to select from the current page."
    except Exception as e:
        logger.error(f"Error handling MORE vendors: {str(e)}")
        return None


def _handle_vendor_selection(selection_number: int, conversation, phone_number: str, meta_service, user=None):
    """Handle vendor selection by number"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        vendor_options = conversation.context_data.get('vendor_options', [])
        if not vendor_options:
            return None
        
        if selection_number < 1 or selection_number > len(vendor_options):
            return f"Please select a number between 1 and {len(vendor_options)}"
        
        selected_vendor = vendor_options[selection_number - 1]
        conversation.context_data['pending_dish'] = {
            'product_id': selected_vendor['product_id'],
            'dish_name': selected_vendor['product_name'],
            'price': selected_vendor['price'],
            'vendor_id': selected_vendor['vendor_id'],
            'vendor_name': selected_vendor['vendor_name']
        }
        conversation.context_data.pop('vendor_selection_active', None)
        conversation.context_data.pop('vendor_options', None)
        conversation.context_data.pop('vendor_search', None)
        conversation.save()
        
        logger.info(f"User selected vendor {selected_vendor['vendor_name']} for {selected_vendor['product_name']}")
        
        message = f"✅ Great choice!\n\n"
        message += f"🏪 *{selected_vendor['vendor_name']}*\n"
        message += f"🍽️ {selected_vendor['product_name']} - ₦{float(selected_vendor['price']):,.0f}\n\n"
        message += f"Would you like to confirm this order?\n\n"
        message += f"💬 Reply:\n"
        message += f"• *YES* - Confirm and proceed\n"
        message += f"• *NO* - Choose another dish"
        
        return message
    except Exception as e:
        logger.error(f"Error handling vendor selection: {str(e)}")
        import traceback
        traceback.print_exc()
        return "Sorry, there was an error processing your selection. Please try again!"


def _extract_vendor_and_dish(content: str):
    """Extract vendor name and dish name from message"""
    import re
    content_lower = content.lower()
    
    # Pattern: "dish from vendor"
    pattern1 = r'(?:i want|order|get me|give me)\s+(.+?)\s+from\s+(.+?)(?:\.|$|please|pls)'
    match1 = re.search(pattern1, content_lower)
    if match1:
        dish = match1.group(1).strip()
        vendor = match1.group(2).strip()
        return (dish, vendor)
    
    # Pattern: "vendor's dish"
    pattern2 = r"(.+?)(?:'s|s)\s+(.+?)(?:\.|$|please|pls)"
    match2 = re.search(pattern2, content_lower)
    if match2:
        vendor = match2.group(1).strip()
        dish = match2.group(2).strip()
        return (dish, vendor)
    
    # Pattern: Just the dish
    pattern3 = r'(?:i want|order|get me|give me)\s+(.+?)(?:\.|$|please|pls|from)'
    match3 = re.search(pattern3, content_lower)
    if match3:
        dish = match3.group(1).strip()
        return (dish, None)
    
    return (content.strip(), None)


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
