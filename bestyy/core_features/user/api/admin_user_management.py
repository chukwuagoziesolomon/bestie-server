"""
Admin API views for user management including suspension and activation.
These endpoints allow admins to suspend/activate vendors and couriers.
"""
import logging
from datetime import datetime
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from bestyy.core_features.user.permissions import IsAdminUser
from bestyy.core_features.user.models import User, VendorProfile, CourierProfile
from bestyy.core_features.user.utils import (
    send_vendor_notification, 
    send_courier_notification,
    notify_vendor_suspended,
    notify_vendor_activated,
    notify_courier_suspended,
    notify_courier_activated,
    record_activity
)

logger = logging.getLogger(__name__)


class UserSuspensionView(APIView):
    """
    API endpoint for suspending and activating vendors and couriers.
    Allows admins to manage user account status based on behavior and compliance.
    
    ## Permissions
    - User must be authenticated
    - User must be a superuser (is_superuser=True)
    
    ## Endpoints
    
    ### POST /api/admin/users/{type}/{id}/suspend/
    Suspend a vendor or courier account.
    
    #### Path Parameters
    - `type` (string): User type. Options: 'vendor', 'courier'
    - `id` (integer): ID of the vendor or courier profile
    
    #### Request Body
    ```json
    {
        "reason": "Violation of terms of service",
        "duration_days": 30,
        "notify_user": true
    }
    ```
    
    #### Response (200 OK)
    ```json
    {
        "success": true,
        "message": "Vendor account suspended successfully",
        "user": {
            "id": 1,
            "email": "vendor@example.com",
            "business_name": "Tasty Bites",
            "status": "suspended",
            "suspension_reason": "Violation of terms of service",
            "suspension_date": "2025-09-08T10:30:00Z",
            "suspension_duration_days": 30
        }
    }
    ```
    
    ### POST /api/admin/users/{type}/{id}/activate/
    Activate a previously suspended vendor or courier account.
    
    #### Path Parameters
    - `type` (string): User type. Options: 'vendor', 'courier'
    - `id` (integer): ID of the vendor or courier profile
    
    #### Request Body
    ```json
    {
        "reason": "Issue resolved, account reactivated",
        "notify_user": true
    }
    ```
    
    #### Response (200 OK)
    ```json
    {
        "success": true,
        "message": "Vendor account activated successfully",
        "user": {
            "id": 1,
            "email": "vendor@example.com",
            "business_name": "Tasty Bites",
            "status": "active",
            "activation_date": "2025-09-08T10:30:00Z"
        }
    }
    ```
    
    ### GET /api/admin/users/{type}/{id}/status/
    Get current status of a vendor or courier account.
    
    #### Path Parameters
    - `type` (string): User type. Options: 'vendor', 'courier'
    - `id` (integer): ID of the vendor or courier profile
    
    #### Response (200 OK)
    ```json
    {
        "user": {
            "id": 1,
            "email": "vendor@example.com",
            "business_name": "Tasty Bites",
            "status": "active",
            "suspension_reason": null,
            "suspension_date": null,
            "suspension_duration_days": null,
            "activation_date": "2025-09-01T10:30:00Z"
        }
    }
    ```
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def post(self, request, user_type=None, user_id=None):
        """Handle suspend and activate actions based on URL path."""
        action = request.path.split('/')[-2]  # Get 'suspend' or 'activate' from URL
        
        # Handle regular user suspension (no user_type parameter)
        if user_type is None:
            return self._suspend_regular_user(request, user_id, action)
        
        # Handle vendor/courier suspension (with user_type parameter)
        if action == 'suspend':
            return self._suspend_user(request, user_type, user_id)
        elif action == 'activate':
            return self._activate_user(request, user_type, user_id)
        else:
            return Response(
                {'error': 'Invalid action. Use /suspend/ or /activate/'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def get(self, request, user_type=None, user_id=None):
        """Get current status of a user account."""
        try:
            # Handle regular user status (no user_type parameter)
            if user_type is None:
                return self._get_regular_user_status(request, user_id)
            
            # Handle vendor/courier status (with user_type parameter)
            profile = self._get_profile(user_type, user_id)
            if not profile:
                return Response(
                    {'error': f'{user_type.title()} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            user_data = self._get_user_status_data(profile, user_type)
            
            return Response({
                'user': user_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting user status: {str(e)}")
            return Response(
                {'error': 'Failed to get user status'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _suspend_user(self, request, user_type, user_id):
        """Suspend a user account."""
        try:
            profile = self._get_profile(user_type, user_id)
            if not profile:
                return Response(
                    {'error': f'{user_type.title()} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if already suspended
            if hasattr(profile, 'is_suspended') and profile.is_suspended:
                return Response(
                    {'error': f'{user_type.title()} is already suspended'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get suspension details from request
            reason = request.data.get('reason', 'Account suspended by admin')
            duration_days = request.data.get('duration_days', None)
            notify_user = request.data.get('notify_user', True)
            
            # Suspend the account
            profile.is_suspended = True
            profile.suspension_reason = reason
            profile.suspension_date = timezone.now()
            profile.suspension_duration_days = duration_days
            profile.save()
            
            # Also suspend the user account
            user = profile.user
            user.is_active = False
            user.save()
            
            # Record activity
            record_activity(
                title='user_suspended',
                description=f'{user_type.title()} {user.email} suspended by admin',
                actor=request.user,
                target_type=user_type,
                target_id=profile.id,
                metadata={
                    'suspended_user_id': user.id,
                    'suspended_user_email': user.email,
                    'reason': reason,
                    'duration_days': duration_days
                }
            )
            
            # Send notification to user
            if notify_user:
                if user_type == 'vendor':
                    notify_vendor_suspended(profile, request.user, reason, duration_days)
                elif user_type == 'courier':
                    notify_courier_suspended(profile, request.user, reason, duration_days)
            
            user_data = self._get_user_status_data(profile, user_type)
            
            return Response({
                'success': True,
                'message': f'{user_type.title()} account suspended successfully',
                'user': user_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error suspending user: {str(e)}")
            return Response(
                {'error': 'Failed to suspend user account'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _activate_user(self, request, user_type, user_id):
        """Activate a suspended user account."""
        try:
            profile = self._get_profile(user_type, user_id)
            if not profile:
                return Response(
                    {'error': f'{user_type.title()} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if not suspended
            if not (hasattr(profile, 'is_suspended') and profile.is_suspended):
                return Response(
                    {'error': f'{user_type.title()} is not currently suspended'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get activation details from request
            reason = request.data.get('reason', 'Account reactivated by admin')
            notify_user = request.data.get('notify_user', True)
            
            # Activate the account
            profile.is_suspended = False
            profile.suspension_reason = None
            profile.suspension_date = None
            profile.suspension_duration_days = None
            profile.activation_date = timezone.now()
            profile.save()
            
            # Also activate the user account
            user = profile.user
            user.is_active = True
            user.save()
            
            # Record activity
            record_activity(
                title='user_activated',
                description=f'{user_type.title()} {user.email} activated by admin',
                actor=request.user,
                target_type=user_type,
                target_id=profile.id,
                metadata={
                    'activated_user_id': user.id,
                    'activated_user_email': user.email,
                    'reason': reason
                }
            )
            
            # Send notification to user
            if notify_user:
                if user_type == 'vendor':
                    notify_vendor_activated(profile, request.user, reason)
                elif user_type == 'courier':
                    notify_courier_activated(profile, request.user, reason)
            
            user_data = self._get_user_status_data(profile, user_type)
            
            return Response({
                'success': True,
                'message': f'{user_type.title()} account activated successfully',
                'user': user_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error activating user: {str(e)}")
            return Response(
                {'error': 'Failed to activate user account'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_profile(self, user_type, user_id):
        """Get vendor or courier profile by ID."""
        try:
            if user_type == 'vendor':
                return VendorProfile.objects.get(id=user_id)
            elif user_type == 'courier':
                return CourierProfile.objects.get(id=user_id)
            else:
                return None
        except (VendorProfile.DoesNotExist, CourierProfile.DoesNotExist):
            return None
    
    def _get_user_status_data(self, profile, user_type):
        """Get user status data for response."""
        user = profile.user
        
        data = {
            'id': profile.id,
            'email': user.email,
            'status': 'suspended' if (hasattr(profile, 'is_suspended') and profile.is_suspended) else 'active',
            'suspension_reason': getattr(profile, 'suspension_reason', None),
            'suspension_date': getattr(profile, 'suspension_date', None),
            'suspension_duration_days': getattr(profile, 'suspension_duration_days', None),
            'activation_date': getattr(profile, 'activation_date', None)
        }
        
        # Add type-specific fields
        if user_type == 'vendor':
            data['business_name'] = profile.business_name
        elif user_type == 'courier':
            data['full_name'] = user.get_full_name() or user.email
        
        return data

    def _suspend_regular_user(self, request, user_id, action):
        """Suspend or activate a regular user (not vendor/courier)."""
        try:
            user = User.objects.get(id=user_id)
            
            # Check if user has vendor or courier profile
            if hasattr(user, 'vendor_profile') or hasattr(user, 'courier_profile'):
                return Response(
                    {'error': 'This user has a vendor or courier profile. Use the appropriate endpoint.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if action == 'suspend':
                if not user.is_active:
                    return Response(
                        {'error': 'User account is already suspended'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Get suspension details from request
                reason = request.data.get('reason', 'Account suspended by admin')
                duration_days = request.data.get('duration_days', None)
                notify_user = request.data.get('notify_user', True)
                
                # Suspend the user account
                user.is_active = False
                user.save()
                
                # Record activity
                record_activity(
                    title='user_suspended',
                    description=f'Regular user {user.email} suspended by admin',
                    actor=request.user,
                    target_type='user',
                    target_id=user.id,
                    metadata={
                        'suspended_user_id': user.id,
                        'suspended_user_email': user.email,
                        'reason': reason,
                        'duration_days': duration_days
                    }
                )
                
                user_data = {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'status': 'suspended',
                    'suspension_reason': reason,
                    'suspension_date': timezone.now().isoformat(),
                    'suspension_duration_days': duration_days,
                    'activation_date': None
                }
                
                return Response({
                    'success': True,
                    'message': 'User account suspended successfully',
                    'user': user_data
                }, status=status.HTTP_200_OK)
            
            elif action == 'activate':
                if user.is_active:
                    return Response(
                        {'error': 'User account is not suspended'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Get activation details from request
                reason = request.data.get('reason', 'Account reactivated by admin')
                notify_user = request.data.get('notify_user', True)
                
                # Activate the user account
                user.is_active = True
                user.save()
                
                # Record activity
                record_activity(
                    title='user_activated',
                    description=f'Regular user {user.email} activated by admin',
                    actor=request.user,
                    target_type='user',
                    target_id=user.id,
                    metadata={
                        'activated_user_id': user.id,
                        'activated_user_email': user.email,
                        'reason': reason
                    }
                )
                
                user_data = {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'status': 'active',
                    'suspension_reason': None,
                    'suspension_date': None,
                    'suspension_duration_days': None,
                    'activation_date': timezone.now().isoformat()
                }
                
                return Response({
                    'success': True,
                    'message': 'User account activated successfully',
                    'user': user_data
                }, status=status.HTTP_200_OK)
            
            else:
                return Response(
                    {'error': 'Invalid action. Use /suspend/ or /activate/'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error managing regular user: {str(e)}")
            return Response(
                {'error': 'Failed to manage user account'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_regular_user_status(self, request, user_id):
        """Get status of a regular user (not vendor/courier)."""
        try:
            user = User.objects.get(id=user_id)
            
            # Check if user has vendor or courier profile
            if hasattr(user, 'vendor_profile') or hasattr(user, 'courier_profile'):
                return Response(
                    {'error': 'This user has a vendor or courier profile. Use the appropriate endpoint.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user_data = {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'status': 'active' if user.is_active else 'suspended',
                'suspension_reason': None,  # Regular users don't have detailed suspension info
                'suspension_date': None,
                'suspension_duration_days': None,
                'activation_date': None
            }
            
            return Response({
                'user': user_data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error getting regular user status: {str(e)}")
            return Response(
                {'error': 'Failed to get user status'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SuspendedUsersListView(APIView):
    """
    API endpoint to get a list of all suspended users (vendors and couriers).
    
    ## Permissions
    - User must be authenticated
    - User must be a superuser (is_superuser=True)
    
    ## Query Parameters
    - `type` (string, optional): Filter by user type ('vendor', 'courier', or omit for both)
    - `page` (integer, optional): Page number for pagination (default: 1)
    - `page_size` (integer, optional): Number of items per page (default: 10, max: 100)
    - `search` (string, optional): Search in names, emails, business names
    
    ## Response Format
    ```json
    {
        "suspended_vendors": {
            "count": 2,
            "results": [
                {
                    "id": 1,
                    "email": "vendor@example.com",
                    "business_name": "Tasty Bites",
                    "suspension_reason": "Violation of terms",
                    "suspension_date": "2025-09-08T10:30:00Z",
                    "suspension_duration_days": 30
                }
            ]
        },
        "suspended_couriers": {
            "count": 1,
            "results": [
                {
                    "id": 1,
                    "email": "courier@example.com",
                    "full_name": "John Doe",
                    "suspension_reason": "Poor service quality",
                    "suspension_date": "2025-09-08T10:30:00Z",
                    "suspension_duration_days": 14
                }
            ]
        },
        "summary": {
            "total_suspended": 3,
            "vendors_suspended": 2,
            "couriers_suspended": 1
        }
    }
    ```
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        try:
            user_type = request.query_params.get('type')
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 10)), 100)
            search = request.query_params.get('search', '')
            
            response_data = {}
            
            # Get suspended vendors
            if not user_type or user_type == 'vendor':
                suspended_vendors = self._get_suspended_vendors(search, page, page_size)
                response_data['suspended_vendors'] = suspended_vendors
            
            # Get suspended couriers
            if not user_type or user_type == 'courier':
                suspended_couriers = self._get_suspended_couriers(search, page, page_size)
                response_data['suspended_couriers'] = suspended_couriers
            
            # Add summary
            total_vendors = response_data.get('suspended_vendors', {}).get('count', 0)
            total_couriers = response_data.get('suspended_couriers', {}).get('count', 0)
            
            response_data['summary'] = {
                'total_suspended': total_vendors + total_couriers,
                'vendors_suspended': total_vendors,
                'couriers_suspended': total_couriers
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting suspended users: {str(e)}")
            return Response(
                {'error': 'Failed to fetch suspended users'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_suspended_vendors(self, search, page, page_size):
        """Get paginated list of suspended vendors."""
        from django.core.paginator import Paginator
        
        queryset = VendorProfile.objects.filter(
            is_suspended=True
        ).select_related('user')
        
        if search:
            queryset = queryset.filter(
                Q(user__email__icontains=search) |
                Q(business_name__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        results = []
        for vendor in page_obj:
            results.append({
                'id': vendor.id,
                'email': vendor.user.email,
                'business_name': vendor.business_name,
                'suspension_reason': vendor.suspension_reason,
                'suspension_date': vendor.suspension_date.isoformat() if vendor.suspension_date else None,
                'suspension_duration_days': vendor.suspension_duration_days
            })
        
        return {
            'count': paginator.count,
            'results': results,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages
        }
    
    def _get_suspended_couriers(self, search, page, page_size):
        """Get paginated list of suspended couriers."""
        from django.core.paginator import Paginator
        from django.db.models import Q
        
        queryset = CourierProfile.objects.filter(
            is_suspended=True
        ).select_related('user')
        
        if search:
            queryset = queryset.filter(
                Q(user__email__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        results = []
        for courier in page_obj:
            results.append({
                'id': courier.id,
                'email': courier.user.email,
                'full_name': courier.user.get_full_name() or courier.user.email,
                'suspension_reason': courier.suspension_reason,
                'suspension_date': courier.suspension_date.isoformat() if courier.suspension_date else None,
                'suspension_duration_days': courier.suspension_duration_days
            })
        
        return {
            'count': paginator.count,
            'results': results,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages
        }
