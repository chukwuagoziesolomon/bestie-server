"""
Admin API views for vendor management.
These endpoints are protected and only accessible by admin users.
"""
import logging
from datetime import timedelta
from decimal import Decimal
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView

from bestyy.core_features.user.models import VendorProfile, CourierProfile, User, SystemSettings
from bestyy.restaurant_features.order.models import Order
from bestyy.core_features.user.serializers.vendor_serializers import VendorProfileSerializer
from bestyy.core_features.user.serializers.courier_serializers import CourierProfileSerializer
from bestyy.core_features.user.permissions import IsAdminUser
from bestyy.core_features.user.utils.websocket_notifications import (
    notify_vendor_approved,
    notify_vendor_rejected,
    notify_courier_approved,
    notify_courier_rejected,
    record_activity
)
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Q
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AdminDashboardMetricsView(APIView):
    """
    API endpoint to get dashboard metrics for admin users.
    Returns counts of users, vendors, couriers, and other relevant metrics.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        from django.contrib.auth import get_user_model
        from user.models import VendorProfile, CourierProfile
        
        User = get_user_model()
        
        # Get total counts
        total_users = User.objects.count()
        total_vendors = VendorProfile.objects.count()
        total_couriers = CourierProfile.objects.count()
        
        # Get today's date and calculate date ranges
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Get new user registrations
        new_users_week = User.objects.filter(date_joined__date__gte=week_ago).count()
        new_users_month = User.objects.filter(date_joined__date__gte=month_ago).count()
        
        # Get pending verifications
        pending_vendors = VendorProfile.objects.filter(verification_status='pending').count()
        pending_couriers = CourierProfile.objects.filter(verification_status='pending').count()
        
        # Get active users (logged in last 30 days)
        active_users = User.objects.filter(last_login__date__gte=month_ago).count()
        
        # Get user growth data for chart (last 30 days)
        user_growth = []
        for i in range(30, -1, -1):
            date = today - timedelta(days=i)
            count = User.objects.filter(date_joined__date__lte=date).count()
            user_growth.append({
                'date': date.isoformat(),
                'count': count
            })
        
        response_data = {
            'totals': {
                'users': total_users,
                'vendors': total_vendors,
                'couriers': total_couriers,
                'active_users': active_users,
            },
            'new_users': {
                'week': new_users_week,
                'month': new_users_month,
            },
            'pending_verifications': {
                'vendors': pending_vendors,
                'couriers': pending_couriers,
            },
            'user_growth': user_growth,
        }
        
        return Response(response_data)


class PendingVendorsList(ListAPIView):
    """
    API endpoint that lists vendors with filtering and pagination.
    Only accessible by admin users.
    
    ## Permissions
    - User must be authenticated
    - User must be a staff member (is_staff=True)
    
    ## Query Parameters
    - `status` (string, optional): Filter by verification status. 
      - Allowed values: 'pending', 'approved', 'rejected'
      - Default: 'pending'
    - `search` (string, optional): Search in business name, email, or CAC number
    - `page` (integer, optional): Page number for pagination. Default: 1
    - `page_size` (integer, optional): Number of items per page. Default: 10, Max: 100
    
    ## Response Format
    ```json
    {
        "count": 42,
        "num_pages": 5,
        "current_page": 1,
        "results": [
            {
                "id": 1,
                "business_name": "Vendor Name",
                "verification_status": "pending",
                "created_at": "2023-01-01T12:00:00Z",
                "user": {
                    "id": 1,
                    "email": "vendor@example.com"
                }
            }
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    serializer_class = VendorProfileSerializer
    pagination_class = None  # We'll use custom pagination
    
    def get_queryset(self):
        queryset = VendorProfile.objects.all()
        
        # Filter by verification status
        status = self.request.query_params.get('status', 'pending')
        if status in ['pending', 'approved', 'rejected']:
            queryset = queryset.filter(verification_status=status)
        
        # Search in business name, email, or CAC number
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(business_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(cac_number__icontains=search)
            )
        
        # VendorProfile supports created_at; order newest first
        return queryset.select_related('user').order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get pagination parameters
        page_size = min(100, int(request.query_params.get('page_size', 10)))
        page = int(request.query_params.get('page', 1))
        
        # Paginate the queryset
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        # Serialize the page
        serializer = self.get_serializer(page_obj, many=True)
        
        return Response({
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'results': serializer.data
        })


class VendorVerificationView(APIView):
    """
    API endpoint for managing vendor verification status.
    Only accessible by admin users.
    
    ## Permissions
    - User must be authenticated
    - User must be a staff member (is_staff=True)
    
    ## Endpoints
    
    ### GET /admin/vendors/{vendor_id}/
    Get detailed information about a specific vendor.
    
    #### Response (200 OK)
    ```json
    {
        "id": 1,
        "business_name": "Vendor Name",
        "verification_status": "pending",
        "verification_date": null,
        "verification_notes": null,
        "created_at": "2023-01-01T12:00:00Z",
        "user": {
            "id": 1,
            "email": "vendor@example.com",
            "first_name": "John",
            "last_name": "Doe"
        }
    }
    ```
    
    ### POST /admin/vendors/{vendor_id}/approve/
    Approve a vendor's verification.
    
    #### Response (200 OK)
    ```json
    {
        "detail": "Vendor Vendor Name has been approved.",
        "vendor": {
            "id": 1,
            "business_name": "Vendor Name",
            "verification_status": "approved",
            "verification_date": "2023-01-01T12:00:00Z"
        }
    }
    ```
    
    ### POST /admin/vendors/{vendor_id}/reject/
    Reject a vendor's verification.
    
    #### Request Body
    ```json
    {
        "reason": "Incomplete documentation provided"
    }
    ```
    
    #### Response (200 OK)
    ```json
    {
        "detail": "Vendor Vendor Name has been rejected.",
        "vendor": {
            "id": 1,
            "business_name": "Vendor Name",
            "verification_status": "rejected",
            "verification_notes": "Incomplete documentation provided",
            "verification_date": "2023-01-01T12:00:00Z"
        }
    }
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def post(self, request, vendor_id):
        """
        Handle vendor verification actions (approve/reject).
        The action is determined by the URL path.
        
        For rejections, expected POST data:
        {
            "reason": "Reason for rejection"
        }
        """
        vendor = get_object_or_404(VendorProfile, id=vendor_id)
        
        # Determine if this is an approve or reject action based on URL
        if request.path.endswith('/approve/'):
            return self._approve_vendor(vendor)
        elif request.path.endswith('/reject/'):
            return self._reject_vendor(request, vendor)
        else:
            return Response(
                {"detail": "Invalid endpoint. Use /approve/ or /reject/."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _approve_vendor(self, vendor):
        """Approve a vendor's verification."""
        vendor.verification_status = 'approved'
        vendor.verification_date = timezone.now()
        vendor.save()
        
        try:
            # Send WebSocket notifications
            notify_vendor_approved(vendor, self.request.user)
            logger.info(f"Vendor {vendor.id} approved by {self.request.user.email}")
            # Record activity
            record_activity(
                title='Vendor approved',
                description=f"{vendor.business_name} was approved",
                icon='store',
                color='#10B981',
                actor=self.request.user,
                target_type='vendor',
                target_id=vendor.id,
                metadata={'vendor_id': vendor.id, 'business_name': vendor.business_name}
            )
        except Exception as e:
            logger.error(f"Failed to send approval notification: {str(e)}")
        
        return Response(
            {
                "detail": f"Vendor {vendor.business_name} has been approved.",
                "vendor": VendorProfileSerializer(vendor).data
            },
            status=status.HTTP_200_OK
        )
    
    def _reject_vendor(self, request, vendor):
        """Reject a vendor's verification with a reason."""
        reason = request.data.get('reason', '').strip()
        if not reason:
            reason = "Verification rejected by admin"
            
        vendor.verification_status = 'rejected'
        vendor.verification_notes = reason
        vendor.verification_date = timezone.now()
        vendor.save()
        
        try:
            # Send WebSocket notifications
            notify_vendor_rejected(vendor, request.user, reason)
            logger.info(f"Vendor {vendor.id} rejected by {request.user.email}")
            # Record activity
            record_activity(
                title='Vendor rejected',
                description=f"{vendor.business_name} was rejected",
                icon='store',
                color='#EF4444',
                actor=request.user,
                target_type='vendor',
                target_id=vendor.id,
                metadata={'vendor_id': vendor.id, 'business_name': vendor.business_name, 'reason': reason}
            )
        except Exception as e:
            logger.error(f"Failed to send rejection notification: {str(e)}")
        
        return Response(
            {
                "detail": f"Vendor {vendor.business_name} has been rejected.",
                "vendor": VendorProfileSerializer(vendor).data
            },
            status=status.HTTP_200_OK
        )
    
    def get(self, request, vendor_id):
        """
        Get vendor details for verification.
        """
        vendor = get_object_or_404(VendorProfile, id=vendor_id)
        return Response(
            VendorProfileSerializer(vendor).data,
            status=status.HTTP_200_OK
        )


class VendorStatsView(APIView):
    """
    API endpoint that provides vendor statistics for the admin dashboard.
    Only accessible by admin users.
    
    ## Permissions
    - User must be authenticated
    - User must be a staff member (is_staff=True)
    
    ## Response Format
    
    ```json
    {
        "status_counts": {
            "pending": 5,
            "approved": 42,
            "rejected": 3
        },
        "total_vendors": 50,
        "recent_registrations": [
            {
                "id": 50,
                "business_name": "New Vendor",
                "verification_status": "pending",
                "created_at": "2023-01-01T12:00:00Z",
                "user": {
                    "id": 100,
                    "email": "new@example.com"
                }
            }
        ],
        "recent_verifications": [
            {
                "id": 49,
                "business_name": "Verified Vendor",
                "verification_status": "approved",
                "verification_date": "2023-01-01T11:30:00Z",
                "verification_notes": null,
                "user": {
                    "id": 99,
                    "email": "verified@example.com"
                }
            }
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        """
        Get vendor statistics including counts by status and recent activity.
        """
        # Get counts by verification status
        status_counts = dict(VendorProfile.objects.values_list('verification_status')
                                     .annotate(count=Count('id'))
                                     .order_by())
        
        # Ensure all statuses are in the response, even if count is 0
        for status in ['pending', 'approved', 'rejected']:
            status_counts[status] = status_counts.get(status, 0)
        
        # Get recent vendor registrations (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_registrations = VendorProfile.objects.filter(
            created_at__gte=thirty_days_ago
        ).order_by('-created_at')[:10]  # Last 10 registrations
        
        # Get recent verification actions (last 30 days)
        recent_verifications = VendorProfile.objects.filter(
            verification_date__isnull=False,
            verification_date__gte=thirty_days_ago
        ).order_by('-verification_date')[:10]  # Last 10 verifications
        
        return Response({
            'status_counts': status_counts,
            'total_vendors': sum(status_counts.values()),
            'recent_registrations': VendorProfileSerializer(
                recent_registrations, many=True
            ).data,
            'recent_verifications': VendorProfileSerializer(
                recent_verifications, many=True
            ).data,
        })


class PendingCouriersList(ListAPIView):
    """
    API endpoint that lists couriers with filtering and pagination.
    Only accessible by admin users.

    Query params:
    - status: 'pending' | 'approved' | 'rejected' (default 'pending')
    - search: search by name, email, phone, nin_number
    - page, page_size
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    serializer_class = CourierProfileSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = CourierProfile.objects.all()

        status_param = self.request.query_params.get('status', 'pending')
        if status_param in ['pending', 'approved', 'rejected']:
            queryset = queryset.filter(verification_status=status_param)

        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(phone__icontains=search)
                | Q(nin_number__icontains=search)
            )

        # CourierProfile has no created_at; order by newest id instead
        return queryset.select_related('user').order_by('-id')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page_size = min(100, int(request.query_params.get('page_size', 10)))
        page = int(request.query_params.get('page', 1))

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        serializer = self.get_serializer(page_obj, many=True)
        return Response({
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'results': serializer.data,
        })


class PendingVerificationsView(APIView):
    """
    Unified endpoint for pending verifications.

    GET /api/admin/verification/pending/?type=<vendor|courier>&status=pending&search=&page=1&page_size=10

    - If type is omitted or empty, defaults to 'vendor'.
    - If type='both', returns both vendor_results and courier_results (each paginated independently).
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        type_param = (request.query_params.get('type') or 'vendor').strip().lower()
        # Normalize common aliases
        if type_param == 'all':
            type_param = 'both'
        status_param = request.query_params.get('status', 'pending')
        search = request.query_params.get('search', '').strip()
        page_size = min(100, int(request.query_params.get('page_size', 10)))
        page = int(request.query_params.get('page', 1))

        def build_response_for(queryset, serializer_cls):
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            data = serializer_cls(page_obj, many=True).data
            return {
                'count': paginator.count,
                'num_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'results': data,
            }

        if type_param in ['', 'vendor']:
            # Vendors path (default)
            v_qs = VendorProfile.objects.all()
            if status_param in ['pending', 'approved', 'rejected']:
                v_qs = v_qs.filter(verification_status=status_param)
            if search:
                v_qs = v_qs.filter(
                    Q(business_name__icontains=search)
                    | Q(user__email__icontains=search)
                    | Q(cac_number__icontains=search)
                )
            v_qs = v_qs.select_related('user').order_by('-created_at')
            return Response(build_response_for(v_qs, VendorProfileSerializer))

        if type_param == 'courier':
            c_qs = CourierProfile.objects.all()
            if status_param in ['pending', 'approved', 'rejected']:
                c_qs = c_qs.filter(verification_status=status_param)
            if search:
                c_qs = c_qs.filter(
                    Q(user__first_name__icontains=search)
                    | Q(user__last_name__icontains=search)
                    | Q(user__email__icontains=search)
                    | Q(phone__icontains=search)
                    | Q(nin_number__icontains=search)
                )
            # CourierProfile has no created_at; order by id desc
            c_qs = c_qs.select_related('user').order_by('-id')
            return Response(build_response_for(c_qs, CourierProfileSerializer))

        if type_param == 'both':
            v_qs = VendorProfile.objects.all()
            if status_param in ['pending', 'approved', 'rejected']:
                v_qs = v_qs.filter(verification_status=status_param)
            if search:
                v_qs = v_qs.filter(
                    Q(business_name__icontains=search)
                    | Q(user__email__icontains=search)
                    | Q(cac_number__icontains=search)
                )
            v_qs = v_qs.select_related('user').order_by('-created_at')

            c_qs = CourierProfile.objects.all()
            if status_param in ['pending', 'approved', 'rejected']:
                c_qs = c_qs.filter(verification_status=status_param)
            if search:
                c_qs = c_qs.filter(
                    Q(user__first_name__icontains=search)
                    | Q(user__last_name__icontains=search)
                    | Q(user__email__icontains=search)
                    | Q(phone__icontains=search)
                    | Q(nin_number__icontains=search)
                )
            # CourierProfile has no created_at; order by id desc
            c_qs = c_qs.select_related('user').order_by('-id')

            return Response({
                'vendors': build_response_for(v_qs, VendorProfileSerializer),
                'couriers': build_response_for(c_qs, CourierProfileSerializer),
            })

        return Response({'detail': "Invalid 'type' parameter. Use 'vendor', 'courier', 'both' (or 'all')."}, status=status.HTTP_400_BAD_REQUEST)


class AdminUsersList(ListAPIView):
    """
    Admin endpoint to list and track regular users (not vendors or couriers).

    GET /api/admin/users/?search=&is_active=true|false&joined_after=YYYY-MM-DD&joined_before=YYYY-MM-DD&page=1&page_size=10

    Excludes staff/superusers and any account that has a VendorProfile or CourierProfile.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    pagination_class = None

    def get_queryset(self):
        qs = User.objects.all()
        # Exclude admins
        qs = qs.filter(is_staff=False, is_superuser=False)
        # Exclude accounts that are vendors or couriers
        qs = qs.filter(vendor_profile__isnull=True, courier_profile__isnull=True)

        # Filters
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(username__icontains=search)
            )

        is_active = self.request.query_params.get('is_active')
        if is_active in ['true', 'false']:
            qs = qs.filter(is_active=(is_active == 'true'))

        joined_after = self.request.query_params.get('joined_after')
        joined_before = self.request.query_params.get('joined_before')
        if joined_after:
            try:
                from datetime import datetime
                qs = qs.filter(date_joined__date__gte=datetime.fromisoformat(joined_after).date())
            except Exception:
                pass
        if joined_before:
            try:
                from datetime import datetime
                qs = qs.filter(date_joined__date__lte=datetime.fromisoformat(joined_before).date())
            except Exception:
                pass

        return qs.order_by('-date_joined')

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        page_size = min(100, int(request.query_params.get('page_size', 10)))
        page = int(request.query_params.get('page', 1))

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)

        def map_user(u: User):
            full_name = u.get_full_name() or u.username or u.email
            profile = getattr(u, 'profile', None)
            phone = getattr(profile, 'phone', None)
            address = getattr(profile, 'address', None)
            return {
                'id': u.id,
                'role': 'user',
                'email': u.email,
                'username': u.username,
                'full_name': full_name,
                'phone': phone,
                'address': address,
                'is_active': u.is_active,
                'last_login': u.last_login.isoformat() if u.last_login else None,
                'date_joined': u.date_joined.isoformat() if hasattr(u, 'date_joined') else None,
            }

        data = [map_user(u) for u in page_obj]
        return Response({
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'results': data,
        })


