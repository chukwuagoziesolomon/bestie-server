from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth.decorators import user_passes_test

from .models import VendorProfile
from .serializers import VendorProfileSerializer

class PendingVendorsAdminView(APIView):
    """
    Admin view to list and manage pending vendor verifications
    """
    template_name = 'admin/user/vendor/pending_vendors.html'
    items_per_page = 20
    
    @method_decorator(staff_member_required)
    def get(self, request, *args, **kwargs):
        # Get search query if any
        search_query = request.GET.get('q', '').strip()
        
        # Get page number from query params
        page_number = request.GET.get('page', 1)
        
        # Base queryset - only pending verifications
        queryset = VendorProfile.objects.filter(
            verification_status='pending'
        ).select_related('user').order_by('created_at')
        
        # Apply search if query exists
        if search_query:
            queryset = queryset.filter(
                Q(business_name__icontains=search_query) |
                Q(user__email__icontains=search_query) |
                Q(cac_number__icontains=search_query) |
                Q(business_address__icontains=search_query)
            )
        
        # Paginate the results
        paginator = Paginator(queryset, self.items_per_page)
        page_obj = paginator.get_page(page_number)
        
        # Get serialized data for the current page
        serializer = VendorProfileSerializer(
            page_obj.object_list,
            many=True,
            context={'request': request}
        )
        
        context = {
            'title': 'Pending Vendor Verifications',
            'opts': VendorProfile._meta,
            'has_view_permission': True,
            'search_query': search_query,
            'page_obj': page_obj,
            'paginator': paginator,
            'vendors': serializer.data,
            'total_count': paginator.count,
        }
        
        return render(request, self.template_name, context)

    @method_decorator(staff_member_required)
    def post(self, request, *args, **kwargs):
        """Handle bulk actions for pending vendors"""
        action = request.POST.get('action')
        vendor_ids = request.POST.getlist('_selected_action')
        
        if not action or not vendor_ids:
            return Response(
                {'error': 'No action or vendors selected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        vendors = VendorProfile.objects.filter(
            id__in=vendor_ids,
            verification_status='pending'  # Only allow actions on pending vendors
        )
        
        updated_count = 0
        
        if action == 'approve':
            updated_count = vendors.update(verification_status='approved')
            message = f'Successfully approved {updated_count} vendor(s).'
        elif action == 'reject':
            updated_count = vendors.update(verification_status='rejected')
            message = f'Successfully rejected {updated_count} vendor(s).'
        else:
            return Response(
                {'error': 'Invalid action'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(
            {'message': message, 'count': updated_count},
            status=status.HTTP_200_OK
        )

# Add this to your admin URLs
def get_admin_urls():
    return [
        path(
            'verification/pending-vendors/',
            PendingVendorsAdminView.as_view(),
            name='pending-vendors-verification',
        ),
    ]
