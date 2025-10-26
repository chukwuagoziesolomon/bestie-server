"""
API endpoint for testing and managing personalized recommendations.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from django.shortcuts import get_object_or_404
from bestyy.core_features.user.models import User
from bestyy.core_features.user.services.personalized_recommendation_service import PersonalizedRecommendationService


class PersonalizedRecommendationPreviewView(APIView):
    """
    API endpoint to preview personalized recommendations for users.
    GET /api/user/recommendations/preview/<user_id>/
    """
    permission_classes = [IsAdminUser]  # Only admins can preview

    def get(self, request, user_id):
        """Get recommendation preview for a specific user"""
        try:
            preview = PersonalizedRecommendationService.get_recommendation_preview(user_id)

            if not preview:
                return Response({
                    'success': False,
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)

            return Response({
                'success': True,
                'preview': preview
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SendPersonalizedRecommendationView(APIView):
    """
    API endpoint to manually send personalized recommendation to a user.
    POST /api/user/recommendations/send/<user_id>/
    """
    permission_classes = [IsAdminUser]  # Only admins can send

    def post(self, request, user_id):
        """Send personalized recommendation to a specific user"""
        try:
            user = get_object_or_404(User, id=user_id)

            # Analyze user and send recommendation
            PersonalizedRecommendationService._send_personalized_recommendation(user)

            return Response({
                'success': True,
                'message': f'Personalized recommendation sent to {user.email}'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BulkRecommendationStatsView(APIView):
    """
    API endpoint to get statistics about personalized recommendations.
    GET /api/user/recommendations/stats/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get recommendation statistics"""
        try:
            # Get eligible users count
            eligible_users = PersonalizedRecommendationService._get_eligible_users()

            # Get sample insights for a few users
            sample_insights = []
            for user in eligible_users[:5]:  # Show insights for first 5 users
                insights = PersonalizedRecommendationService._analyze_user_behavior(user)
                sample_insights.append({
                    'user_id': user.id,
                    'user_email': user.email,
                    'insights': insights
                })

            return Response({
                'success': True,
                'stats': {
                    'eligible_users_count': len(eligible_users),
                    'sample_user_insights': sample_insights
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)