class PendingVerificationSummaryView(APIView):
    """
    Summarized, normalized view across vendors and couriers for admin.

    GET /api/admin/verification/summary/?type=vendor|courier|both|all&status=pending&search=&page=1&page_size=10

    Returns entries with fields:
    - profile_photo (URL)
    - role (vendor|courier)
    - full_name
    - phone_number
    - package_type (courier: vehicle_type; vendor: null)
    - date (vendor.created_at or user.date_joined)
    - address (vendor.business_address or user.profile.address if available)
    - id_image (URL)
    - cac_document (URL or null, vendors only)
    - nin_number (couriers only if provided)
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        type_param = (request.query_params.get('type') or 'vendor').strip().lower()
        if type_param == 'all':
            type_param = 'both'
        status_param = request.query_params.get('status', 'pending')
        search = request.query_params.get('search', '').strip()
        page_size = min(100, int(request.query_params.get('page_size', 10)))
        page = int(request.query_params.get('page', 1))

        def vendor_qs():
            qs = VendorProfile.objects.all()
            if status_param in ['pending', 'approved', 'rejected']:
                qs = qs.filter(verification_status=status_param)
            if search:
                qs = qs.filter(
                    Q(business_name__icontains=search)
                    | Q(user__email__icontains=search)
                    | Q(user__first_name__icontains=search)
                    | Q(user__last_name__icontains=search)
                    | Q(cac_number__icontains=search)
                )
            return qs.select_related('user').order_by('-created_at')

        def courier_qs():
            qs = CourierProfile.objects.all()
            if status_param in ['pending', 'approved', 'rejected']:
                qs = qs.filter(verification_status=status_param)
            if search:
                qs = qs.filter(
                    Q(user__first_name__icontains=search)
                    | Q(user__last_name__icontains=search)
                    | Q(user__email__icontains=search)
                    | Q(phone__icontains=search)
                    | Q(nin_number__icontains=search)
                )
            return qs.select_related('user').order_by('-id')  # no created_at

        results = []

        def abs_url(path):
            try:
                return self.request.build_absolute_uri(path) if path else None
            except Exception:
                return path

        def map_vendor(v: VendorProfile):
            user = v.user
            full_name = user.get_full_name() or user.username or user.email
            address = getattr(v, 'business_address', None)
            profile_photo = abs_url(v.logo.url) if getattr(v, 'logo', None) else None
            id_image = abs_url(v.valid_id.url) if getattr(v, 'valid_id', None) else None
            cac_document = abs_url(v.cac_document.url) if getattr(v, 'cac_document', None) else None
            return {
                'role': 'vendor',
                'full_name': full_name,
                'phone_number': v.phone,  # Changed from phone to phone_number
                'package_type': None,  # Vendors don't have package type
                'date': v.created_at.isoformat() if hasattr(v, 'created_at') and v.created_at else None,
                'address': address,
                'profile_photo': profile_photo,
                'id_image': id_image,  # Changed from id_document to id_image
                'cac_document': cac_document,
                'nin_number': None,  # Vendors don't have NIN
            }

        def map_courier(c: CourierProfile):
            user = c.user
            full_name = user.get_full_name() or user.username or user.email
            # Try pull address from UserProfile if exists
            address = getattr(getattr(user, 'profile', None), 'address', None)
            profile_photo = abs_url(c.profile_photo.url) if getattr(c, 'profile_photo', None) else None
            id_image = abs_url(c.id_upload.url) if getattr(c, 'id_upload', None) else None
            return {
                'role': 'courier',
                'full_name': full_name,
                'phone_number': c.phone,  # Changed from phone to phone_number
                'package_type': getattr(c, 'vehicle_type', None),  # Will be None if not set
                'date': user.date_joined.isoformat() if hasattr(user, 'date_joined') and user.date_joined else None,
                'address': address,
                'profile_photo': profile_photo,
                'id_image': id_image,  # Changed from id_document to id_image
                'cac_document': None,  # Couriers don't have CAC
                'nin_number': getattr(c, 'nin_number', None),  # Add NIN if available
            }

        if type_param in ['', 'vendor']:
            paginator = Paginator(vendor_qs(), page_size)
            page_obj = paginator.get_page(page)
            results = [map_vendor(v) for v in page_obj]
            return Response({
                'count': paginator.count,
                'num_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'results': results,
            })

        if type_param == 'courier':
            paginator = Paginator(courier_qs(), page_size)
            page_obj = paginator.get_page(page)
            results = [map_courier(c) for c in page_obj]
            return Response({
                'count': paginator.count,
                'num_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'results': results,
            })

        if type_param == 'both':
            v_paginator = Paginator(vendor_qs(), page_size)
            v_page_obj = v_paginator.get_page(page)
            c_paginator = Paginator(courier_qs(), page_size)
            c_page_obj = c_paginator.get_page(page)
            return Response({
                'vendors': {
                    'count': v_paginator.count,
                    'num_pages': v_paginator.num_pages,
                    'current_page': v_page_obj.number,
                    'results': [map_vendor(v) for v in v_page_obj],
                },
                'couriers': {
                    'count': c_paginator.count,
                    'num_pages': c_paginator.num_pages,
                    'current_page': c_page_obj.number,
                    'results': [map_courier(c) for c in c_page_obj],
                }
            })

        return Response({'detail': "Invalid 'type' parameter. Use 'vendor', 'courier', 'both' (or 'all')."}, status=status.HTTP_400_BAD_REQUEST)


class RegularUsersCountView(APIView):
    """
    API endpoint to get the total count of regular users (not vendors or couriers).
    Only accessible by admin users.
    
    ## Permissions
    - User must be authenticated
    - User must be a superuser (is_superuser=True)
    
    ## Response Format
    
    ```json
    {
        "total_regular_users": 150,
        "active_regular_users": 120,
        "new_users_this_month": 25,
        "new_users_this_week": 8
    }
    ```
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        """
        Get the total count of regular users (excluding vendors, couriers, and staff).
        """
        from datetime import timedelta
        
        # Get base queryset for regular users
        # Exclude staff, superusers, and users with vendor/courier profiles
        regular_users = User.objects.filter(
            is_staff=False,
            is_superuser=False,
            vendor_profile__isnull=True,
            courier_profile__isnull=True
        )
        
        # Get total count
        total_regular_users = regular_users.count()
        
        # Get active users (logged in last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        active_regular_users = regular_users.filter(
            last_login__date__gte=thirty_days_ago.date()
        ).count()
        
        # Get new users this month
        month_ago = timezone.now() - timedelta(days=30)
        new_users_this_month = regular_users.filter(
            date_joined__date__gte=month_ago.date()
        ).count()
        
        # Get new users this week
        week_ago = timezone.now() - timedelta(days=7)
        new_users_this_week = regular_users.filter(
            date_joined__date__gte=week_ago.date()
        ).count()
        
        return Response({
            'total_regular_users': total_regular_users,
            'active_regular_users': active_regular_users,
            'new_users_this_month': new_users_this_month,
            'new_users_this_week': new_users_this_week,
        })


