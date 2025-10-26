"""
API endpoints for email and phone verification during signup
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from bestyy.core_features.user.models import User, VendorProfile, CourierProfile, UserProfile
from bestyy.core_features.user.services.verification_service import VerificationService
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def send_email_verification_signup(request):
    """
    Send email verification during signup (no authentication required)
    POST /api/user/verification/send-email-signup/
    Body: { "email": "user@example.com" }
    """
    email = request.data.get('email')

    if not email:
        return Response({
            'success': False,
            'error': 'Email is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check if user already exists
    if User.objects.filter(email=email).exists():
        return Response({
            'success': False,
            'error': 'An account with this email already exists'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Send verification email (signup version - no user account yet)
    success, message = VerificationService.send_email_verification_signup(email)

    if success:
        return Response({
            'success': True,
            'message': message
        })
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email_signup(request):
    """
    Verify email during signup (no authentication required)
    POST /api/user/verification/verify-email-signup/
    Body: { "email": "user@example.com", "code": "123456" }
    """
    email = request.data.get('email')
    code = request.data.get('code')

    if not email or not code:
        return Response({
            'success': False,
            'error': 'Email and verification code are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    success, message = VerificationService.verify_email_signup(email, code)

    if success:
        return Response({
            'success': True,
            'message': message,
            'email_verified': True
        })
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_email_verification(request):
    """
    Send email verification to authenticated user (post-signup)
    POST /api/user/verification/send-email/
    """
    user = request.user

    # Get profile
    profile = None
    if hasattr(user, 'vendor_profile'):
        profile = user.vendor_profile
    elif hasattr(user, 'courier_profile'):
        profile = user.courier_profile

    if not profile:
        return Response({
            'success': False,
            'error': 'Profile not found'
        }, status=status.HTTP_404_NOT_FOUND)

    if profile.email_verified:
        return Response({
            'success': False,
            'error': 'Email already verified'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Send verification email
    success = VerificationService.send_email_verification(user, profile)

    if success:
        return Response({
            'success': True,
            'message': 'Verification email sent successfully'
        })
    else:
        return Response({
            'success': False,
            'error': 'Failed to send verification email'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_email(request):
    """
    Verify email using code
    POST /api/user/verification/verify-email/
    Body: { "code": "123456" }
    """
    user = request.user
    code = request.data.get('code')

    if not code:
        return Response({
            'success': False,
            'error': 'Verification code is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    success, message = VerificationService.verify_email(user, code)

    if success:
        return Response({
            'success': True,
            'message': message
        })
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def initiate_whatsapp_signup(request):
    """
    Initiate WhatsApp-based signup process
    POST /api/user/verification/initiate-whatsapp-signup/
    Body: {
        "user_type": "vendor|courier",
        "email": "user@example.com",
        "password": "password123",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "+2348012345678",
        ...profile_data
    }
    """
    from ..models import PendingUser
    import random

    user_type = request.data.get('user_type')
    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    phone = request.data.get('phone')

    if not all([user_type, email, password, phone]):
        return Response({
            'success': False,
            'error': 'user_type, email, password, and phone are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    if user_type not in ['vendor', 'courier']:
        return Response({
            'success': False,
            'error': 'user_type must be either "vendor" or "courier"'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check if email or phone already exists
    if User.objects.filter(email=email).exists():
        return Response({
            'success': False,
            'error': 'An account with this email already exists'
        }, status=status.HTTP_400_BAD_REQUEST)

    if (UserProfile.objects.filter(phone=phone).exists() or
        VendorProfile.objects.filter(phone=phone).exists() or
        CourierProfile.objects.filter(phone=phone).exists()):
        return Response({
            'success': False,
            'error': 'This phone number is already registered'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Prepare profile data (exclude user fields)
    profile_data = {}
    user_fields = {'user_type', 'email', 'password', 'first_name', 'last_name', 'phone'}
    for key, value in request.data.items():
        if key not in user_fields:
            profile_data[key] = value

    # Generate verification code
    verification_code = str(random.randint(100000, 999999))

    try:
        # Create pending user
        pending_user = PendingUser.objects.create(
            email=email,
            password=password,  # Will be hashed when creating actual user
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            user_type=user_type,
            verification_code=verification_code,
            profile_data=profile_data
        )

        # Return verification page data
        return Response({
            'success': True,
            'pending_user_id': pending_user.id,
            'verification_code': verification_code,
            'message': 'Signup initiated. Complete verification via WhatsApp.',
            'whatsapp_link': f'https://wa.me/2347012345678?text=VERIFY%20{verification_code}'
        })

    except Exception as e:
        logger.error(f"Failed to create pending user: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to initiate signup process'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def get_verification_status(request):
    """
    Get verification status and WhatsApp link for pending user
    POST /api/user/verification/verification-status/
    Body: { "pending_user_id": 123 }
    """
    from ..models import PendingUser

    pending_user_id = request.data.get('pending_user_id')

    if not pending_user_id:
        return Response({
            'success': False,
            'error': 'pending_user_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        pending_user = PendingUser.objects.get(id=pending_user_id)

        if pending_user.is_expired:
            pending_user.delete()
            return Response({
                'success': False,
                'error': 'Verification session expired. Please start signup again.'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'pending_user_id': pending_user.id,
            'verification_code': pending_user.verification_code,
            'user_type': pending_user.user_type,
            'email': pending_user.email,
            'phone': pending_user.phone,
            'whatsapp_link': f'https://wa.me/2347012345678?text=VERIFY%20{pending_user.verification_code}',
            'expires_at': pending_user.expires_at.isoformat(),
            'is_expired': False
        })

    except PendingUser.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Verification session not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def check_verification_complete(request):
    """
    Check if verification is complete and return user login info
    POST /api/user/verification/check-complete/
    Body: { "pending_user_id": 123 }
    """
    from ..models import PendingUser

    pending_user_id = request.data.get('pending_user_id')

    if not pending_user_id:
        return Response({
            'success': False,
            'error': 'pending_user_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        pending_user = PendingUser.objects.get(id=pending_user_id)

        if pending_user.is_verified:
            return Response({
                'success': True,
                'verified': True,
                'message': 'Account created successfully! You can now log in.',
                'user_type': pending_user.user_type,
                'email': pending_user.email,
                'login_url': f'/login?email={pending_user.email}&user_type={pending_user.user_type}'
            })
        else:
            return Response({
                'success': True,
                'verified': False,
                'message': 'Verification pending. Please complete verification via WhatsApp.'
            })

    except PendingUser.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Verification session not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def send_whatsapp_verification(request):
    """
    Send WhatsApp verification code during signup
    POST /api/user/verification/send-whatsapp/
    Body: { "phone": "+2348012345678" }
    """
    from ..models import User, VendorProfile, CourierProfile, UserProfile

    phone = request.data.get('phone')

    if not phone:
        return Response({
            'success': False,
            'error': 'Phone number is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check if phone is already registered
    if (UserProfile.objects.filter(phone=phone).exists() or
        VendorProfile.objects.filter(phone=phone).exists() or
        CourierProfile.objects.filter(phone=phone).exists()):
        return Response({
            'success': False,
            'error': 'This phone number is already registered'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Generate verification code
    code = VerificationService.generate_phone_code()

    # Send via WhatsApp using existing service
    from bestyy.communication.whatsapp.services.meta_whatsapp_service import MetaWhatsAppService
    whatsapp_service = MetaWhatsAppService()
    message = f"""🔔 Bestyy Verification Code

