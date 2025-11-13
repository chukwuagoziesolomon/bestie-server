"""
Admin API views for managing subscription plans
"""
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from django.shortcuts import get_object_or_404

from bestyy.core_features.user.models import SubscriptionPlan
from bestyy.core_features.user.permissions import IsAdminUser


class AdminSubscriptionPlanListView(ListAPIView):
    """
    Admin view to list all subscription plans (active and inactive)
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    queryset = SubscriptionPlan.objects.all()
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
                'is_active': plan.is_active,
                'created_at': plan.created_at.isoformat(),
                'updated_at': plan.updated_at.isoformat()
            })

        return Response({
            'count': len(plans_data),
            'results': plans_data
        })


class AdminSubscriptionPlanDetailView(APIView):
    """
    Admin view to create, update, and delete subscription plans
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request, plan_id):
        """Get a specific subscription plan"""
        plan = get_object_or_404(SubscriptionPlan, id=plan_id)

        return Response({
            'id': plan.id,
            'name': plan.name,
            'plan_type': plan.plan_type,
            'interval': plan.interval,
            'price': float(plan.price),
            'currency': plan.currency,
            'description': plan.description,
            'features': plan.features,
            'duration_days': plan.duration_days,
            'is_active': plan.is_active,
            'created_at': plan.created_at.isoformat(),
            'updated_at': plan.updated_at.isoformat()
        })

    def post(self, request):
        """Create a new subscription plan"""
        data = request.data

        # Validate required fields
        required_fields = ['name', 'plan_type', 'interval', 'price']
        for field in required_fields:
            if field not in data:
                return Response(
                    {"detail": f"{field} is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Check for duplicate plan_type + interval combination
        if SubscriptionPlan.objects.filter(
            plan_type=data['plan_type'],
            interval=data['interval']
        ).exists():
            return Response(
                {"detail": f"A {data['plan_type']} plan with {data['interval']} interval already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        plan = SubscriptionPlan.objects.create(
            name=data['name'],
            plan_type=data['plan_type'],
            interval=data['interval'],
            price=data['price'],
            currency=data.get('currency', 'NGN'),
            description=data.get('description', ''),
            features=data.get('features', []),
            duration_days=data.get('duration_days', 30),
            is_active=data.get('is_active', True)
        )

        return Response({
            'success': True,
            'message': 'Subscription plan created successfully',
            'plan': {
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
            }
        }, status=status.HTTP_201_CREATED)

    def put(self, request, plan_id):
        """Update an existing subscription plan"""
        plan = get_object_or_404(SubscriptionPlan, id=plan_id)
        data = request.data

        # Check for duplicate plan_type + interval combination (excluding current plan)
        if SubscriptionPlan.objects.filter(
            plan_type=data.get('plan_type', plan.plan_type),
            interval=data.get('interval', plan.interval)
        ).exclude(id=plan_id).exists():
            return Response(
                {"detail": f"A {data.get('plan_type', plan.plan_type)} plan with {data.get('interval', plan.interval)} interval already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update fields
        plan.name = data.get('name', plan.name)
        plan.plan_type = data.get('plan_type', plan.plan_type)
        plan.interval = data.get('interval', plan.interval)
        plan.price = data.get('price', plan.price)
        plan.currency = data.get('currency', plan.currency)
        plan.description = data.get('description', plan.description)
        plan.features = data.get('features', plan.features)
        plan.duration_days = data.get('duration_days', plan.duration_days)
        plan.is_active = data.get('is_active', plan.is_active)
        plan.save()

        return Response({
            'success': True,
            'message': 'Subscription plan updated successfully',
            'plan': {
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
            }
        })

    def delete(self, request, plan_id):
        """Delete a subscription plan"""
        plan = get_object_or_404(SubscriptionPlan, id=plan_id)

        # Check if plan has active subscriptions
        if plan.subscriptions.filter(status__in=['active', 'non-renewing']).exists():
            return Response(
                {"detail": "Cannot delete plan with active subscriptions"},
                status=status.HTTP_400_BAD_REQUEST
            )

        plan.delete()

        return Response({
            'success': True,
            'message': 'Subscription plan deleted successfully'
        })


class AdminSubscriptionPlanBulkUpdateView(APIView):
    """
    Admin view to bulk update subscription plans (activate/deactivate)
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def post(self, request):
        """Bulk update plan statuses"""
        data = request.data

        plan_ids = data.get('plan_ids', [])
        action = data.get('action')  # 'activate' or 'deactivate'

        if not plan_ids or action not in ['activate', 'deactivate']:
            return Response(
                {"detail": "plan_ids (list) and action ('activate' or 'deactivate') are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        plans = SubscriptionPlan.objects.filter(id__in=plan_ids)
        updated_count = plans.update(is_active=(action == 'activate'))

        return Response({
            'success': True,
            'message': f'{updated_count} plans {action}d successfully',
            'updated_count': updated_count
        })