class CourierVerificationView(APIView):
    """
    API endpoint for managing courier verification status.
    Only accessible by admin users.
    
    ## Permissions
    - User must be authenticated
    - User must be a superuser (is_superuser=True)
    
    ## Endpoints
    
    ### GET /admin/couriers/{courier_id}/
    Get detailed information about a specific courier for verification.
    
    #### Response (200 OK)
    ```json
    {
        "id": 1,
        "user": {
            "id": 1,
            "email": "courier@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "full_name": "John Doe"
        },
        "phone": "+1234567890",
        "service_areas": "Area 1, Area 2",
        "delivery_radius": "5km",
        "opening_hours": "08:00:00",
        "closing_hours": "18:00:00",
        "has_bike": true,
        "verification_preference": "NIN",
        "nin_number": "12345678901",
        "vehicle_type": "bike",
        "verification_status": "pending",
        "profile_photo": "http://example.com/photo.jpg",
        "id_upload": "http://example.com/id.jpg",
        "is_active": true,
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z"
    }
    ```
    
    ### POST /admin/couriers/{courier_id}/approve/
    Approve a courier's verification.
    
    #### Response (200 OK)
    ```json
    {
        "detail": "Courier John Doe has been approved.",
        "courier": {
            "id": 1,
            "verification_status": "approved",
            "updated_at": "2023-01-01T12:00:00Z"
        }
    }
    ```
    
    ### POST /admin/couriers/{courier_id}/reject/
    Reject a courier's verification.
    
    #### Request Body
    ```json
    {
        "reason": "Invalid identification document"
    }
    ```
    
    #### Response (200 OK)
    ```json
    {
        "detail": "Courier John Doe has been rejected.",
        "courier": {
            "id": 1,
            "verification_status": "rejected",
            "verification_notes": "Invalid identification document",
            "updated_at": "2023-01-01T12:00:00Z"
        }
    }
    ```
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def post(self, request, courier_id):
        """
        Handle courier verification actions (approve/reject).
        The action is determined by the URL path.
        
        For rejections, expected POST data:
        {
            "reason": "Reason for rejection"
        }
        """
        courier = get_object_or_404(CourierProfile, id=courier_id)
        
        # Determine if this is an approve or reject action based on URL
        if request.path.endswith('/approve/'):
            return self._approve_courier(courier)
        elif request.path.endswith('/reject/'):
            return self._reject_courier(request, courier)
        else:
            return Response(
                {"detail": "Invalid endpoint. Use /approve/ or /reject/."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _approve_courier(self, courier):
        """Approve a courier's verification."""
        courier.verification_status = 'approved'
        courier.save()
        
        try:
            # Send WebSocket notifications
            notify_courier_approved(courier, self.request.user)
            logger.info(f"Courier {courier.id} approved by {self.request.user.email}")
            # Record activity
            record_activity(
                title='Courier approved',
                description=f"{courier.user.get_full_name()} was approved",
                icon='delivery_truck',
                color='#10B981',
                actor=self.request.user,
                target_type='courier',
                target_id=courier.id,
                metadata={'courier_id': courier.id, 'user_name': courier.user.get_full_name()}
            )
        except Exception as e:
            logger.error(f"Failed to send approval notification: {str(e)}")
        
        return Response(
            {
                "detail": f"Courier {courier.user.get_full_name()} has been approved.",
                "courier": {
                    "id": courier.id,
                    "verification_status": courier.verification_status,
                    "updated_at": courier.updated_at.isoformat()
                }
            },
            status=status.HTTP_200_OK
        )
    
    def _reject_courier(self, request, courier):
        """Reject a courier's verification with a reason."""
        reason = request.data.get('reason', '').strip()
        if not reason:
            reason = "Verification rejected by admin"
            
        courier.verification_status = 'rejected'
        # Add verification_notes field to CourierProfile model if it doesn't exist
        if hasattr(courier, 'verification_notes'):
            courier.verification_notes = reason
        courier.save()
        
        try:
            # Send WebSocket notifications
            notify_courier_rejected(courier, request.user, reason)
            logger.info(f"Courier {courier.id} rejected by {request.user.email}")
            # Record activity
            record_activity(
                title='Courier rejected',
                description=f"{courier.user.get_full_name()} was rejected",
                icon='delivery_truck',
                color='#EF4444',
                actor=request.user,
                target_type='courier',
                target_id=courier.id,
                metadata={'courier_id': courier.id, 'user_name': courier.user.get_full_name(), 'reason': reason}
            )
        except Exception as e:
            logger.error(f"Failed to send rejection notification: {str(e)}")
        
        return Response(
            {
                "detail": f"Courier {courier.user.get_full_name()} has been rejected.",
                "courier": {
                    "id": courier.id,
                    "verification_status": courier.verification_status,
                    "verification_notes": getattr(courier, 'verification_notes', reason),
                    "updated_at": courier.updated_at.isoformat()
                }
            },
            status=status.HTTP_200_OK
        )
    
    def get(self, request, courier_id):
        """
        Get courier details for verification.
        """
        courier = get_object_or_404(CourierProfile, id=courier_id)
        
        # Build response data similar to the dashboard display
        response_data = {
            "id": courier.id,
            "user": {
                "id": courier.user.id,
                "email": courier.user.email,
                "first_name": courier.user.first_name,
                "last_name": courier.user.last_name,
                "full_name": courier.user.get_full_name() or f"{courier.user.first_name} {courier.user.last_name}".strip(),
                "date_joined": courier.user.date_joined.isoformat() if courier.user.date_joined else None,
            },
            "phone": courier.phone,
            "service_areas": courier.service_areas,
            "delivery_radius": courier.delivery_radius,
            "opening_hours": courier.opening_hours.strftime("%H:%M:%S") if courier.opening_hours else None,
            "closing_hours": courier.closing_hours.strftime("%H:%M:%S") if courier.closing_hours else None,
            "has_bike": courier.has_bike,
            "verification_preference": courier.verification_preference,
            "nin_number": courier.nin_number,
            "vehicle_type": courier.vehicle_type,
            "verification_status": courier.verification_status,
            "is_active": courier.is_active,
            "created_at": courier.created_at.isoformat() if courier.created_at else None,
            "updated_at": courier.updated_at.isoformat() if courier.updated_at else None,
        }
        
        # Add file URLs if they exist (handle Cloudinary URLs properly)
        from user.utils.cloudinary_verification_utils import get_verification_document_urls
        
        
        document_urls = get_verification_document_urls(courier)
        response_data.update(document_urls)
        
        # Add verification notes if available
        if hasattr(courier, 'verification_notes'):
            response_data["verification_notes"] = courier.verification_notes
        
        return Response(response_data, status=status.HTTP_200_OK)


