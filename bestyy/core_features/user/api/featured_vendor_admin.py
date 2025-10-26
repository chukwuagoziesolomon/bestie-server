"""
Admin API views for managing featured vendors.
These endpoints are protected and only accessible by admin users.
"""
import logging
from datetime import timedelta
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView

from bestyy.core_features.user.models import VendorProfile, SubscriptionPlan
from bestyy.core_features.user.permissions import IsAdminUser

logger = logging.getLogger(__name__)


class FeaturedVendorListView(ListAPIView):
    """
    API endpoint to list and manage featured vendors.
    Only accessible by admin users.

    ## Permissions
    - User must be authenticated
    - User must be a staff member (is_staff=True)

    ## Query Parameters
    - `status` (string, optional): Filter by featured status ('featured', 'expired', 'not_featured')
    - `search` (string, optional): Search in business name or email
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
                "is_featured": true,
                "featured_priority": 5,
                "featured_expiry": "2024-12-31T23:59:59Z",
                "subscription_plan": {
                    "id": 2,
                    "name": "Pro Plan (Featured)",
                    "price": 5000.0,
                    "currency": "NGN"
                },
                "user": {
                    "id": 1,
                    "email": "vendor@example.com"
                },
                "created_at": "2023-01-01T12:00:00Z"
            }
        ]
    }
    ```
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    pagination_class = None

    def get_queryset(self):
        queryset = VendorProfile.objects.filter(
            verification_status='approved',
            is_suspended=False
        ).select_related('user', 'subscription_plan')

        # Filter by featured status
        status_filter = self.request.query_params.get('status', '').strip()
        if status_filter == 'featured':
            queryset = queryset.filter(is_featured=True)
        elif status_filter == 'expired':
            queryset = queryset.filter(
                is_featured=True,
                featured_expiry__lt=timezone.now()
            )
        elif status_filter == 'not_featured':
            queryset = queryset.filter(is_featured=False)

        # Search in business name or email
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(business_name__icontains=search) |
                Q(user__email__icontains=search)
            )

        return queryset.order_by('-is_featured', '-featured_priority', '-created_at')

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


class FeaturedVendorManagementView(APIView):
    """
    API endpoint for managing individual featured vendor status.
    Only accessible by admin users.

    ## Permissions
    - User must be authenticated
    - User must be a staff member (is_staff=True)

    ## Endpoints

    ### GET /api/admin/featured-vendors/{vendor_id}/
    Get detailed information about a vendor's featured status.

    #### Response (200 OK)
    ```json
    {
        "id": 1,
        "business_name": "Vendor Name",
        "is_featured": true,
        "featured_priority": 5,
        "featured_expiry": "2024-12-31T23:59:59Z",
        "subscription_plan": {
            "id": 2,
            "name": "Pro Plan (Featured)",
            "price": 5000.0,
            "currency": "NGN"
        },
        "featured_days_remaining": 45,
        "can_extend_featured": true
    }
    ```

    ### POST /api/admin/featured-vendors/{vendor_id}/feature/
    Make a vendor featured (upgrade to Pro plan).

    #### Request Body
    ```json
    {
        "duration_days": 30,
        "priority": 5
    }
    ```

    #### Response (200 OK)
    ```json
    {
        "success": true,
        "message": "Vendor Vendor Name is now featured",
        "vendor": {
            "id": 1,
            "business_name": "Vendor Name",
            "is_featured": true,
            "featured_priority": 5,
            "featured_expiry": "2024-11-01T10:00:00Z"
        }
    }
    ```

    ### POST /api/admin/featured-vendors/{vendor_id}/unfeature/
    Remove featured status from a vendor.

    #### Response (200 OK)
    ```json
    {
        "success": true,
        "message": "Vendor Vendor Name is no longer featured",
        "vendor": {
            "id": 1,
            "business_name": "Vendor Name",
            "is_featured": false
        }
    }
    ```

    ### POST /api/admin/featured-vendors/{vendor_id}/extend/
    Extend featured status for a vendor.

    #### Request Body
    ```json
    {
        "additional_days": 30
    }
    ```

    #### Response (200 OK)
    ```json
    {
        "success": true,
        "message": "Featured status extended by 30 days",
        "vendor": {
            "id": 1,
            "business_name": "Vendor Name",
            "featured_expiry": "2024-12-01T10:00:00Z"
        }
    }
    ```
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request, vendor_id):
        """Get vendor featured status details."""
        vendor = get_object_or_404(VendorProfile, id=vendor_id)

        # Calculate days remaining if featured
        days_remaining = None
        can_extend = False
        if vendor.is_featured and vendor.featured_expiry:
            if vendor.featured_expiry > timezone.now():
                delta = vendor.featured_expiry - timezone.now()
                days_remaining = delta.days
                can_extend = True
            else:
                days_remaining = 0

        response_data = {
            'id': vendor.id,
            'business_name': vendor.business_name,
            'is_featured': vendor.is_featured,
            'featured_priority': vendor.featured_priority,
            'featured_expiry': vendor.featured_expiry.isoformat() if vendor.featured_expiry else None,
            'subscription_plan': {
                'id': vendor.subscription_plan.id if vendor.subscription_plan else None,
                'name': vendor.subscription_plan.name if vendor.subscription_plan else None,
                'price': float(vendor.subscription_plan.price) if vendor.subscription_plan else None,
                'currency': vendor.subscription_plan.currency if vendor.subscription_plan else None,
            } if vendor.subscription_plan else None,
            'featured_days_remaining': days_remaining,
            'can_extend_featured': can_extend,
            'user': {
                'id': vendor.user.id,
                'email': vendor.user.email,
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request, vendor_id):
        """Handle featured vendor management actions."""
        vendor = get_object_or_404(VendorProfile, id=vendor_id)

        if request.path.endswith('/feature/'):
            return self._make_featured(request, vendor)
        elif request.path.endswith('/unfeature/'):
            return self._remove_featured(vendor)
        elif request.path.endswith('/extend/'):
            return self._extend_featured(request, vendor)
        else:
            return Response(
                {"detail": "Invalid endpoint. Use /feature/, /unfeature/, or /extend/."},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _make_featured(self, request, vendor):
        """Make a vendor featured."""
        duration_days = int(request.data.get('duration_days', 30))
        priority = int(request.data.get('priority', 1))

        # Validate duration
        if duration_days < 1 or duration_days > 365:
            return Response(
                {"detail": "Duration must be between 1 and 365 days."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate priority
        if priority < 1 or priority > 100:
            return Response(
                {"detail": "Priority must be between 1 and 100."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create Pro subscription plan
        pro_plan, created = SubscriptionPlan.objects.get_or_create(
            plan_type='pro',
            defaults={
                'name': 'Pro Plan (Featured)',
                'price': 5000.00,
                'currency': 'NGN',
                'duration_days': duration_days,
                'is_active': True
            }
        )

        # Update vendor
        now = timezone.now()
        vendor.is_featured = True
        vendor.featured_priority = priority
        vendor.featured_expiry = now + timedelta(days=duration_days)
        vendor.subscription_plan = pro_plan
        vendor.save()

        logger.info(f"Vendor {vendor.id} ({vendor.business_name}) made featured by {request.user.email}")

        return Response({
            'success': True,
            'message': f'Vendor {vendor.business_name} is now featured',
            'vendor': {
                'id': vendor.id,
                'business_name': vendor.business_name,
                'is_featured': vendor.is_featured,
                'featured_priority': vendor.featured_priority,
                'featured_expiry': vendor.featured_expiry.isoformat(),
                'subscription_plan': {
                    'id': pro_plan.id,
                    'name': pro_plan.name,
                    'price': float(pro_plan.price),
                    'currency': pro_plan.currency,
                }
            }
        }, status=status.HTTP_200_OK)

    def _remove_featured(self, vendor):
        """Remove featured status from vendor."""
        vendor.is_featured = False
        vendor.featured_priority = 0
        vendor.featured_expiry = None
        vendor.save()

        logger.info(f"Vendor {vendor.id} ({vendor.business_name}) removed from featured")

        return Response({
            'success': True,
            'message': f'Vendor {vendor.business_name} is no longer featured',
            'vendor': {
                'id': vendor.id,
                'business_name': vendor.business_name,
                'is_featured': vendor.is_featured,
            }
        }, status=status.HTTP_200_OK)

    def _extend_featured(self, request, vendor):
        """Extend featured status for vendor."""
        if not vendor.is_featured:
            return Response(
                {"detail": "Vendor is not currently featured."},
                status=status.HTTP_400_BAD_REQUEST
            )

        additional_days = int(request.data.get('additional_days', 30))

        if additional_days < 1 or additional_days > 365:
            return Response(
                {"detail": "Additional days must be between 1 and 365."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extend expiry date
        if vendor.featured_expiry:
            vendor.featured_expiry = vendor.featured_expiry + timedelta(days=additional_days)
        else:
            vendor.featured_expiry = timezone.now() + timedelta(days=additional_days)

        vendor.save()

        logger.info(f"Vendor {vendor.id} ({vendor.business_name}) featured status extended by {additional_days} days")

        return Response({
            'success': True,
            'message': f'Featured status extended by {additional_days} days',
            'vendor': {
                'id': vendor.id,
                'business_name': vendor.business_name,
                'featured_expiry': vendor.featured_expiry.isoformat(),
            }
        }, status=status.HTTP_200_OK)


class FeaturedVendorStatsView(APIView):
    """
    API endpoint to get featured vendor statistics for admin dashboard.
    Only accessible by admin users.

    ## Permissions
    - User must be authenticated
    - User must be a staff member (is_staff=True)

    ## Response Format

    ```json
    {
        "total_featured_vendors": 15,
        "active_featured_vendors": 12,
        "expired_featured_vendors": 3,
        "featured_this_month": 5,
        "expiring_soon": [
            {
                "id": 1,
                "business_name": "Vendor Name",
                "featured_expiry": "2024-10-15T23:59:59Z",
                "days_remaining": 3
            }
        ],
        "subscription_plan_stats": {
            "free": 85,
            "pro": 15
        }
    }
    ```
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        """Get featured vendor statistics."""
        now = timezone.now()
        seven_days_from_now = now + timedelta(days=7)
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Basic counts
        total_featured = VendorProfile.objects.filter(is_featured=True).count()
        active_featured = VendorProfile.objects.filter(
            is_featured=True,
            featured_expiry__gt=now
        ).count()
        expired_featured = VendorProfile.objects.filter(
            is_featured=True,
            featured_expiry__lte=now
        ).count()

        # New featured this month
        featured_this_month = VendorProfile.objects.filter(
            is_featured=True,
            updated_at__gte=this_month_start
        ).count()

        # Expiring soon (next 7 days)
        expiring_soon = VendorProfile.objects.filter(
            is_featured=True,
            featured_expiry__gt=now,
            featured_expiry__lte=seven_days_from_now
        ).order_by('featured_expiry')[:10]

        expiring_data = []
        for vendor in expiring_soon:
            days_remaining = (vendor.featured_expiry - now).days
            expiring_data.append({
                'id': vendor.id,
                'business_name': vendor.business_name,
                'featured_expiry': vendor.featured_expiry.isoformat(),
                'days_remaining': days_remaining,
                'user': {
                    'id': vendor.user.id,
                    'email': vendor.user.email,
                }
            })

        # Subscription plan stats
        plan_stats = dict(
            VendorProfile.objects.values('subscription_plan__plan_type')
            .annotate(count=Count('id'))
            .filter(subscription_plan__isnull=False)
            .order_by()
        )

        # Ensure all plan types are included
        for plan_type in ['free', 'pro']:
            plan_stats[plan_type] = plan_stats.get(plan_type, 0)

        return Response({
            'total_featured_vendors': total_featured,
            'active_featured_vendors': active_featured,
            'expired_featured_vendors': expired_featured,
            'featured_this_month': featured_this_month,
            'expiring_soon': expiring_data,
            'subscription_plan_stats': plan_stats,
        }, status=status.HTTP_200_OK)