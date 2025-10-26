from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.urls import path
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.core.paginator import Paginator

from .models import CourierProfile
from .serializers import CourierProfileSerializer

class PendingCouriersAdminView(APIView):
    """
    Admin view to list and manage pending courier verifications
    """
    template_name = 'admin/user/courier/pending_couriers.html'
    items_per_page = 20
    
    @method_decorator(staff_member_required)
    def get(self, request, *args, **kwargs):
        # Get search query if any
        search_query = request.GET.get('q', '').strip()
        
        # Get page number from query params
        page_number = request.GET.get('page', 1)
        
        # Base queryset - only pending verifications
        queryset = CourierProfile.objects.filter(
            verification_status='pending'
        ).select_related('user').order_by('created_at')
        
        # Apply search if query exists
        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__email__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(nin_number__icontains=search_query)
            )
        
        # Paginate the results
        paginator = Paginator(queryset, self.items_per_page)
        page_obj = paginator.get_page(page_number)
        
        # Get serialized data for the current page
        serializer = CourierProfileSerializer(
            page_obj.object_list,
            many=True,
            context={'request': request}
        )
        
        context = {
            'title': 'Pending Courier Verifications',
            'opts': CourierProfile._meta,
            'has_view_permission': True,
            'search_query': search_query,
            'page_obj': page_obj,
            'paginator': paginator,
            'couriers': serializer.data,
            'total_count': paginator.count,
        }
        
        return render(request, self.template_name, context)

    @method_decorator(staff_member_required)
    def post(self, request, *args, **kwargs):
        """Handle bulk actions for pending couriers"""
        action = request.POST.get('action')
        courier_ids = request.POST.getlist('_selected_action')
        
        if not action or not courier_ids:
            return Response(
                {'error': 'No action or couriers selected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        couriers = CourierProfile.objects.filter(
            id__in=courier_ids,
            verification_status='pending'  # Only allow actions on pending couriers
        )
        
        updated_count = 0
        
        if action == 'approve':
            updated_count = couriers.update(verification_status='approved')
            message = f'Successfully approved {updated_count} courier(s).'
        elif action == 'reject':
            updated_count = couriers.update(verification_status='rejected')
            message = f'Successfully rejected {updated_count} courier(s).'
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
def get_admin_courier_urls():
    return [
        path(
            'verification/pending-couriers/',
            PendingCouriersAdminView.as_view(),
            name='pending-couriers-verification',
        ),
    ]
