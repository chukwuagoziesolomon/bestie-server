"""
WhatsApp webhook handlers for verification and bot interactions
"""
import json
import re
import logging
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.conf import settings
from bestyy.core_features.user.models import PendingUser
from .services.meta_whatsapp_service import MetaWhatsAppService

logger = logging.getLogger(__name__)

@csrf_exempt
def whatsapp_verification_webhook(request):
    """
    Handle WhatsApp verification messages
    POST /webhooks/whatsapp/verification/
    """
    if request.method == 'GET':
        # Webhook verification (Meta setup)
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode == 'subscribe' and token == settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(challenge)
        return HttpResponse('Forbidden', status=403)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"Verification webhook received: {data}")

            # Process the webhook
            process_verification_message(data)

        except Exception as e:
            logger.error(f"Verification webhook error: {e}")

        # Always return 200 to Meta
        return JsonResponse({'status': 'received'})

def process_verification_message(webhook_data):
    """Process incoming WhatsApp message for verification"""

    try:
        entry = webhook_data['entry'][0]
        changes = entry['changes'][0]
        value = changes['value']

        # Check if it's an incoming message
        if 'messages' in value:
            message_data = value['messages'][0]

            from_number = message_data['from']
            message_text = message_data['text']['body'].strip()

            # Check if it's a verification message (starts with VERIFY)
            if message_text.upper().startswith('VERIFY'):
                # Handle role-specific verification codes
                if message_text.upper().startswith('VERIFY VEN'):
                    # Vendor verification: VERIFY VEN 123456
                    pattern = r'VERIFY\s+VEN\s+(\d{4})'
                    match = re.search(pattern, message_text.upper())
                    if match:
                        submitted_code = match.group(1)
                        handle_role_verification_code(from_number, submitted_code, 'vendor')
                    else:
                        send_error_message(from_number, "Invalid format. Please send: VERIFY VEN 1234")

                elif message_text.upper().startswith('VERIFY COU'):
                    # Courier verification: VERIFY COU 5678
                    pattern = r'VERIFY\s+COU\s+(\d{4})'
                    match = re.search(pattern, message_text.upper())
                    if match:
                        submitted_code = match.group(1)
                        handle_role_verification_code(from_number, submitted_code, 'courier')
                    else:
                        send_error_message(from_number, "Invalid format. Please send: VERIFY COU 5678")

                else:
                    # Legacy format: VERIFY 123456
                    pattern = r'VERIFY\s+(\d{6})'
                    match = re.search(pattern, message_text.upper())
                    if match:
                        submitted_code = match.group(1)
                        handle_verification_code(from_number, submitted_code)
                    else:
                        send_error_message(from_number, "Invalid format. Please send: VERIFY 123456 or VERIFY VEN/COU 1234")
            else:
                # Not a verification message - could be bot interaction
                handle_other_messages(from_number, message_text)

    except Exception as e:
        logger.error(f"Error processing verification message: {e}")

