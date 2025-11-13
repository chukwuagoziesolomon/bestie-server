"""
API views for managing vendor subscriptions using Paystack
"""
import logging
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView

from bestyy.core_features.user.models import VendorProfile, SubscriptionPlan, VendorSubscription
from bestyy.core_features.user.services.paystack_service import PaystackService
from bestyy.core_features.user.permissions import IsAdminUser

logger = logging.getLogger(__name__)


class SubscriptionPlanListView(ListAPIView):
    """
    API endpoint to list active subscription plans.
    """
    permission_classes = [permissions.IsAuthenticated]
    queryset = SubscriptionPlan.get_active_plans()
    serializer_class = None  # We'll use custom serialization

    def list(self, request, *args, **kwargs):
        plans = self.get_queryset()
        plans_data = []

        for plan in plans:
            plans_data.append({
                'id': plan.id,
                'name': plan.name,
                'plan_type': plan.plan_type,
                'interval': plan.interval,
                'price': float(plan.price),
                'currency': plan.currency,
                'description': plan.description,
                'features': plan.features,
                'duration_days': plan.duration_days,
                'is_active': plan.is_active
            })

        return Response({
            'count': len(plans_data),
            'results': plans_data
        })


class VendorSubscriptionView(APIView):
    """
    API endpoint for vendor subscription management.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get current vendor subscription status"""
        try:
            vendor = request.user.vendor_profile
        except VendorProfile.DoesNotExist:
            return Response(
                {"detail": "User is not a vendor"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            subscription = vendor.subscription
            subscription_data = {
                'subscription_code': subscription.paystack_subscription_code,
                'plan': {
                    'id': subscription.plan.id,
                    'name': subscription.plan.name,
                    'plan_type': subscription.plan.plan_type,
                    'price': float(subscription.plan.price),
                    'currency': subscription.plan.currency
                },
                'status': subscription.status,
                'next_payment_date': subscription.next_payment_date.isoformat() if subscription.next_payment_date else None,
                'start_date': subscription.start_date.isoformat(),
                'is_featured_active': subscription.is_featured_active
            }
        except VendorSubscription.DoesNotExist:
            subscription_data = None

        return Response({
            'vendor_id': vendor.id,
            'business_name': vendor.business_name,
            'subscription': subscription_data
        })

    def post(self, request):
        """Create or update vendor subscription"""
        try:
            vendor = request.user.vendor_profile
        except VendorProfile.DoesNotExist:
            return Response(
                {"detail": "User is not a vendor"},
                status=status.HTTP_400_BAD_REQUEST
            )

        plan_id = request.data.get('plan_id')
        if not plan_id:
            return Response(
                {"detail": "plan_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {"detail": "Invalid plan"},
                status=status.HTTP_400_BAD_REQUEST
            )

        paystack_service = PaystackService()

        # Check if vendor already has a subscription
        try:
            existing_subscription = vendor.subscription
            # Cancel existing subscription first
            cancel_result = paystack_service.disable_subscription(
                existing_subscription.paystack_subscription_code
            )
            if not cancel_result['success']:
                logger.warning(f"Failed to cancel existing subscription: {cancel_result.get('error')}")
            existing_subscription.cancel_subscription()
        except VendorSubscription.DoesNotExist:
            pass

        # Create new subscription on Paystack
        customer_result = paystack_service.create_customer(request.user)
        if not customer_result['success']:
            return Response(
                {"detail": f"Failed to create Paystack customer: {customer_result.get('error')}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        customer_code = customer_result['customer_id']

        # Create plan on Paystack if it doesn't exist
        plan_result = paystack_service.create_plan(
            name=plan.name,
            interval=plan.get_paystack_interval(),
            amount=int(plan.price * 100),  # Convert to kobo
            description=plan.description
        )

        if not plan_result['success']:
            return Response(
                {"detail": f"Failed to create Paystack plan: {plan_result.get('error')}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        plan_code = plan_result['plan_code']

        # Initialize subscription transaction
        transaction_result = paystack_service.initialize_subscription_transaction(
            email=request.user.email,
            plan_code=plan_code,
            amount=int(plan.price * 100)
        )

        if not transaction_result['success']:
            return Response(
                {"detail": f"Failed to initialize subscription: {transaction_result.get('error')}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'success': True,
            'message': 'Subscription initialized successfully',
            'authorization_url': transaction_result['authorization_url'],
            'plan': {
                'id': plan.id,
                'name': plan.name,
                'price': float(plan.price),
                'currency': plan.currency
            }
        })


class AdminSubscriptionManagementView(APIView):
    """
    Admin API endpoint for managing vendor subscriptions.
    Only accessible by admin users.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def post(self, request, vendor_id):
        """Admin actions: create, cancel, or modify subscriptions"""
        vendor = get_object_or_404(VendorProfile, id=vendor_id)

        action = request.data.get('action')
        if not action:
            return Response(
                {"detail": "action is required (create, cancel, modify)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        paystack_service = PaystackService()

        if action == 'create':
            return self._create_subscription(request, vendor, paystack_service)
        elif action == 'cancel':
            return self._cancel_subscription(vendor, paystack_service)
        elif action == 'modify':
            return self._modify_subscription(request, vendor, paystack_service)
        else:
            return Response(
                {"detail": "Invalid action. Use: create, cancel, modify"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _create_subscription(self, request, vendor, paystack_service):
        """Admin: Create subscription for vendor"""
        plan_id = request.data.get('plan_id')
        if not plan_id:
            return Response(
                {"detail": "plan_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {"detail": "Invalid plan"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create customer on Paystack
        customer_result = paystack_service.create_customer(vendor.user)
        if not customer_result['success']:
            return Response(
                {"detail": f"Failed to create customer: {customer_result.get('error')}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        customer_code = customer_result['customer_id']

        # Create subscription directly (admin bypasses payment)
        subscription_result = paystack_service.create_subscription(
            customer_code=customer_code,
            plan_code=f"PLN_{plan.id}"  # Assuming plan codes follow this pattern
        )

        if not subscription_result['success']:
            return Response(
                {"detail": f"Failed to create subscription: {subscription_result.get('error')}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create local subscription record
        subscription_data = subscription_result['subscription_data']
        subscription, created = VendorSubscription.objects.update_or_create(
            vendor=vendor,
            defaults={
                'plan': plan,
                'paystack_subscription_code': subscription_data.get('subscription_code'),
                'paystack_customer_code': customer_code,
                'paystack_email_token': subscription_data.get('email_token'),
                'status': 'active',
                'next_payment_date': subscription_data.get('next_payment_date'),
                'invoice_limit': subscription_data.get('invoice_limit')
            }
        )

        # Update vendor featured status
        vendor.is_featured = True
        vendor.featured_priority = 1
        vendor.featured_expiry = None  # Managed by subscription now
        vendor.save()

        return Response({
            'success': True,
            'message': f'Subscription created for {vendor.business_name}',
            'subscription': {
                'code': subscription.paystack_subscription_code,
                'status': subscription.status,
                'plan': plan.name
            }
        })

    def _cancel_subscription(self, vendor, paystack_service):
        """Admin: Cancel vendor subscription"""
        try:
            subscription = vendor.subscription
        except VendorSubscription.DoesNotExist:
            return Response(
                {"detail": "Vendor has no active subscription"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cancel on Paystack
        cancel_result = paystack_service.disable_subscription(
            subscription.paystack_subscription_code
        )

        if not cancel_result['success']:
            return Response(
                {"detail": f"Failed to cancel Paystack subscription: {cancel_result.get('error')}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update local record
        subscription.cancel_subscription()

        # Remove featured status
        vendor.is_featured = False
        vendor.featured_priority = 0
        vendor.featured_expiry = None
        vendor.save()

        return Response({
            'success': True,
            'message': f'Subscription cancelled for {vendor.business_name}'
        })

    def _modify_subscription(self, request, vendor, paystack_service):
        """Admin: Modify vendor subscription (change plan)"""
        new_plan_id = request.data.get('new_plan_id')
        if not new_plan_id:
            return Response(
                {"detail": "new_plan_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            new_plan = SubscriptionPlan.objects.get(id=new_plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {"detail": "Invalid new plan"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            subscription = vendor.subscription
        except VendorSubscription.DoesNotExist:
            return Response(
                {"detail": "Vendor has no active subscription"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cancel current subscription
        cancel_result = paystack_service.disable_subscription(
            subscription.paystack_subscription_code
        )

        if not cancel_result['success']:
            return Response(
                {"detail": f"Failed to cancel current subscription: {cancel_result.get('error')}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create new subscription with new plan
        subscription_result = paystack_service.create_subscription(
            customer_code=subscription.paystack_customer_code,
            plan_code=f"PLN_{new_plan.id}"
        )

        if not subscription_result['success']:
            return Response(
                {"detail": f"Failed to create new subscription: {subscription_result.get('error')}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update local record
        subscription_data = subscription_result['subscription_data']
        subscription.plan = new_plan
        subscription.paystack_subscription_code = subscription_data.get('subscription_code')
        subscription.paystack_email_token = subscription_data.get('email_token')
        subscription.next_payment_date = subscription_data.get('next_payment_date')
        subscription.invoice_limit = subscription_data.get('invoice_limit')
        subscription.save()

        return Response({
            'success': True,
            'message': f'Subscription updated for {vendor.business_name}',
            'new_plan': new_plan.name
        })