class UnifiedVerificationView(APIView):
    """
    Unified API endpoint for managing verification of both vendors and couriers.
    Only accessible by admin users.
    
    ## Permissions
    - User must be authenticated
    - User must be a superuser (is_superuser=True)
    
    ## Endpoints
    
    ### GET /admin/verification/{type}/{id}/
    Get detailed information about a specific vendor or courier for verification.
    
    #### URL Parameters
    - `type`: Either 'vendor' or 'courier'
    - `id`: The ID of the vendor or courier profile
    
    #### Response (200 OK) - Vendor
    ```json
    {
        "type": "vendor",
        "id": 1,
        "user": {
            "id": 1,
            "email": "vendor@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "full_name": "John Doe",
            "date_joined": "2023-01-01T12:00:00Z"
        },
        "business_name": "John's Restaurant",
        "phone": "+1234567890",
        "business_address": "123 Main St",
        "cac_number": "RC123456",
        "verification_status": "pending",
        "verification_notes": null,
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "logo": "http://example.com/logo.jpg",
        "cac_document": "http://example.com/cac.pdf",
        "valid_id": "http://example.com/id.jpg"
    }
    ```
    
    #### Response (200 OK) - Courier
    ```json
    {
        "type": "courier",
        "id": 1,
        "user": {
            "id": 1,
            "email": "courier@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "full_name": "Jane Smith",
            "date_joined": "2023-01-01T12:00:00Z"
        },
        "phone": "+1234567890",
        "service_areas": "Area 1, Area 2",
        "delivery_radius": "5km",
        "vehicle_type": "bike",
        "nin_number": "12345678901",
        "verification_status": "pending",
        "verification_notes": null,
        "created_at": "2023-01-01T12:00:00Z",
        "updated_at": "2023-01-01T12:00:00Z",
        "profile_photo": "http://example.com/photo.jpg",
        "id_upload": "http://example.com/id.jpg"
    }
    ```
    
    ### POST /admin/verification/{type}/{id}/approve/
    Approve a vendor or courier's verification.
    
    #### Response (200 OK)
    ```json
    {
        "detail": "Vendor John's Restaurant has been approved.",
        "type": "vendor",
        "id": 1,
        "verification_status": "approved",
        "updated_at": "2023-01-01T12:00:00Z"
    }
    ```
    
    ### POST /admin/verification/{type}/{id}/reject/
    Reject a vendor or courier's verification.
    
    #### Request Body
    ```json
    {
        "reason": "Invalid documentation provided"
    }
    ```
    
    #### Response (200 OK)
    ```json
    {
        "detail": "Vendor John's Restaurant has been rejected.",
        "type": "vendor",
        "id": 1,
        "verification_status": "rejected",
        "verification_notes": "Invalid documentation provided",
        "updated_at": "2023-01-01T12:00:00Z"
    }
    ```
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request, verification_type, verification_id):
        """
        Get vendor or courier details for verification.
        """
        if verification_type == 'vendor':
            return self._get_vendor_details(request, verification_id)
        elif verification_type == 'courier':
            return self._get_courier_details(request, verification_id)
        else:
            return Response(
                {"detail": "Invalid verification type. Use 'vendor' or 'courier'."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def post(self, request, verification_type, verification_id):
        """
        Handle vendor or courier verification actions (approve/reject).
        """
        if verification_type == 'vendor':
            return self._handle_vendor_action(request, verification_id)
        elif verification_type == 'courier':
            return self._handle_courier_action(request, verification_id)
        else:
            return Response(
                {"detail": "Invalid verification type. Use 'vendor' or 'courier'."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _get_vendor_details(self, request, vendor_id):
        """Get vendor details for verification."""
        vendor = get_object_or_404(VendorProfile, id=vendor_id)
        
        response_data = {
            "type": "vendor",
            "id": vendor.id,
            "user": {
                "id": vendor.user.id,
                "email": vendor.user.email,
                "first_name": vendor.user.first_name,
                "last_name": vendor.user.last_name,
                "full_name": vendor.user.get_full_name() or f"{vendor.user.first_name} {vendor.user.last_name}".strip(),
                "date_joined": vendor.user.date_joined.isoformat() if vendor.user.date_joined else None,
            },
            "business_name": vendor.business_name,
            "phone": vendor.phone,
            "business_address": getattr(vendor, 'business_address', None),
            "cac_number": getattr(vendor, 'cac_number', None),
            "verification_status": vendor.verification_status,
            "verification_notes": getattr(vendor, 'verification_notes', None),
            "created_at": vendor.created_at.isoformat() if vendor.created_at else None,
            "updated_at": vendor.updated_at.isoformat() if vendor.updated_at else None,
        }
        
        # Add file URLs if they exist (handle Cloudinary URLs properly)
        from user.utils.cloudinary_verification_utils import get_verification_document_urls
        
        
        document_urls = get_verification_document_urls(vendor)
        response_data.update(document_urls)
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    def _get_courier_details(self, request, courier_id):
        """Get courier details for verification."""
        courier = get_object_or_404(CourierProfile, id=courier_id)
        
        response_data = {
            "type": "courier",
            "id": courier.id,
            "user": {
                "id": courier.user.id,
                "email": courier.user.email,
                "first_name": courier.user.first_name,
                "last_name": courier.user.last_name,
                "full_name": courier.user.get_full_name() or f"{courier.user.first_name} {courier.user.last_name}".strip(),
                "date_joined": courier.user.date_joined.isoformat() if courier.user.date_joined else None,
            },
            "phone": courier.phone,
            "service_areas": courier.service_areas,
            "delivery_radius": courier.delivery_radius,
            "vehicle_type": courier.vehicle_type,
            "nin_number": courier.nin_number,
            "verification_status": courier.verification_status,
            "verification_notes": getattr(courier, 'verification_notes', None),
            "created_at": courier.created_at.isoformat() if courier.created_at else None,
            "updated_at": courier.updated_at.isoformat() if courier.updated_at else None,
        }
        
        # Add file URLs if they exist (handle Cloudinary URLs properly)
        from user.utils.cloudinary_verification_utils import get_verification_document_urls
        
        
        document_urls = get_verification_document_urls(courier)
        response_data.update(document_urls)
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    def _handle_vendor_action(self, request, vendor_id):
        """Handle vendor approve/reject actions."""
        vendor = get_object_or_404(VendorProfile, id=vendor_id)
        
        if request.path.endswith('/approve/'):
            return self._approve_vendor(vendor)
        elif request.path.endswith('/reject/'):
            return self._reject_vendor(request, vendor)
        else:
            return Response(
                {"detail": "Invalid endpoint. Use /approve/ or /reject/."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _handle_courier_action(self, request, courier_id):
        """Handle courier approve/reject actions."""
        courier = get_object_or_404(CourierProfile, id=courier_id)
        
        if request.path.endswith('/approve/'):
            return self._approve_courier(courier)
        elif request.path.endswith('/reject/'):
            return self._reject_courier(request, courier)
        else:
            return Response(
                {"detail": "Invalid endpoint. Use /approve/ or /reject/."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _approve_vendor(self, vendor):
        """Approve a vendor's verification."""
        vendor.verification_status = 'approved'
        vendor.verification_date = timezone.now()
        vendor.save()
        
        try:
            # Send WebSocket notifications
            notify_vendor_approved(vendor, self.request.user)
            logger.info(f"Vendor {vendor.id} approved by {self.request.user.email}")
            # Record activity
            record_activity(
                title='Vendor approved',
                description=f"{vendor.business_name} was approved",
                icon='store',
                color='#10B981',
                actor=self.request.user,
                target_type='vendor',
                target_id=vendor.id,
                metadata={'vendor_id': vendor.id, 'business_name': vendor.business_name}
            )
        except Exception as e:
            logger.error(f"Failed to send approval notification: {str(e)}")
        
        return Response(
            {
                "detail": f"Vendor {vendor.business_name} has been approved.",
                "type": "vendor",
                "id": vendor.id,
                "verification_status": vendor.verification_status,
                "updated_at": vendor.updated_at.isoformat()
            },
            status=status.HTTP_200_OK
        )
    
    def _reject_vendor(self, request, vendor):
        """Reject a vendor's verification with a reason."""
        reason = request.data.get('reason', '').strip()
        if not reason:
            reason = "Verification rejected by admin"
            
        vendor.verification_status = 'rejected'
        vendor.verification_notes = reason
        vendor.verification_date = timezone.now()
        vendor.save()
        
        try:
            # Send WebSocket notifications
            notify_vendor_rejected(vendor, request.user, reason)
            logger.info(f"Vendor {vendor.id} rejected by {request.user.email}")
            # Record activity
            record_activity(
                title='Vendor rejected',
                description=f"{vendor.business_name} was rejected",
                icon='store',
                color='#EF4444',
                actor=request.user,
                target_type='vendor',
                target_id=vendor.id,
                metadata={'vendor_id': vendor.id, 'business_name': vendor.business_name, 'reason': reason}
            )
        except Exception as e:
            logger.error(f"Failed to send rejection notification: {str(e)}")
        
        return Response(
            {
                "detail": f"Vendor {vendor.business_name} has been rejected.",
                "type": "vendor",
                "id": vendor.id,
                "verification_status": vendor.verification_status,
                "verification_notes": vendor.verification_notes,
                "updated_at": vendor.updated_at.isoformat()
            },
            status=status.HTTP_200_OK
        )
    
    def _approve_courier(self, courier):
        """Approve a courier's verification."""
        courier.verification_status = 'approved'
        courier.save()
        
        try:
            # Send WebSocket notifications
            notify_courier_approved(courier, self.request.user)
            logger.info(f"Courier {courier.id} approved by {self.request.user.email}")
            # Record activity
            record_activity(
                title='Courier approved',
                description=f"{courier.user.get_full_name()} was approved",
                icon='delivery_truck',
                color='#10B981',
                actor=self.request.user,
                target_type='courier',
                target_id=courier.id,
                metadata={'courier_id': courier.id, 'user_name': courier.user.get_full_name()}
            )
        except Exception as e:
            logger.error(f"Failed to send approval notification: {str(e)}")
        
        return Response(
            {
                "detail": f"Courier {courier.user.get_full_name()} has been approved.",
                "type": "courier",
                "id": courier.id,
                "verification_status": courier.verification_status,
                "updated_at": courier.updated_at.isoformat()
            },
            status=status.HTTP_200_OK
        )
    
    def _reject_courier(self, request, courier):
        """Reject a courier's verification with a reason."""
        reason = request.data.get('reason', '').strip()
        if not reason:
            reason = "Verification rejected by admin"
            
        courier.verification_status = 'rejected'
        if hasattr(courier, 'verification_notes'):
            courier.verification_notes = reason
        courier.save()
        
        try:
            # Send WebSocket notifications
            notify_courier_rejected(courier, request.user, reason)
            logger.info(f"Courier {courier.id} rejected by {request.user.email}")
            # Record activity
            record_activity(
                title='Courier rejected',
                description=f"{courier.user.get_full_name()} was rejected",
                icon='delivery_truck',
                color='#EF4444',
                actor=request.user,
                target_type='courier',
                target_id=courier.id,
                metadata={'courier_id': courier.id, 'user_name': courier.user.get_full_name(), 'reason': reason}
            )
        except Exception as e:
            logger.error(f"Failed to send rejection notification: {str(e)}")
        
        return Response(
            {
                "detail": f"Courier {courier.user.get_full_name()} has been rejected.",
                "type": "courier",
                "id": courier.id,
                "verification_status": courier.verification_status,
                "verification_notes": getattr(courier, 'verification_notes', reason),
                "updated_at": courier.updated_at.isoformat()
            },
            status=status.HTTP_200_OK
        )