def handle_verification_code(phone_number, code):
    """Process legacy verification code submission (6-digit)"""

    # Format phone number
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number

    try:
        # Find pending user
        pending_user = PendingUser.objects.get(
            phone=phone_number,
            verification_code=code,
            is_verified=False,
            expires_at__gt=timezone.now()
        )

        # Check if phone number is already associated with an existing user
        existing_user = None
        try:
            from bestyy.core_features.user.models import UserProfile, VendorProfile, CourierProfile
            # Check different profile types
            for profile_model in [UserProfile, VendorProfile, CourierProfile]:
                try:
                    profile = profile_model.objects.get(phone=phone_number)
                    existing_user = profile.user
                    break
                except profile_model.DoesNotExist:
                    continue
        except Exception as e:
            logger.error(f"Error checking existing user: {e}")

        if existing_user:
            # User exists - add the new role instead of creating new account
            logger.info(f"Adding role {pending_user.user_type} to existing user {existing_user.email}")

            # Add the new role
            existing_user.add_role(pending_user.user_type)

            # Create the appropriate profile if it doesn't exist
            if pending_user.user_type == 'vendor':
                VendorProfile.objects.get_or_create(
                    user=existing_user,
                    defaults={
                        'phone': phone_number,
                        **pending_user.profile_data
                    }
                )
            elif pending_user.user_type == 'courier':
                CourierProfile.objects.get_or_create(
                    user=existing_user,
                    defaults={
                        'phone': phone_number,
                        **pending_user.profile_data
                    }
                )

            # Delete the pending user since we're not creating a new account
            pending_user.delete()

            # Send success message for role addition
            whatsapp_service = MetaWhatsAppService()
            roles = existing_user.get_roles()

            success_message = f"""✅ *Role Added Successfully!*

Welcome back, {existing_user.first_name}! 🎉

Your account now includes: {', '.join([role.title() for role in roles])}

"""

            if 'vendor' in roles and 'courier' in roles:
                success_message += """
🏪 *As a Vendor & Courier:*
• Manage your restaurant business
• Accept delivery assignments
• Earn from both sides of the platform

🌐 Dashboard: bestyy.com/vendor/dashboard
🚴 Dashboard: bestyy.com/courier/dashboard
"""
            elif 'vendor' in roles:
                success_message += """
🏪 *Vendor Features:*
• Accept and manage orders
• Send delivery updates
• Get order notifications

🌐 Dashboard: bestyy.com/vendor/dashboard
"""
            elif 'courier' in roles:
                success_message += """
🚴 *Courier Features:*
• Receive delivery assignments
• Update order status
• Earn delivery fees

🌐 Dashboard: bestyy.com/courier/dashboard
"""

            success_message += """
💡 *Pro Tips:*
• Keep your profiles updated
• Respond quickly to notifications
• Maintain good ratings

Reply with *HELP* anytime for assistance."""

            whatsapp_service.send_message(to=phone_number, message=success_message)
            logger.info(f"Successfully added role {pending_user.user_type} to user {existing_user.email}")

        else:
            # No existing user - create new account as before
            user, message = pending_user.create_user_account()

            if user:
                # Send success message with role-specific guidance
                whatsapp_service = MetaWhatsAppService()
                roles = user.get_roles()

                if 'vendor' in roles:
                    success_message = f"""✅ *Verification Successful!*

Welcome to Bestyy, {user.first_name}! 🎉

Your vendor account has been created successfully!

📱 *What you can do with WhatsApp:*
• Accept and manage orders
• Send delivery updates to customers
• Receive customer inquiries
• Get order notifications

🌐 *Next Steps:*
1. Visit your dashboard: bestyy.com/vendor/dashboard
2. Upload your menu items
3. Set your business hours
4. Configure delivery settings

💡 *Pro Tips:*
• Keep your menu updated
• Respond quickly to customer messages
• Set competitive prices

Reply with *HELP* anytime for assistance or *MENU* to see available commands."""

                elif 'courier' in roles:
                    success_message = f"""✅ *Verification Successful!*

Welcome to Bestyy, {user.first_name}! 🚴‍♂️

Your courier account has been created successfully!

📱 *What you can do with WhatsApp:*
• Receive delivery assignments
• Update order status
• Communicate with vendors
• Get delivery notifications

🌐 *Next Steps:*
1. Complete your profile: bestyy.com/courier/profile
2. Set your availability
3. Update your location
4. Start accepting deliveries

💡 *Pro Tips:*
• Keep your location updated
• Respond quickly to assignments
• Maintain good ratings

Reply with *HELP* anytime for assistance or *STATUS* to check your availability."""

                else:
                    success_message = f"""✅ *Verification Successful!*

Welcome to Bestyy, {user.first_name}! 🎉

Your account has been created successfully!

🌐 Visit the app: bestyy.com

Reply with *HELP* anytime for assistance."""

                whatsapp_service.send_message(to=phone_number, message=success_message)
                logger.info(f"User {user.email} verified successfully via WhatsApp")
            else:
                send_error_message(phone_number, "Account creation failed. Please contact support.")

    except PendingUser.DoesNotExist:
        # Invalid code or expired
        send_error_message(phone_number, """❌ *Verification Failed*

The code you entered is invalid or expired.

Please:
1. Go back to the signup page
2. Start the process again
3. Make sure to send the code within 10 minutes

Need help? Reply with *SUPPORT*""")

        logger.warning(f"Invalid verification attempt from {phone_number}")


