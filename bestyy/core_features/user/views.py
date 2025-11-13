from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from .models import User, VendorProfile, CourierProfile
from .forms import VendorSignupForm, CourierSignupForm
import secrets

def social_login_test(request):
    """Test view for social login"""
    return render(request, 'social_login.html')

def multi_role_signup(request):
    """Handle multi-role signup form"""
    if request.method == 'POST':
        # Get the roles from the form
        roles = request.POST.getlist('roles[]', [])

        if not roles:
            return JsonResponse({
                'success': False,
                'error': 'At least one role must be selected.'
            }, status=400)

        # Validate required fields based on roles
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')

        if not all([email, password, first_name, last_name, phone]):
            return JsonResponse({
                'success': False,
                'error': 'All basic fields are required.'
            }, status=400)

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'error': 'An account with this email already exists.'
            }, status=400)

        # Check if phone already exists
        if (User.objects.filter(phone=phone).exists() or
            VendorProfile.objects.filter(phone=phone).exists() or
            CourierProfile.objects.filter(phone=phone).exists()):
            return JsonResponse({
                'success': False,
                'error': 'This phone number is already registered.'
            }, status=400)

        # Validate role-specific fields
        profile_data = {}

        if 'vendor' in roles:
            business_name = request.POST.get('business_name')
            business_category = request.POST.get('business_category')
            business_address = request.POST.get('business_address')

            if not all([business_name, business_category, business_address]):
                return JsonResponse({
                    'success': False,
                    'error': 'Business name, category, and address are required for vendor registration.'
                }, status=400)

            profile_data.update({
                'business_name': business_name,
                'business_category': business_category,
                'business_address': business_address,
                'business_description': request.POST.get('business_description', ''),
            })

        if 'courier' in roles:
            vehicle_type = request.POST.get('vehicle_type')
            if not vehicle_type:
                return JsonResponse({
                    'success': False,
                    'error': 'Vehicle type is required for courier registration.'
                }, status=400)

            profile_data.update({
                'service_areas': request.POST.get('service_areas', ''),
                'vehicle_type': vehicle_type,
                'has_bike': request.POST.get('has_bike', 'false').lower() == 'true',
            })

        # Create pending user
        pending_user = PendingUser.objects.create(
            email=email,
            password=password,  # Will be hashed when creating actual user
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            user_type=roles[0],  # Primary role
            verification_code=str(secrets.randbelow(900000) + 100000),
            profile_data=profile_data
        )

        # Return JSON response with verification details
        return JsonResponse({
            'success': True,
            'pending_user_id': pending_user.pk,
            'verification_code': pending_user.verification_code,
            'phone': pending_user.phone,
            'roles': roles,
            'message': f'Send "VERIFY {pending_user.verification_code}" to WhatsApp number {pending_user.phone}'
        })

    return JsonResponse({
        'success': False,
        'error': 'Method not allowed.'
    }, status=405)

def whatsapp_verification(request, pending_id):
    """Handle WhatsApp verification - return JSON response"""
    try:
        pending_user = PendingUser.objects.get(id=pending_id)

        if pending_user.is_expired:
            pending_user.delete()
            return JsonResponse({
                'success': False,
                'error': 'Verification session expired. Please start signup again.'
            }, status=400)

        return JsonResponse({
            'success': True,
            'verification_code': pending_user.verification_code,
            'phone': pending_user.phone,
            'whatsapp_number': '15551482837',  # Your business number
            'pending_id': pending_id,
            'expires_at': pending_user.expires_at.isoformat(),
            'user_type': pending_user.user_type,
            'message': f'Send "VERIFY {pending_user.verification_code}" to WhatsApp number {pending_user.phone}'
        })

    except PendingUser.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Verification session not found.'
        }, status=404)