class AllPendingVerificationsView(APIView):
    """
    Unified API endpoint to get all pending verifications (both vendors and couriers) in one response.
    Only accessible by admin users.
    
    ## Permissions
    - User must be authenticated
    - User must be a superuser (is_superuser=True)
    
    ## Endpoints
    
    ### GET /admin/verification/pending/
    Get all pending verifications for both vendors and couriers.
    
    #### Query Parameters
    - `type` (string, optional): Filter by type ('vendor', 'courier', or omit for both)
    - `page` (integer, optional): Page number for pagination (default: 1)
    - `page_size` (integer, optional): Number of items per page (default: 10, max: 100)
    - `search` (string, optional): Search in names, emails, business names
    
    #### Response (200 OK)
    ```json
    {
        "vendors": {
            "count": 5,
            "results": [
                {
                    "type": "vendor",
                    "id": 1,
                    "user": {
                        "id": 1,
                        "email": "vendor@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "full_name": "John Doe",
                        "date_joined": "2023-01-01T12:00:00Z"
                    },
                    "business_name": "John's Restaurant",
                    "phone": "+1234567890",
                    "verification_status": "pending",
                    "created_at": "2023-01-01T12:00:00Z",
                    "logo": "https://res.cloudinary.com/.../logo.jpg",
                    "cac_document": "https://res.cloudinary.com/.../cac.pdf"
                }
            ]
        },
        "couriers": {
            "count": 3,
            "results": [
                {
                    "type": "courier",
                    "id": 1,
                    "user": {
                        "id": 2,
                        "email": "courier@example.com",
                        "first_name": "Jane",
                        "last_name": "Smith",
                        "full_name": "Jane Smith",
                        "date_joined": "2023-01-01T12:00:00Z"
                    },
                    "phone": "+1234567890",
                    "vehicle_type": "bike",
                    "verification_status": "pending",
                    "created_at": "2023-01-01T12:00:00Z",
                    "profile_photo": "https://res.cloudinary.com/.../photo.jpg",
                    "id_upload": "https://res.cloudinary.com/.../id.jpg"
                }
            ]
        },
        "summary": {
            "total_pending": 8,
            "vendors_pending": 5,
            "couriers_pending": 3
        }
    }
    ```
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        """
        Get all pending verifications for both vendors and couriers.
        """
        from django.core.paginator import Paginator
        
        # Get query parameters
        type_filter = request.query_params.get('type', '').strip().lower()
        search = request.query_params.get('search', '').strip()
        page_size = min(100, int(request.query_params.get('page_size', 10)))
        page = int(request.query_params.get('page', 1))
        
        response_data = {
            "vendors": {"count": 0, "results": []},
            "couriers": {"count": 0, "results": []},
            "summary": {
                "total_pending": 0,
                "vendors_pending": 0,
                "couriers_pending": 0
            }
        }
        
        # Get vendors if requested
        if type_filter in ['', 'vendor']:
            vendors = self._get_pending_vendors(search)
            vendor_paginator = Paginator(vendors, page_size)
            vendor_page = vendor_paginator.get_page(page)
            
            vendor_results = []
            for vendor in vendor_page:
                vendor_data = self._build_vendor_data(vendor)
                vendor_results.append(vendor_data)
            
            response_data["vendors"] = {
                "count": vendor_paginator.count,
                "num_pages": vendor_paginator.num_pages,
                "current_page": vendor_page.number,
                "results": vendor_results
            }
        
        # Get couriers if requested
        if type_filter in ['', 'courier']:
            couriers = self._get_pending_couriers(search)
            courier_paginator = Paginator(couriers, page_size)
            courier_page = courier_paginator.get_page(page)
            
            courier_results = []
            for courier in courier_page:
                courier_data = self._build_courier_data(courier)
                courier_results.append(courier_data)
            
            response_data["couriers"] = {
                "count": courier_paginator.count,
                "num_pages": courier_paginator.num_pages,
                "current_page": courier_page.number,
                "results": courier_results
            }
        
        # Update summary
        response_data["summary"] = {
            "total_pending": response_data["vendors"]["count"] + response_data["couriers"]["count"],
            "vendors_pending": response_data["vendors"]["count"],
            "couriers_pending": response_data["couriers"]["count"]
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    def _get_pending_vendors(self, search):
        """Get pending vendors with optional search."""
        vendors = VendorProfile.objects.filter(verification_status='pending').select_related('user')
        
        if search:
            vendors = vendors.filter(
                Q(business_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )
        
        return vendors.order_by('-created_at')
    
    def _get_pending_couriers(self, search):
        """Get pending couriers with optional search."""
        couriers = CourierProfile.objects.filter(verification_status='pending').select_related('user')
        
        if search:
            couriers = couriers.filter(
                Q(user__email__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(phone__icontains=search) |
                Q(nin_number__icontains=search)
            )
        
        return couriers.order_by('-created_at')
    
    def _build_vendor_data(self, vendor):
        """Build vendor data for response."""
        from user.utils.cloudinary_verification_utils import get_verification_document_urls
        
        vendor_data = {
            "type": "vendor",
            "id": vendor.id,
            "user": {
                "id": vendor.user.id,
                "email": vendor.user.email,
                "first_name": vendor.user.first_name,
                "last_name": vendor.user.last_name,
                "full_name": vendor.user.get_full_name() or f"{vendor.user.first_name} {vendor.user.last_name}".strip(),
                "date_joined": vendor.user.date_joined.isoformat() if vendor.user.date_joined else None,
            },
            "business_name": vendor.business_name,
            "phone": vendor.phone,
            "business_address": getattr(vendor, 'business_address', None),
            "cac_number": getattr(vendor, 'cac_number', None),
            "verification_status": vendor.verification_status,
            "verification_notes": getattr(vendor, 'verification_notes', None),
            "created_at": vendor.created_at.isoformat() if vendor.created_at else None,
            "updated_at": vendor.updated_at.isoformat() if vendor.updated_at else None,
        }
        
        # Add document URLs
        document_urls = get_verification_document_urls(vendor)
        vendor_data.update(document_urls)
        
        return vendor_data
    
    def _build_courier_data(self, courier):
        """Build courier data for response."""
        from user.utils.cloudinary_verification_utils import get_verification_document_urls
        
        courier_data = {
            "type": "courier",
            "id": courier.id,
            "user": {
                "id": courier.user.id,
                "email": courier.user.email,
                "first_name": courier.user.first_name,
                "last_name": courier.user.last_name,
                "full_name": courier.user.get_full_name() or f"{courier.user.first_name} {courier.user.last_name}".strip(),
                "date_joined": courier.user.date_joined.isoformat() if courier.user.date_joined else None,
            },
            "phone": courier.phone,
            "service_areas": courier.service_areas,
            "delivery_radius": courier.delivery_radius,
            "vehicle_type": courier.vehicle_type,
            "nin_number": courier.nin_number,
            "verification_status": courier.verification_status,
            "verification_notes": getattr(courier, 'verification_notes', None),
            "created_at": courier.created_at.isoformat() if courier.created_at else None,
            "updated_at": courier.updated_at.isoformat() if courier.updated_at else None,
        }
        
        # Add document URLs
        document_urls = get_verification_document_urls(courier)
        courier_data.update(document_urls)
        
        return courier_data


class ProfitAnalyticsView(APIView):
    """
    API endpoint for calculating total platform profit from completed orders.
    Profit is only recorded when orders are marked as 'completed' (user confirms receipt).

    ## Permissions
    - User must be authenticated
    - User must be a staff member (is_staff=True)

    ## Endpoints

    ### GET /api/user/admin/profit/
    Get total profit analytics with optional date filtering.

    #### Query Parameters
    - `start_date` (string, optional): Start date in YYYY-MM-DD format
    - `end_date` (string, optional): End date in YYYY-MM-DD format
    - `period` (string, optional): Quick period filter ('today', 'week', 'month', 'year')

    #### Response (200 OK)
    ```json
    {
        "total_profit": "15000.00",
        "total_revenue": "150000.00",
        "total_orders": 150,
        "average_profit_per_order": "100.00",
        "profit_margin_percentage": "10.00",
        "period": {
            "start_date": "2023-01-01",
            "end_date": "2023-12-31"
        },
        "breakdown": {
            "commission_revenue": "15000.00",
            "delivery_fees": "0.00",
            "other_revenue": "0.00"
        },
        "monthly_trend": [
            {
                "month": "2023-01",
                "profit": "1200.00",
                "orders": 12
            }
        ]
    }
    ```

    ### GET /api/user/admin/profit/detailed/
    Get detailed profit breakdown by order with pagination.

    #### Query Parameters
    - `start_date` (string, optional): Start date in YYYY-MM-DD format
    - `end_date` (string, optional): End date in YYYY-MM-DD format
    - `page` (integer, optional): Page number (default: 1)
    - `page_size` (integer, optional): Items per page (default: 20, max: 100)

    #### Response (200 OK)
    ```json
    {
        "count": 150,
        "num_pages": 8,
        "current_page": 1,
        "results": [
            {
                "order_id": 123,
                "order_number": "ORD-00123",
                "completed_at": "2023-01-01T12:00:00Z",
                "total_amount": "1000.00",
                "platform_commission": "100.00",
                "delivery_fee": "500.00",
                "vendor_payout": "900.00",
                "courier_payout": "500.00",
                "profit": "100.00"
            }
        ],
        "summary": {
            "total_profit": "15000.00",
            "total_revenue": "150000.00"
        }
    }
    ```
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request, detailed=None):
        """Get profit analytics."""
        if detailed:
            return self._get_detailed_profit(request)
        else:
            return self._get_profit_summary(request)

    def _get_date_range(self, request):
        """Get date range from request parameters."""
        from datetime import datetime, timedelta

        # Check for period filter first
        period = request.query_params.get('period')
        if period:
            today = timezone.now().date()
            if period == 'today':
                start_date = today
                end_date = today
            elif period == 'week':
                start_date = today - timedelta(days=7)
                end_date = today
            elif period == 'month':
                start_date = today - timedelta(days=30)
                end_date = today
            elif period == 'year':
                start_date = today - timedelta(days=365)
                end_date = today
            else:
                # Default to last 30 days
                start_date = today - timedelta(days=30)
                end_date = today
        else:
            # Use explicit dates
            start_date_str = request.query_params.get('start_date')
            end_date_str = request.query_params.get('end_date')

            if start_date_str:
                start_date = datetime.fromisoformat(start_date_str).date()
            else:
                start_date = timezone.now().date() - timedelta(days=30)

            if end_date_str:
                end_date = datetime.fromisoformat(end_date_str).date()
            else:
                end_date = timezone.now().date()

        return start_date, end_date

    def _get_profit_summary(self, request):
        """Get profit summary with optional monthly trend."""
        start_date, end_date = self._get_date_range(request)

        # Get all completed orders in date range
        completed_orders = Order.objects.filter(
            status='completed',
            payment_confirmed=True,
            delivered_at__date__gte=start_date,
            delivered_at__date__lte=end_date
        ).select_related('vendor', 'courier')

        # Calculate totals
        total_revenue = completed_orders.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        total_delivery_fees = completed_orders.aggregate(
            total=Sum('delivery_fee')
        )['total'] or Decimal('0.00')

        # Platform profit = delivery fees (10% commission calculated from revenue)
        platform_commission_rate = Decimal('0.10')  # 10% commission
        total_platform_commission = total_revenue * platform_commission_rate
        total_profit = total_platform_commission + total_delivery_fees
        total_orders = completed_orders.count()

        # Calculate metrics
        average_profit_per_order = total_profit / total_orders if total_orders > 0 else Decimal('0.00')
        profit_margin_percentage = (total_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0.00')

        # Monthly trend (last 12 months)
        monthly_trend = []
        for i in range(11, -1, -1):
            month_start = timezone.now().date().replace(day=1) - timedelta(days=i*30)
            month_end = month_start.replace(day=28) + timedelta(days=4)  # End of month
            month_end = month_end - timedelta(days=month_end.day)

            month_orders = completed_orders.filter(
                delivered_at__date__gte=month_start,
                delivered_at__date__lte=month_end
            )

            month_revenue = month_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            month_delivery_fees = month_orders.aggregate(total=Sum('delivery_fee'))['total'] or Decimal('0.00')
            month_commission = month_revenue * platform_commission_rate
            month_profit = month_commission + month_delivery_fees

            monthly_trend.append({
                'month': month_start.strftime('%Y-%m'),
                'profit': str(month_profit),
                'orders': month_orders.count()
            })

        return Response({
            'total_profit': str(total_profit),
            'total_revenue': str(total_revenue),
            'total_orders': total_orders,
            'average_profit_per_order': str(average_profit_per_order),
            'profit_margin_percentage': str(profit_margin_percentage.quantize(Decimal('0.01'))),
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'breakdown': {
                'commission_revenue': str(total_platform_commission),
                'delivery_fees': str(total_delivery_fees),
                'other_revenue': '0.00'  # For future expansion
            },
            'monthly_trend': monthly_trend
        })

    def _get_detailed_profit(self, request):
        """Get detailed profit breakdown by order."""
        from django.core.paginator import Paginator

        start_date, end_date = self._get_date_range(request)

        # Get completed orders with profit details
        completed_orders = Order.objects.filter(
            status='completed',
            delivered_at__date__gte=start_date,
            delivered_at__date__lte=end_date
        ).select_related('vendor', 'courier').order_by('-delivered_at')

        # Calculate profit for each order
        order_data = []
        total_profit = Decimal('0.00')
        total_revenue = Decimal('0.00')

        for order in completed_orders:
            # Calculate commission as 10% of order total
            platform_commission_rate = Decimal('0.10')
            commission = order.total_amount * platform_commission_rate
            delivery_fee = order.delivery_fee or Decimal('0.00')
            profit = commission + delivery_fee

            order_data.append({
                'order_id': order.id,
                'order_number': order.order_number or f'#{order.id}',
                'completed_at': order.delivered_at.isoformat() if order.delivered_at else None,
                'total_amount': str(order.total_amount),
                'platform_commission': str(commission),
                'delivery_fee': str(delivery_fee),
                'profit': str(profit)
            })

            total_profit += profit
            total_revenue += order.total_amount

        # Paginate results
        page_size = min(100, int(request.query_params.get('page_size', 20)))
        page = int(request.query_params.get('page', 1))

        paginator = Paginator(order_data, page_size)
        page_obj = paginator.get_page(page)

        return Response({
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'results': list(page_obj),
            'summary': {
                'total_profit': str(total_profit),
                'total_revenue': str(total_revenue),
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                }
            }
        })