def handle_role_verification_code(phone_number, code, role):
    """Process role-specific verification code submission (4-digit)"""

    # Format phone number
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number

    try:
        # Find pending user with matching role
        pending_user = PendingUser.objects.get(
            phone=phone_number,
            user_type=role,
            verification_code=code,
            is_verified=False,
            expires_at__gt=timezone.now()
        )

        # Check if phone number is already associated with an existing user
        existing_user = None
        try:
            from bestyy.core_features.user.models import UserProfile, VendorProfile, CourierProfile
            # Check different profile types
            for profile_model in [UserProfile, VendorProfile, CourierProfile]:
                try:
                    profile = profile_model.objects.get(phone=phone_number)
                    existing_user = profile.user
                    break
                except profile_model.DoesNotExist:
                    continue
        except Exception as e:
            logger.error(f"Error checking existing user: {e}")

        if existing_user:
            # User exists - add the new role instead of creating new account
            logger.info(f"Adding role {role} to existing user {existing_user.email}")

            # Add the new role
            existing_user.add_role(role)

            # Create the appropriate profile if it doesn't exist
            if role == 'vendor':
                VendorProfile.objects.get_or_create(
                    user=existing_user,
                    defaults={
                        'phone': phone_number,
                        **pending_user.profile_data
                    }
                )
            elif role == 'courier':
                CourierProfile.objects.get_or_create(
                    user=existing_user,
                    defaults={
                        'phone': phone_number,
                        **pending_user.profile_data
                    }
                )

            # Delete the pending user since we're not creating a new account
            pending_user.delete()

            # Send success message for role addition
            whatsapp_service = MetaWhatsAppService()
            roles = existing_user.get_roles()

            success_message = f"""✅ *{role.title()} Role Added Successfully!*

Welcome back, {existing_user.first_name}! 🎉

Your account now includes: {', '.join([r.title() for r in roles])}

"""

            if 'vendor' in roles and 'courier' in roles:
                success_message += f"""
🏪 *As a {role.title()} & {'Courier' if role == 'vendor' else 'Vendor'}:*
• Manage your restaurant business
• Accept delivery assignments
• Earn from both sides of the platform

🌐 Dashboard: bestyy.com/{role}/dashboard
🚴 Dashboard: bestyy.com/{'courier' if role == 'vendor' else 'vendor'}/dashboard
"""
            elif role == 'vendor':
                success_message += """
🏪 *Vendor Features:*
• Accept and manage orders
• Send delivery updates
• Get order notifications

🌐 Dashboard: bestyy.com/vendor/dashboard
"""
            elif role == 'courier':
                success_message += """
🚴 *Courier Features:*
• Receive delivery assignments
• Update order status
• Earn delivery fees

🌐 Dashboard: bestyy.com/courier/dashboard
"""

            success_message += """
💡 *Pro Tips:*
• Keep your profiles updated
• Respond quickly to notifications
• Maintain good ratings

Reply with *HELP* anytime for assistance."""

            whatsapp_service.send_message(to=phone_number, message=success_message)
            logger.info(f"Successfully added {role} role to user {existing_user.email}")

        else:
            # No existing user - create new account as before
            user, message = pending_user.create_user_account()

            if user:
                # Send success message with role-specific guidance
                whatsapp_service = MetaWhatsAppService()

                if role == 'vendor':
                    success_message = f"""✅ *Vendor Verification Successful!*

Welcome to Bestyy, {user.first_name}! 🎉

Your vendor account has been created successfully!

📱 *What you can do with WhatsApp:*
• Accept and manage orders
• Send delivery updates to customers
• Receive customer inquiries
• Get order notifications

🌐 *Next Steps:*
1. Visit your dashboard: bestyy.com/vendor/dashboard
2. Upload your menu items
3. Set your business hours
4. Configure delivery settings

💡 *Pro Tips:*
• Keep your menu updated
• Respond quickly to customer messages
• Set competitive prices

Reply with *HELP* anytime for assistance or *MENU* to see available commands."""

                elif role == 'courier':
                    success_message = f"""✅ *Courier Verification Successful!*

Welcome to Bestyy, {user.first_name}! 🚴‍♂️

Your courier account has been created successfully!

📱 *What you can do with WhatsApp:*
• Receive delivery assignments
• Update order status
• Communicate with vendors
• Get delivery notifications

🌐 *Next Steps:*
1. Complete your profile: bestyy.com/courier/profile
2. Set your availability
3. Update your location
4. Start accepting deliveries

💡 *Pro Tips:*
• Keep your location updated
• Respond quickly to assignments
• Maintain good ratings

Reply with *HELP* anytime for assistance or *STATUS* to check your availability."""

                whatsapp_service.send_message(to=phone_number, message=success_message)
                logger.info(f"User {user.email} verified successfully as {role} via WhatsApp")
            else:
                send_error_message(phone_number, "Account creation failed. Please contact support.")

    except PendingUser.DoesNotExist:
        # Invalid code or expired
        send_error_message(phone_number, f"""❌ *{role.title()} Verification Failed*

The code you entered is invalid or expired.

Please:
1. Go back to the signup page
2. Start the {role} registration process again
3. Make sure to send the code within 10 minutes

Need help? Reply with *SUPPORT*""")

        logger.warning(f"Invalid {role} verification attempt from {phone_number}")