Hi there!

Your verification code is: *{code}*

This code will expire in 10 minutes.

Please reply with this code to complete your verification.

Best regards,
Bestyy Team"""

    try:
        whatsapp_service.send_message(
            to=phone,
            message=message,
            message_type='verification'
        )

        # Store code in cache for verification
        cache_key = f"whatsapp_signup_verification_{phone.replace('+', '').replace(' ', '').replace('-', '')}"
        cache.set(cache_key, code, timeout=600)  # 10 minutes

        return Response({
            'success': True,
            'message': 'Verification code sent to WhatsApp'
        })

    except Exception as e:
        logger.error(f"Failed to send WhatsApp verification: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to send verification code'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_whatsapp_code(request):
    """
    Verify WhatsApp code during signup
    POST /api/user/verification/verify-whatsapp/
    Body: { "phone": "+2348012345678", "code": "123456" }
    """
    phone = request.data.get('phone')
    code = request.data.get('code')

    if not phone or not code:
        return Response({
            'success': False,
            'error': 'Phone number and verification code are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check cached code
    cache_key = f"whatsapp_signup_verification_{phone.replace('+', '').replace(' ', '').replace('-', '')}"
    stored_code = cache.get(cache_key)

    if not stored_code:
        return Response({
            'success': False,
            'error': 'Verification code expired or not found'
        }, status=status.HTTP_400_BAD_REQUEST)

    if stored_code != code:
        return Response({
            'success': False,
            'error': 'Invalid verification code'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Mark phone as verified for signup
    verified_key = f"whatsapp_signup_verified_{phone.replace('+', '').replace(' ', '').replace('-', '')}"
    cache.set(verified_key, True, timeout=3600)  # 1 hour

    # Clear the verification code
    cache.delete(cache_key)

    return Response({
        'success': True,
        'message': 'WhatsApp number verified successfully'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_phone_verification(request):
    """
    Send phone verification code to authenticated user (post-signup)
    POST /api/user/verification/send-phone/
    """
    user = request.user

    # Get profile
    profile = None
    if hasattr(user, 'vendor_profile'):
        profile = user.vendor_profile
    elif hasattr(user, 'courier_profile'):
        profile = user.courier_profile

    if not profile:
        return Response({
            'success': False,
            'error': 'Profile not found'
        }, status=status.HTTP_404_NOT_FOUND)

    if not user.phone:
        return Response({
            'success': False,
            'error': 'Phone number not provided'
        }, status=status.HTTP_400_BAD_REQUEST)

    if profile.phone_verified:
        return Response({
            'success': False,
            'error': 'Phone already verified'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Send verification code
    success, message = VerificationService.send_phone_verification(user, profile)

    return Response({
        'success': success,
        'message' if success else 'error': message
    }, status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_phone(request):
    """
    Verify phone using code
    POST /api/user/verification/verify-phone/
    Body: { "code": "123456" }
    """
    user = request.user
    code = request.data.get('code')

    if not code:
        return Response({
            'success': False,
            'error': 'Verification code is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    success, message = VerificationService.verify_phone(user, code)

    if success:
        return Response({
            'success': True,
            'message': message
        })
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_bank_account(request):
    """
    Verify and save bank account details
    POST /api/user/verification/verify-bank/
    Body: {
        "user_email": "user@example.com",
        "account_number": "1234567890",
        "account_name": "John Doe",
        "bank_name": "Access Bank"
    }
    Note: bank_code is optional - it will be automatically resolved from bank_name
    """
    user_email = request.data.get('user_email')

    if not user_email:
        return Response({
            'success': False,
            'error': 'User email is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=user_email)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Get profile
    profile = None
    if hasattr(user, 'vendor_profile'):
        profile = user.vendor_profile
    elif hasattr(user, 'courier_profile'):
        profile = user.courier_profile

    if not profile:
        return Response({
            'success': False,
            'error': 'Profile not found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Extract bank details
    account_number = request.data.get('account_number')
    account_name = request.data.get('account_name')
    bank_code = request.data.get('bank_code')
    bank_name = request.data.get('bank_name')

    if not all([account_number, account_name, bank_name]):
        return Response({
            'success': False,
            'error': 'Account number, account name, and bank name are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # If bank_code not provided, try to resolve it from bank_name
    if not bank_code:
        from bestyy.core_features.user.services.paystack_service import PaystackService
        paystack_service = PaystackService()
        banks_result = paystack_service.get_supported_banks()

        if banks_result['success']:
            # Find bank by name (case-insensitive partial match)
            bank_name_lower = bank_name.lower().strip()
            for bank in banks_result['banks']:
                if (bank.get('name', '').lower().strip() == bank_name_lower or
                    bank_name_lower in bank.get('name', '').lower() or
                    bank.get('slug', '').lower() == bank_name_lower):
                    bank_code = bank.get('code')
                    break

        # If still not found, try common bank mappings
        if not bank_code:
            common_banks = {
                'access': '044', 'access bank': '044',
                'first bank': '011', 'first bank of nigeria': '011',
                'gtbank': '058', 'guaranty trust bank': '058', 'gtb': '058',
                'zenith': '057', 'zenith bank': '057',
                'uba': '033', 'united bank for africa': '033',
                'fidelity': '070', 'fidelity bank': '070',
                'sterling': '232', 'sterling bank': '232',
                'wema': '035', 'wema bank': '035',
                'polaris': '076', 'polaris bank': '076',
                'union': '032', 'union bank': '032', 'union bank of nigeria': '032',
                'unity': '215', 'unity bank': '215',
                'stanbic': '039', 'stanbic ibtc': '039', 'stanbic ibtc bank': '039',
                'heritage': '030', 'heritage bank': '030',
                'keystone': '082', 'keystone bank': '082',
                'ecobank': '050', 'eco bank': '050',
                'diamond': '063', 'diamond bank': '063',
                'jaiz': '301', 'jaiz bank': '301',
                'mainstreet': '014', 'mainstreet bank': '014',
                'citibank': '023', 'citi bank': '023',
                'enterprise': '084', 'enterprise bank': '084',
                'fcmb': '214', 'first city monument bank': '214'
            }

            bank_code = common_banks.get(bank_name_lower)

        if not bank_code:
            return Response({
                'success': False,
                'error': f'Could not identify bank code for "{bank_name}". Please select from supported banks or provide the bank code manually.'
            }, status=status.HTTP_400_BAD_REQUEST)

    # Verify bank account
    success, message = VerificationService.verify_bank_account(
        profile, account_number, account_name, bank_code, bank_name
    )

    if success:
        return Response({
            'success': True,
            'message': message
        })
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def whatsapp_webhook_verification(request):
    """
    Handle WhatsApp webhook for verification messages
    POST /api/user/verification/whatsapp-webhook/
    """
    from ..models import PendingUser
    from bestyy.communication.whatsapp.services.meta_whatsapp_service import MetaWhatsAppService

    # Get message data from webhook
    try:
        # Meta WhatsApp webhook structure
        entries = request.data.get('entry', [])
        if not entries:
            return Response({'status': 'no_entries'})

        for entry in entries:
            changes = entry.get('changes', [])
            for change in changes:
                messages = change.get('value', {}).get('messages', [])
                for message in messages:
                    if message.get('type') == 'text':
                        from_number = message.get('from')
                        message_text = message.get('text', {}).get('body', '').strip().upper()

                        # Check if message starts with VERIFY
                        if message_text.startswith('VERIFY '):
                            code = message_text.split(' ')[1] if len(message_text.split(' ')) > 1 else ''

                            if code and code.isdigit() and len(code) == 6:
                                # Find pending user with this code and phone
                                try:
                                    pending_user = PendingUser.objects.get(
                                        verification_code=code,
                                        phone=from_number
                                    )

                                    if not pending_user.is_expired and not pending_user.is_verified:
                                        # Verify the user
                                        user, message = pending_user.create_user_account()

                                        if user:
                                            # Send success message back to user
                                            whatsapp_service = MetaWhatsAppService()
                                            success_message = f"""✅ Welcome {user.first_name}!