class SystemSettingsView(APIView):
    """
    API endpoint for managing system-wide settings including pricing and commission rates.
    Only accessible by admin users.

    ## Permissions
    - User must be authenticated
    - User must be a staff member (is_staff=True)

    ## Endpoints

    ### GET /api/admin/settings/
    Get all system settings or filter by category.

    #### Query Parameters
    - `category` (string, optional): Filter by category ('pricing', 'commission', 'delivery', etc.)
    - `active_only` (boolean, optional): Only return active settings (default: true)

    #### Response (200 OK)
    ```json
    {
        "settings": [
            {
                "key": "platform_commission_rate",
                "value": "0.10",
                "description": "Platform commission rate as decimal (0.10 = 10%)",
                "data_type": "decimal",
                "is_active": true,
                "updated_at": "2023-01-01T12:00:00Z",
                "updated_by": {
                    "id": 1,
                    "email": "admin@example.com"
                }
            },
            {
                "key": "delivery_base_fee",
                "value": "1500.00",
                "description": "Base delivery fee in Naira",
                "data_type": "decimal",
                "is_active": true,
                "updated_at": "2023-01-01T12:00:00Z"
            }
        ]
    }
    ```

    ### POST /api/admin/settings/
    Create or update a system setting.

    #### Request Body
    ```json
    {
        "key": "platform_commission_rate",
        "value": "0.12",
        "description": "Platform commission rate as decimal (0.12 = 12%)",
        "data_type": "decimal"
    }
    ```

    #### Response (200 OK)
    ```json
    {
        "key": "platform_commission_rate",
        "value": "0.12",
        "description": "Platform commission rate as decimal (0.12 = 12%)",
        "data_type": "decimal",
        "is_active": true,
        "updated_at": "2023-01-01T12:00:00Z",
        "updated_by": 1
    }
    ```

    ### GET /api/admin/settings/{key}/
    Get a specific system setting by key.

    #### Response (200 OK)
    ```json
    {
        "key": "platform_commission_rate",
        "value": "0.10",
        "description": "Platform commission rate as decimal (0.10 = 10%)",
        "data_type": "decimal",
        "is_active": true,
        "updated_at": "2023-01-01T12:00:00Z"
    }
    ```

    ### PUT /api/admin/settings/{key}/
    Update a specific system setting.

    #### Request Body
    ```json
    {
        "value": "0.15",
        "description": "Updated commission rate"
    }
    ```

    ### DELETE /api/admin/settings/{key}/
    Deactivate a system setting (soft delete).

    ## Common Settings

    ### Pricing Settings
    - `delivery_base_fee`: Base delivery fee in Naira (default: 1500.00)
    - `delivery_rate_per_km`: Additional fee per kilometer (default: 300.00)
    - `delivery_max_distance_for_base`: Maximum distance for base fee only (default: 5.0 km)

    ### Commission Settings
    - `platform_commission_rate`: Platform commission as decimal (default: 0.10 = 10%)
    - `default_vendor_fixed_amount`: Fixed vendor payout amount (default: 0.00)
    - `default_courier_fixed_amount`: Fixed courier payout amount (default: 500.00)
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request, key=None):
        """Get system settings."""
        if key:
            # Get specific setting
            try:
                setting = SystemSettings.objects.get(key=key)
                return Response({
                    'key': setting.key,
                    'value': setting.value,
                    'description': setting.description,
                    'data_type': setting.data_type,
                    'is_active': setting.is_active,
                    'updated_at': setting.updated_at.isoformat() if setting.updated_at else None,
                    'updated_by': setting.updated_by.id if setting.updated_by else None
                })
            except SystemSettings.DoesNotExist:
                return Response(
                    {'error': f'Setting with key "{key}" not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Get all settings with optional filtering
            queryset = SystemSettings.objects.all()

            category = request.query_params.get('category')
            if category:
                # Filter by category based on key patterns
                if category == 'pricing':
                    queryset = queryset.filter(key__in=[
                        'delivery_base_fee', 'delivery_rate_per_km', 'delivery_max_distance_for_base'
                    ])
                elif category == 'commission':
                    queryset = queryset.filter(key__in=[
                        'platform_commission_rate', 'default_vendor_fixed_amount', 'default_courier_fixed_amount'
                    ])

            active_only = request.query_params.get('active_only', 'true').lower() == 'true'
            if active_only:
                queryset = queryset.filter(is_active=True)

            settings_data = []
            for setting in queryset.order_by('key'):
                setting_data = {
                    'key': setting.key,
                    'value': setting.value,
                    'description': setting.description,
                    'data_type': setting.data_type,
                    'is_active': setting.is_active,
                    'updated_at': setting.updated_at.isoformat() if setting.updated_at else None,
                }
                if setting.updated_by:
                    setting_data['updated_by'] = {
                        'id': setting.updated_by.id,
                        'email': setting.updated_by.email
                    }
                settings_data.append(setting_data)

            return Response({'settings': settings_data})

    def post(self, request, key=None):
        """Create or update a system setting."""
        if key:
            # Update specific setting
            return self._update_setting(request, key)
        else:
            # Create new setting
            setting_data = request.data.copy()
            setting_data['updated_by'] = request.user

            setting = SystemSettings.set_setting(
                key=setting_data['key'],
                value=setting_data['value'],
                description=setting_data.get('description'),
                data_type=setting_data.get('data_type', 'string'),
                user=request.user
            )

            return Response({
                'key': setting.key,
                'value': setting.value,
                'description': setting.description,
                'data_type': setting.data_type,
                'is_active': setting.is_active,
                'updated_at': setting.updated_at.isoformat() if setting.updated_at else None,
                'updated_by': setting.updated_by.id if setting.updated_by else None
            }, status=status.HTTP_201_CREATED)

    def put(self, request, key=None):
        """Update a specific system setting."""
        if not key:
            return Response(
                {'error': 'Setting key is required in URL'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return self._update_setting(request, key)

    def delete(self, request, key=None):
        """Deactivate a system setting (soft delete)."""
        if not key:
            return Response(
                {'error': 'Setting key is required in URL'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            setting = SystemSettings.objects.get(key=key)
            setting.is_active = False
            setting.updated_by = request.user
            setting.save()

            return Response({
                'message': f'Setting "{key}" has been deactivated',
                'key': setting.key,
                'is_active': setting.is_active
            })
        except SystemSettings.DoesNotExist:
            return Response(
                {'error': f'Setting with key "{key}" not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def _update_setting(self, request, key):
        """Helper method to update a setting."""
        try:
            setting = SystemSettings.objects.get(key=key)

            # Update fields
            if 'value' in request.data:
                setting.value = str(request.data['value'])
            if 'description' in request.data:
                setting.description = request.data['description']
            if 'data_type' in request.data:
                setting.data_type = request.data['data_type']

            setting.updated_by = request.user
            setting.save()

            return Response({
                'key': setting.key,
                'value': setting.value,
                'description': setting.description,
                'data_type': setting.data_type,
                'is_active': setting.is_active,
                'updated_at': setting.updated_at.isoformat() if setting.updated_at else None,
                'updated_by': setting.updated_by.id if setting.updated_by else None
            })

        except SystemSettings.DoesNotExist:
            return Response(
                {'error': f'Setting with key "{key}" not found'},
                status=status.HTTP_404_NOT_FOUND
            )
