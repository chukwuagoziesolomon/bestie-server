"""
Service for automatic account creation and reuse during checkout.
Handles guest users and prevents duplicate accounts.
"""
import logging
from typing import Optional, Tuple, Dict, Any, Union
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from bestyy.restaurant_features.order.models import Order

logger = logging.getLogger(__name__)
User = get_user_model()


class AutomaticAccountService:
    """
    Service to handle automatic account creation and reuse for guest users.
    """

    @staticmethod
    def create_or_reuse_account_for_order(order, guest_info):
        """
        Create a new account for guest user or reuse existing account.
        Returns (user, message, credentials)

        Args:
            order: The order object
            guest_info: Dict containing guest user information like name, phone, email

        Returns:
            Tuple of (user_object, message, credentials_dict)
        """
        try:
            with transaction.atomic():
                # Extract guest information
                email = guest_info.get('email', '').strip().lower()
                phone = guest_info.get('phone', '').strip()
                first_name = guest_info.get('first_name', '').strip()
                last_name = guest_info.get('last_name', '').strip()

                if not email:
                    return None, "Email is required for account creation", {}

                # Check if user already exists by email
                existing_user = User.objects.filter(email=email).first()

                if existing_user:
                    # User exists - reuse account
                    logger.info(f"Reusing existing account for {email}")

                    # Update order with existing user
                    order.customer = existing_user
                    order.save()

                    # Generate temporary password for login
                    temp_password = User.objects.make_random_password(length=12)

                    # Set temporary password (user can change later)
                    existing_user.set_password(temp_password)
                    existing_user.save()

                    credentials = {
                        'email': existing_user.email,
                        'password': temp_password,
                        'login_url': f"{settings.FRONTEND_URL}/login"
                    }

                    # Send login credentials via email
                    AutomaticAccountService._send_existing_account_credentials(existing_user, credentials, order)

                    return existing_user, f"Account already exists. Login credentials sent to {email}", credentials

                else:
                    # Create new account
                    logger.info(f"Creating new account for {email}")

                    # Generate secure password
                    password = User.objects.make_random_password(length=12)

                    # Create user
                    user = User.objects.create_user(
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                        phone=phone,
                        role='user'
                    )

                    # Update order with new user
                    order.customer = user
                    order.save()

                    credentials = {
                        'email': user.email,
                        'password': password,
                        'login_url': f"{settings.FRONTEND_URL}/login"
                    }

                    # Send welcome email with credentials
                    AutomaticAccountService._send_new_account_credentials(user, credentials, order)

                    return user, f"Account created successfully. Login credentials sent to {email}", credentials

        except Exception as e:
            logger.error(f"Error creating/reusing account for order {order.id}: {str(e)}")
            return None, f"Failed to create account: {str(e)}", {}

    @staticmethod
    def find_existing_account_by_phone_or_email(phone=None, email=None):
        """
        Find existing user by phone or email for account reuse.
        """
        if email:
            return User.objects.filter(email__iexact=email.strip()).first()

        if phone:
            # Clean phone number
            clean_phone = phone.replace('+', '').replace(' ', '').replace('-', '').strip()

            # Check User model phone field
            user = User.objects.filter(phone__icontains=clean_phone).first()
            if user:
                return user

            # Check profiles for phone
            from bestyy.core_features.user.models import UserProfile, VendorProfile, CourierProfile

            # Check user profiles
            profile = UserProfile.objects.filter(phone__icontains=clean_phone).select_related('user').first()
            if profile:
                return profile.user

            # Check vendor profiles
            vendor_profile = VendorProfile.objects.filter(phone__icontains=clean_phone).select_related('user').first()
            if vendor_profile:
                return vendor_profile.user

            # Check courier profiles
            courier_profile = CourierProfile.objects.filter(phone__icontains=clean_phone).select_related('user').first()
            if courier_profile:
                return courier_profile.user

        return None

    @staticmethod
    def _send_new_account_credentials(user, credentials, order):
        """
        Send welcome email with login credentials for new account.
        """
        try:
            subject = f"Welcome to Bestyy! Your Account Details"
            message = f"""
Hello {user.first_name},

Thank you for your order #{order.id}! We've created an account for you so you can easily track your orders and place future orders.

Your login credentials:
Email: {credentials['email']}
Password: {credentials['password']}

Please login at: {credentials['login_url']}

Important: This is a temporary password. Please change it after your first login for security.

Order Details:
- Order ID: #{order.id}
- Total Amount: ₦{order.total_amount}
- Status: {order.status}

If you have any questions, please contact our support team.

Best regards,
Bestyy Team
            """

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )

            logger.info(f"Sent new account credentials to {user.email}")

        except Exception as e:
            logger.error(f"Failed to send new account credentials to {user.email}: {str(e)}")

    @staticmethod
    def _send_existing_account_credentials(user, credentials, order):
        """
        Send login reminder for existing account.
        """
        try:
            subject = f"Your Bestyy Account Login Details"
            message = f"""
Hello {user.first_name},

We noticed you've placed a new order with us. Here are your login credentials to access your account:

Email: {credentials['email']}
Password: {credentials['password']} (temporary - please change after login)

Login at: {credentials['login_url']}

Your recent order:
- Order ID: #{order.id}
- Total Amount: ₦{order.total_amount}
- Status: {order.status}

If you didn't place this order or have any questions, please contact support immediately.

Best regards,
Bestyy Team
            """

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )

            logger.info(f"Sent existing account reminder to {user.email}")

        except Exception as e:
            logger.error(f"Failed to send existing account reminder to {user.email}: {str(e)}")

    @staticmethod
    def get_account_credentials_for_order(order: Order) -> Optional[Dict[str, Any]]:
        """
        Get account credentials for an existing order.
        Useful for resending credentials or displaying account info.
        """
        if not order.customer:
            return None

        # Generate temporary password
        temp_password = User.objects.make_random_password(length=12)
        order.customer.set_password(temp_password)
        order.customer.save()

        return {
            'email': order.customer.email,
            'password': temp_password,
            'login_url': f"{settings.FRONTEND_URL}/login",
            'order_id': order.id,
            'customer_name': order.customer.full_name
        }