Your {pending_user.user_type} account has been created successfully!

You can now log in to your dashboard and start using Bestyy.

Best regards,
Bestyy Team"""

                                            whatsapp_service.send_message(
                                                to=from_number,
                                                message=success_message,
                                                message_type='text'
                                            )

                                            return Response({
                                                'status': 'success',
                                                'message': f'Account created for {user.email}'
                                            })

                                except PendingUser.DoesNotExist:
                                    # Send invalid code message
                                    whatsapp_service = MetaWhatsAppService()
                                    error_message = """❌ Invalid verification code.

Please check your code and try again, or start the signup process over.

Bestyy Team"""

                                    whatsapp_service.send_message(
                                        to=from_number,
                                        message=error_message,
                                        message_type='text'
                                    )

        return Response({'status': 'processed'})

    except Exception as e:
        logger.error(f"WhatsApp webhook error: {str(e)}")
        return Response({'status': 'error', 'message': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_verification_status(request):
    """
    Get verification status for authenticated user
    GET /api/user/verification/status/
    """
    user = request.user

    # Get profile
    profile = None
    if hasattr(user, 'vendor_profile'):
        profile = user.vendor_profile
    elif hasattr(user, 'courier_profile'):
        profile = user.courier_profile

    if not profile:
        return Response({
            'success': False,
            'error': 'Profile not found'
        }, status=status.HTTP_404_NOT_FOUND)

    status_data = VerificationService.get_verification_status(profile)

    return Response({
        'success': True,
        'verification_status': status_data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_signup_verification(request):
    """
    Complete signup verification process
    POST /api/user/verification/complete-signup/
    """
    user = request.user

    # Get profile
    profile = None
    if hasattr(user, 'vendor_profile'):
        profile = user.vendor_profile
    elif hasattr(user, 'courier_profile'):
        profile = user.courier_profile

    if not profile:
        return Response({
            'success': False,
            'error': 'Profile not found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Check if user self-verifications are complete (email, phone, bank)
    if not VerificationService.is_user_verification_complete(profile):
        status_data = VerificationService.get_verification_status(profile)
        return Response({
            'success': False,
            'error': 'Please complete email, phone, and bank account verification before proceeding',
            'verification_status': status_data
        }, status=status.HTTP_400_BAD_REQUEST)

    # Mark user verification as complete (but account still pending admin approval)
    user.profile_complete = True
    user.save()

    return Response({
        'success': True,
        'message': 'Your verification is complete! Your account is now pending admin approval. You will be notified once approved.',
        'user_verification_complete': True,
        'admin_approval_pending': profile.verification_status == 'pending'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_supported_banks(request):
    """
    Get list of supported banks for account verification from Paystack API
    GET /api/user/verification/supported-banks/
    """
    from bestyy.core_features.user.services.paystack_service import PaystackService

    paystack_service = PaystackService()
    result = paystack_service.get_supported_banks()

    if result['success']:
        # Format the banks data for frontend
        banks = []
        for bank in result['banks']:
            banks.append({
                'code': bank.get('code'),
                'name': bank.get('name'),
                'slug': bank.get('slug'),
                'longcode': bank.get('longcode'),
                'gateway': bank.get('gateway'),
                'pay_with_bank': bank.get('pay_with_bank', False),
                'active': bank.get('active', True),
                'country': bank.get('country'),
                'currency': bank.get('currency'),
                'type': bank.get('type')
            })

        return Response({
            'success': True,
            'banks': banks
        })
    else:
        # Fallback to common Nigerian banks if API fails
        banks = [
            {'code': '044', 'name': 'Access Bank'},
            {'code': '023', 'name': 'Citibank Nigeria'},
            {'code': '063', 'name': 'Diamond Bank'},
            {'code': '050', 'name': 'Ecobank Nigeria'},
            {'code': '084', 'name': 'Enterprise Bank'},
            {'code': '070', 'name': 'Fidelity Bank'},
            {'code': '011', 'name': 'First Bank of Nigeria'},
            {'code': '214', 'name': 'First City Monument Bank'},
            {'code': '058', 'name': 'Guaranty Trust Bank'},
            {'code': '030', 'name': 'Heritage Banking Company'},
            {'code': '301', 'name': 'Jaiz Bank'},
            {'code': '082', 'name': 'Keystone Bank'},
            {'code': '014', 'name': 'MainStreet Bank'},
            {'code': '076', 'name': 'Polaris Bank'},
            {'code': '039', 'name': 'Stanbic IBTC Bank'},
            {'code': '232', 'name': 'Sterling Bank'},
            {'code': '032', 'name': 'Union Bank of Nigeria'},
            {'code': '033', 'name': 'United Bank for Africa'},
            {'code': '215', 'name': 'Unity Bank'},
            {'code': '035', 'name': 'Wema Bank'},
            {'code': '057', 'name': 'Zenith Bank'},
        ]

        return Response({
            'success': True,
            'banks': banks,
            'note': 'Using fallback bank list due to API unavailability'
        })