def handle_other_messages(phone_number, message_text):
    """Handle non-verification messages (basic bot responses)"""

    whatsapp_service = MetaWhatsAppService()

    # Format phone number for user lookup
    formatted_phone = phone_number if phone_number.startswith('+') else '+' + phone_number

    # Try to find the user by phone number
    user = None
    try:
        from bestyy.core_features.user.models import UserProfile, VendorProfile, CourierProfile
        # Check different profile types
        for profile_model in [UserProfile, VendorProfile, CourierProfile]:
            try:
                profile = profile_model.objects.get(phone=formatted_phone)
                user = profile.user
                break
            except profile_model.DoesNotExist:
                continue
    except Exception as e:
        logger.error(f"Error finding user by phone: {e}")

    if 'HELP' in message_text:
        if user:
            roles = user.get_roles()
            if 'vendor' in roles:
                help_message = """🆘 *Bestyy Vendor Help*

Available commands:
• *HELP* - Show this help
• *ORDERS* - View recent orders
• *STATUS* - Check your availability
• *MENU* - Manage your menu
• *SUPPORT* - Contact support

🌐 Dashboard: bestyy.com/vendor/dashboard"""
            elif 'courier' in roles:
                help_message = """🆘 *Bestyy Courier Help*

Available commands:
• *HELP* - Show this help
• *DELIVERIES* - View active deliveries
• *STATUS* - Check your availability
• *LOCATION* - Update your location
• *SUPPORT* - Contact support

🌐 Dashboard: bestyy.com/courier/dashboard"""
            else:
                help_message = """🆘 *Bestyy Help*

Available commands:
• *HELP* - Show this help
• *ORDERS* - View your orders
• *SUPPORT* - Contact support

🌐 Visit: bestyy.com"""
        else:
            help_message = """🆘 *Bestyy Help*

Available commands:
• *HELP* - Show this help
• *STATUS* - Check verification status
• *SUPPORT* - Contact support

For signup issues, please visit: bestyy.com/signup"""

        whatsapp_service.send_message(to=phone_number, message=help_message)

    elif 'STATUS' in message_text:
        if user:
            roles = user.get_roles()
            if 'vendor' in roles:
                try:
                    vendor_profile = user.vendor_profile
                    status_message = f"""📋 *Vendor Status*

Name: {user.first_name} {user.last_name}
Business: {vendor_profile.business_name}
Status: {'Active' if vendor_profile.verification_status == 'approved' else 'Pending Approval'}
Rating: {vendor_profile.average_rating or 'No ratings yet'}

🌐 Dashboard: bestyy.com/vendor/dashboard"""
                except:
                    status_message = "Profile information not available."
            elif 'courier' in roles:
                try:
                    courier_profile = user.courier_profile
                    status_message = f"""📋 *Courier Status*

Name: {user.first_name} {user.last_name}
Status: {courier_profile.availability_status.title()}
Rating: {courier_profile.average_rating or 'No ratings yet'}
Completed Deliveries: {courier_profile.completed_deliveries}

🌐 Dashboard: bestyy.com/courier/dashboard"""
                except:
                    status_message = "Profile information not available."
            else:
                status_message = f"""📋 *Account Status*

Name: {user.first_name} {user.last_name}
Email: {user.email}
Status: Active

🌐 Visit: bestyy.com"""
        else:
            # Check if user has pending verification
            try:
                pending_user = PendingUser.objects.get(
                    phone=formatted_phone,
                    is_verified=False,
                    expires_at__gt=timezone.now()
                )

                status_message = f"""📋 *Verification Status*

Your verification code: *{pending_user.verification_code}*

⏰ Expires: {pending_user.expires_at.strftime('%H:%M %p')}

Send: VERIFY {pending_user.verification_code}"""

            except PendingUser.DoesNotExist:
                status_message = """📋 *Verification Status*

No active verification found. Please start the signup process at: bestyy.com/signup"""

        whatsapp_service.send_message(to=phone_number, message=status_message)

    elif 'ORDERS' in message_text and user:
        # Show recent orders for the user
        try:
            from bestyy.restaurant_features.order.models import Order
            recent_orders = Order.objects.filter(customer=user).order_by('-created_at')[:3]

            if recent_orders:
                orders_text = "📦 *Your Recent Orders*\n\n"
                for order in recent_orders:
                    orders_text += f"• Order #{order.id}\n"
                    orders_text += f"  Status: {order.status}\n"
                    orders_text += f"  Total: ₦{order.total_amount}\n"
                    orders_text += f"  Date: {order.created_at.strftime('%d/%m/%Y')}\n\n"

                orders_text += "🌐 View all orders: bestyy.com/orders"
            else:
                orders_text = "📦 *Your Orders*\n\nYou haven't placed any orders yet.\n\n🌐 Start ordering: bestyy.com"

            whatsapp_service.send_message(to=phone_number, message=orders_text)

        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            whatsapp_service.send_message(to=phone_number, message="Sorry, I couldn't fetch your orders right now.")

    elif 'DELIVERIES' in message_text and user and 'courier' in user.get_roles():
        # Show active deliveries for courier
        try:
            from bestyy.delivery_features.delivery.models import Delivery
            active_deliveries = Delivery.objects.filter(
                courier=user,
                status__in=['assigned', 'picked_up', 'in_transit']
            ).order_by('-created_at')[:3]

            if active_deliveries:
                deliveries_text = "🚴‍♂️ *Your Active Deliveries*\n\n"
                for delivery in active_deliveries:
                    deliveries_text += f"• Delivery #{delivery.id}\n"
                    deliveries_text += f"  Status: {delivery.status.replace('_', ' ').title()}\n"
                    deliveries_text += f"  Pickup: {delivery.pickup_address}\n"
                    deliveries_text += f"  Dropoff: {delivery.delivery_address}\n\n"

                deliveries_text += "🌐 Dashboard: bestyy.com/courier/dashboard"
            else:
                deliveries_text = "🚴‍♂️ *Your Deliveries*\n\nNo active deliveries right now.\n\n🌐 Dashboard: bestyy.com/courier/dashboard"

            whatsapp_service.send_message(to=phone_number, message=deliveries_text)

        except Exception as e:
            logger.error(f"Error fetching deliveries: {e}")
            whatsapp_service.send_message(to=phone_number, message="Sorry, I couldn't fetch your deliveries right now.")

    elif 'MENU' in message_text and user and 'vendor' in user.get_roles():
        # Show menu management options for vendor
        menu_message = """🍽️ *Menu Management*

Available options:
• *VIEW MENU* - See your current menu
• *ADD ITEM* - Add new menu item
• *UPDATE ITEM* - Modify existing item
• *DELETE ITEM* - Remove menu item

🌐 Full menu management: bestyy.com/vendor/menu"""

        whatsapp_service.send_message(to=phone_number, message=menu_message)

    elif 'SUPPORT' in message_text:
        support_message = """🆘 *Bestyy Support*

Need help? We're here for you!

📧 Email: support@bestyy.com
📱 WhatsApp: +2348012345678
🌐 Help Center: bestyy.com/help

For urgent issues, please call our support line."""

        whatsapp_service.send_message(to=phone_number, message=support_message)

    else:
        # Unknown command - provide helpful response
        if user:
            unknown_message = f"""🤔 I didn't understand that command.

Reply with *HELP* to see available commands for your account type.

🌐 Visit your dashboard: bestyy.com"""
        else:
            unknown_message = """🤔 I didn't understand that message.

If you're trying to verify your account, send: VERIFY 123456

For help, reply with *HELP* or visit: bestyy.com/signup"""

        whatsapp_service.send_message(to=phone_number, message=unknown_message)

def send_error_message(phone_number, message):
    """Send error message via WhatsApp"""
    whatsapp_service = MetaWhatsAppService()
    whatsapp_service.send_message(to=phone_number, message=message)