"""
Service for handling email and phone verification during signup
"""
import random
import string
import re
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from bestyy.core_features.user.models import User, VendorProfile, CourierProfile
from bestyy.communication.whatsapp.services.meta_whatsapp_service import MetaWhatsAppService
import logging

logger = logging.getLogger(__name__)


class VerificationService:
    """
    Service to handle email and phone verification for vendors and couriers
    """

    @staticmethod
    def sanitize_cache_key(key: str) -> str:
        """
        Sanitize cache key by removing non-alphanumeric characters
        to ensure compatibility with memcached and other cache backends
        """
        return re.sub(r'[^a-zA-Z0-9]', '', key)

    @staticmethod
    def generate_email_code():
        """Generate a 6-digit email verification code"""
        return str(random.randint(100000, 999999))

    @staticmethod
    def generate_phone_code():
        """Generate a 6-digit phone verification code"""
        return str(random.randint(100000, 999999))

    @staticmethod
    def send_email_verification(user, profile):
        """
        Send email verification code to user
        """
        try:
            # Check if email verification attempts exceeded
            if profile.email_verification_attempts >= 5:
                return False, "Too many verification attempts. Please contact support."

            # Generate code
            code = VerificationService.generate_email_code()

            # Save code to profile
            profile.email_verification_code = code
            profile.email_verification_attempts += 1
            profile.save()

            # Send email
            subject = "Verify Your Email - Bestyy"

            # Get logo URL - direct path to static file
            logo_url = f"{settings.BASE_URL}/static/logo.png"

            html_message = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Verify Your Email - Bestyy</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: #f8f9fa;
                        padding: 20px;
                    }}
                    .container {{
                        background-color: #ffffff;
                        border-radius: 12px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                        overflow: hidden;
                        margin: 20px 0;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 40px 30px;
                        text-align: center;
                        color: white;
                    }}
                    .logo {{
                        max-width: 120px;
                        height: auto;
                        margin-bottom: 20px;
                        border-radius: 8px;
                    }}
                    .content {{
                        padding: 40px 30px;
                    }}
                    .welcome-text {{
                        font-size: 18px;
                        margin-bottom: 30px;
                        color: #555;
                    }}
                    .code-container {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        border-radius: 12px;
                        padding: 30px;
                        text-align: center;
                        margin: 30px 0;
                        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                    }}
                    .code-title {{
                        color: white;
                        font-size: 16px;
                        margin-bottom: 15px;
                        font-weight: 500;
                        letter-spacing: 1px;
                    }}
                    .verification-code {{
                        font-size: 36px;
                        font-weight: bold;
                        color: white;
                        letter-spacing: 8px;
                        font-family: 'Courier New', monospace;
                        background-color: rgba(255, 255, 255, 0.2);
                        padding: 15px 30px;
                        border-radius: 8px;
                        display: inline-block;
                        margin: 10px 0;
                        border: 2px solid rgba(255, 255, 255, 0.3);
                    }}
                    .instructions {{
                        background-color: #f8f9fa;
                        border-left: 4px solid #667eea;
                        padding: 20px;
                        margin: 30px 0;
                        border-radius: 0 8px 8px 0;
                    }}
                    .instructions h4 {{
                        margin-top: 0;
                        color: #333;
                        font-size: 16px;
                    }}
                    .warning {{
                        background-color: #fff3cd;
                        border: 1px solid #ffeaa7;
                        color: #856404;
                        padding: 15px;
                        border-radius: 8px;
                        margin: 20px 0;
                        font-size: 14px;
                    }}
                    .footer {{
                        background-color: #f8f9fa;
                        padding: 30px;
                        text-align: center;
                        border-top: 1px solid #e9ecef;
                    }}
                    .footer-content {{
                        max-width: 400px;
                        margin: 0 auto;
                    }}
                    .brand {{
                        font-size: 24px;
                        font-weight: bold;
                        color: #667eea;
                        margin-bottom: 10px;
                    }}
                    .tagline {{
                        color: #666;
                        font-size: 14px;
                        margin-bottom: 20px;
                    }}
                    .social-links {{
                        margin: 20px 0;
                    }}
                    .social-links a {{
                        display: inline-block;
                        margin: 0 10px;
                        color: #667eea;
                        text-decoration: none;
                        font-weight: 500;
                    }}
                    .copyright {{
                        color: #999;
                        font-size: 12px;
                        margin-top: 20px;
                    }}
                    @media (max-width: 600px) {{
                        body {{
                            padding: 10px;
                        }}
                        .container {{
                            margin: 10px 0;
                        }}
                        .header, .content, .footer {{
                            padding: 20px;
                        }}
                        .verification-code {{
                            font-size: 28px;
                            letter-spacing: 4px;
                            padding: 12px 20px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <!-- Header -->
                    <div class="header">
                        <img src="{logo_url}" alt="Bestyy Logo" class="logo">
                        <h1 style="margin: 0; font-size: 28px;">Welcome to Bestyy!</h1>
                        <p style="margin: 10px 0 0 0; opacity: 0.9;">Your Food Delivery Experience</p>
                    </div>

                    <!-- Content -->
                    <div class="content">
                        <p class="welcome-text">
                            Hi {user.first_name or 'there'}!<br>
                            Thank you for joining Bestyy. To complete your registration and start enjoying delicious meals, please verify your email address.
                        </p>

                        <!-- Verification Code -->
                        <div class="code-container">
                            <div class="code-title">YOUR VERIFICATION CODE</div>
                            <div class="verification-code">{code}</div>
                        </div>

                        <!-- Instructions -->
                        <div class="instructions">
                            <h4>How to verify your email:</h4>
                            <ol style="margin: 0; padding-left: 20px;">
                                <li>Open the Bestyy app or website</li>
                                <li>Navigate to the email verification section</li>
                                <li>Enter the code shown above</li>
                                <li>Click "Verify Email" to complete registration</li>
                            </ol>
                        </div>

                        <!-- Warning -->
                        <div class="warning">
                            <strong>Important:</strong> This code will expire in 10 minutes for security reasons.
                            If you didn't request this verification, please ignore this email.
                        </div>

                        <!-- Help -->
                        <p style="text-align: center; color: #666; font-size: 14px; margin-top: 30px;">
                            Having trouble? Contact our support team at
                            <a href="mailto:support@bestyy.com" style="color: #667eea;">support@bestyy.com</a>
                        </p>
                    </div>

                    <!-- Footer -->
                    <div class="footer">
                        <div class="footer-content">
                            <div class="brand">Bestyy</div>
                            <div class="tagline">Delicious food, delivered fast</div>

                            <div class="social-links">
                                <a href="#">Facebook</a> |
                                <a href="#">Twitter</a> |
                                <a href="#">Instagram</a>
                            </div>

                            <div class="copyright">
                                © 2024 Bestyy. All rights reserved.<br>
                                This email was sent to {user.email}
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """

            send_mail(
                subject=subject,
                message=f"Your Bestyy verification code is: {code}\n\nThis code will expire in 10 minutes.",
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False
            )

            logger.info(f"Email verification code sent to {user.email}")
            return True, "Verification code sent successfully"

        except Exception as e:
            logger.error(f"Failed to send email verification to {user.email}: {str(e)}")
            return False, "Failed to send verification code"

    @staticmethod
    def send_phone_verification(user, profile):
        """
        Send phone verification code via WhatsApp
        """
        try:
            # Check if phone verification attempts exceeded
            if profile.phone_verification_attempts >= 5:
                return False, "Too many verification attempts. Please contact support."

            # Generate code
            code = VerificationService.generate_phone_code()

            # Save code to profile
            profile.phone_verification_code = code
            profile.phone_verification_attempts += 1
            profile.save()

            # Send via Meta WhatsApp
            whatsapp_service = MetaWhatsAppService()
            message = f"""🔔 Bestyy Verification Code

Hi {user.first_name or 'there'}!

Your verification code is: *{code}*

This code will expire in 10 minutes.

If you didn't request this code, please ignore this message.

Best regards,
Bestyy Team"""

            result = whatsapp_service.send_message(
                to=user.phone,
                message=message,
                message_type='text'
            )

            if not result['success']:
                logger.error(f"Failed to send WhatsApp verification to {user.phone}: {result['message']}")
                return False, result['message']

            logger.info(f"Phone verification code sent to {user.phone}")
            return True, "Verification code sent successfully"

        except Exception as e:
            logger.error(f"Failed to send phone verification to {user.phone}: {str(e)}")
            return False, "Failed to send verification code"

    @staticmethod
    def verify_email(user, code):
        """
        Verify email using code
        """
        try:
            # Get profile (vendor or courier)
            profile = None
            if hasattr(user, 'vendor_profile'):
                profile = user.vendor_profile
            elif hasattr(user, 'courier_profile'):
                profile = user.courier_profile

            if not profile:
                return False, "Profile not found"

            # Check code
            if profile.email_verification_code != code:
                return False, "Invalid verification code"

            # Mark as verified
            profile.email_verified = True
            profile.email_verified_at = timezone.now()
            profile.email_verification_code = None  # Clear code
            profile.save()

            logger.info(f"Email verified for user {user.email}")
            return True, "Email verified successfully"

        except Exception as e:
            logger.error(f"Email verification failed: {str(e)}")
            return False, "Verification failed"

    @staticmethod
    def verify_phone(user, code):
        """
        Verify phone using code
        """
        try:
            # Get profile (vendor or courier)
            profile = None
            if hasattr(user, 'vendor_profile'):
                profile = user.vendor_profile
            elif hasattr(user, 'courier_profile'):
                profile = user.courier_profile

            if not profile:
                return False, "Profile not found"

            # Check code
            if profile.phone_verification_code != code:
                return False, "Invalid verification code"

            # Mark as verified
            profile.phone_verified = True
            profile.phone_verified_at = timezone.now()
            profile.phone_verification_code = None  # Clear code
            profile.save()

            logger.info(f"Phone verified for user {user.phone}")
            return True, "Phone verified successfully"

        except Exception as e:
            logger.error(f"Phone verification failed: {str(e)}")
            return False, "Verification failed"

    @staticmethod
    def send_email_verification_signup(email: str) -> tuple[bool, str]:
        """
        Send email verification during signup (no user account yet)
        """
        try:
            # Sanitize email for cache key
            sanitized_email = VerificationService.sanitize_cache_key(email)

            # Check if email is already verified in signup process
            cache_key = f"signup_email_verified_{sanitized_email}"
            if cache.get(cache_key):
                return False, "Email already verified"

            code = VerificationService.generate_email_code()

            # Store code in cache with email
            cache_key = f"signup_email_code_{sanitized_email}"
            cache.set(cache_key, code, timeout=600)  # 10 minutes

            # Always send actual email now that Gmail is configured
            # Remove DEBUG check so emails are sent in development too
            subject = "Verify Your Email - Bestyy"
            logo_url = f"{settings.BASE_URL}/static/logo.png"

            html_message = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f8f9fa;">
                <div style="background: linear-gradient(90deg, #23C7B2 0%, #25AC9B 100%); color: white; padding: 20px; text-align: center;">
                    <div style="font-size: 48px; margin-bottom: 10px;">🍽️</div>
                    <img src="{logo_url}" alt="Bestyy Logo" style="max-width: 80px; height: auto; margin-bottom: 10px; display: block; margin-left: auto; margin-right: auto;" onerror="this.style.display='none'">
                    <h1 style="margin: 0;">📧 Email Verification</h1>
                    <p style="margin: 5px 0;">Welcome to Bestyy!</p>
                </div>
                <div style="background-color: white; padding: 20px; margin: 20px; border-radius: 8px;">
                    <h2 style="color: #333; margin-top: 0;">Verify Your Email Address</h2>
                    <p>Hi there!</p>
                    <p>Thank you for joining Bestyy. To complete your registration and start enjoying delicious meals from local vendors, please verify your email address.</p>

                    <div style="background-color: #f8f9fa; border: 2px solid #28a745; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                        <h3 style="margin: 0; color: #28a745;">Your Verification Code</h3>
                        <div style="font-size: 32px; font-weight: bold; color: #333; letter-spacing: 4px; font-family: monospace; background-color: #fff; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #ddd;">{code}</div>
                    </div>

                    <div style="background-color: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h4 style="margin: 0; color: #333;">How to verify:</h4>
                        <ol style="margin: 10px 0; padding-left: 20px;">
                            <li>Open the Bestyy signup page</li>
                            <li>Navigate to the email verification section</li>
                            <li>Enter the 6-digit code shown above</li>
                            <li>Click "Verify Email" to continue</li>
                        </ol>
                    </div>

                    <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h4 style="margin: 0; color: #856404;">⏰ Important</h4>
                        <p style="margin: 5px 0;">This verification code will expire in <strong>10 minutes</strong> for security reasons.</p>
                        <p style="margin: 5px 0;">If you didn't request this verification, please ignore this email.</p>
                    </div>

                    <div style="text-align: center; margin: 30px 0;">
                        <p style="color: #666; font-size: 14px;">
                            Having trouble? Contact our support team at<br>
                            <a href="mailto:support@bestyy.com" style="color: #28a745;">support@bestyy.com</a>
                        </p>
                    </div>
                </div>
                <div style="text-align: center; color: #666; font-size: 12px; padding: 20px;">
                    <p>This is an automated verification email from Bestyy.</p>
                    <p>Bestyy - Connecting Customers with Local Vendors</p>
                </div>
            </body>
            </html>
            """

            plain_message = f"""
            Welcome to Bestyy!

            Hi there!

            Your verification code is: {code}

            This code will expire in 10 minutes.

            If you didn't request this verification, please ignore this email.

            Best regards,
            Bestyy Team
            """

            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False
            )

            return True, "Verification email sent successfully"

        except Exception as e:
            logger.error(f"Failed to send email verification to {email}: {str(e)}")
            return False, "Failed to send verification email"

    @staticmethod
    def verify_email_signup(email: str, code: str) -> tuple[bool, str]:
        """
        Verify email during signup
        """
        try:
            # Sanitize email for cache key
            sanitized_email = VerificationService.sanitize_cache_key(email)

            cache_key = f"signup_email_code_{sanitized_email}"
            stored_code = cache.get(cache_key)

            if not stored_code:
                return False, "Verification code expired or not found"

            if stored_code != code:
                return False, "Invalid verification code"

            # Mark email as verified for signup
            verified_key = f"signup_email_verified_{sanitized_email}"
            cache.set(verified_key, True, timeout=3600)  # 1 hour

            # Delete the code
            cache.delete(cache_key)

            return True, "Email verified successfully"

        except Exception as e:
            logger.error(f"Failed to verify email {email}: {str(e)}")
            return False, "Verification failed"

    @staticmethod
    def send_phone_verification_signup(phone: str) -> tuple[bool, str]:
        """
        Send phone verification during signup (no user account yet)
        """
        try:
            # Sanitize phone for cache key
            sanitized_phone = VerificationService.sanitize_cache_key(phone)

            # Check if phone is already verified in signup process
            cache_key = f"signup_phone_verified_{sanitized_phone}"
            if cache.get(cache_key):
                return False, "Phone already verified"

            code = VerificationService.generate_phone_code()

            # Store code in cache with phone
            cache_key = f"signup_phone_code_{sanitized_phone}"
            cache.set(cache_key, code, timeout=600)  # 10 minutes

            # Always send actual WhatsApp message now that Meta WhatsApp is configured
            # Remove DEBUG check so WhatsApp messages are sent in development too
            whatsapp_service = MetaWhatsAppService()
            message = f"""🔔 Bestyy Verification Code

Hi there!

Your verification code is: *{code}*

This code will expire in 10 minutes.

If you didn't request this code, please ignore this message.

Best regards,
Bestyy Team"""

            result = whatsapp_service.send_message(
                to=phone,
                message=message,
                message_type='text'
            )

            if not result['success']:
                logger.error(f"Failed to send WhatsApp verification to {phone}: {result['message']}")
                return False, result['message']

            return True, "Verification code sent successfully"

        except Exception as e:
            logger.error(f"Failed to send phone verification to {phone}: {str(e)}")
            return False, "Failed to send verification code"

    @staticmethod
    def verify_phone_signup(phone: str, code: str) -> tuple[bool, str]:
        """
        Verify phone during signup
        """
        try:
            # Sanitize phone for cache key
            sanitized_phone = VerificationService.sanitize_cache_key(phone)

            cache_key = f"signup_phone_code_{sanitized_phone}"
            stored_code = cache.get(cache_key)

            if not stored_code:
                return False, "Verification code expired or not found"

            if stored_code != code:
                return False, "Invalid verification code"

            # Mark phone as verified for signup
            verified_key = f"signup_phone_verified_{sanitized_phone}"
            cache.set(verified_key, True, timeout=3600)  # 1 hour

            # Delete the code
            cache.delete(cache_key)

            return True, "Phone verified successfully"

        except Exception as e:
            logger.error(f"Failed to verify phone {phone}: {str(e)}")
            return False, "Verification failed"

    @staticmethod
    def verify_bank_account(profile, account_number, account_name, bank_code, bank_name):
        """
        Verify bank account details using Paystack API
        """
        try:
            # Basic validation first
            if not account_number.isdigit():
                return False, "Account number must contain only digits"

            if len(account_number) < 10:
                return False, "Account number is too short"

            # For Nigerian banks, account numbers are typically 10 digits
            if len(account_number) != 10:
                return False, "Invalid account number length"

            # Import Paystack service
            from user.services.paystack_service import PaystackService
            paystack_service = PaystackService()

            # Verify account using Paystack's resolve account endpoint
            verification_result = paystack_service.verify_bank_account(account_number, bank_code)

            if not verification_result['success']:
                return False, verification_result.get('message', 'Bank account verification failed')

            # Check if the account name matches (case-insensitive)
            resolved_account_name = verification_result.get('account_name', '').strip().lower()
            provided_account_name = account_name.strip().lower()

            if resolved_account_name != provided_account_name:
                return False, "Account name does not match bank records"

            # Update profile with verified details
            profile.account_number = account_number
            profile.account_name = account_name  # Use provided name (already verified to match)
            profile.bank_code = bank_code
            profile.bank_name = bank_name
            profile.bank_account_verified = True
            profile.bank_account_verified_at = timezone.now()
            profile.save()

            logger.info(f"Bank account verified for profile {profile} using Paystack API")
            return True, "Bank account verified successfully"

        except Exception as e:
            logger.error(f"Bank account verification failed: {str(e)}")
            return False, "Bank account verification failed"

    @staticmethod
    def is_user_verification_complete(profile):
        """
        Check if user has completed self-verification (email, phone, bank)
        This is separate from admin approval
        """
        return (
            profile.email_verified and
            profile.phone_verified and
            profile.bank_account_verified
        )

    @staticmethod
    def is_profile_complete(profile):
        """
        Check if profile is fully approved (user verification + admin approval)
        """
        return (
            VerificationService.is_user_verification_complete(profile) and
            profile.verification_status == 'approved'
        )

    @staticmethod
    def get_verification_status(profile):
        """
        Get verification status for a profile
        """
        return {
            'email_verified': profile.email_verified,
            'phone_verified': profile.phone_verified,
            'bank_account_verified': profile.bank_account_verified,
            'user_verification_complete': VerificationService.is_user_verification_complete(profile),
            'admin_approved': profile.verification_status == 'approved',
            'verification_status': profile.verification_status,  # 'pending', 'approved', 'rejected'
            'profile_complete': VerificationService.is_profile_complete(profile),
            'email_verified_at': profile.email_verified_at.isoformat() if profile.email_verified_at else None,
            'phone_verified_at': profile.phone_verified_at.isoformat() if profile.phone_verified_at else None,
            'bank_verified_at': profile.bank_account_verified_at.isoformat() if profile.bank_account_verified_at else None,
        }