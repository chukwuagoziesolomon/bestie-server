"""
API endpoints for AI capabilities and limitations documentation.
Provides endpoints to view and test AI limitations and capabilities.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from ..ai_service import WhatsAppAIService


class AICapabilitiesOverviewView(APIView):
    """
    API endpoint to get comprehensive AI capabilities and limitations overview.
    GET /api/whatsapp/ai/capabilities/
    """
    permission_classes = [IsAuthenticated]  # Allow authenticated users to view

    def get(self, request):
        """Get AI capabilities and limitations summary"""
        ai_service = WhatsAppAIService()

        try:
            capabilities = ai_service.get_ai_capabilities_summary()

            return Response({
                'success': True,
                'ai_capabilities': capabilities
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIMemoryLimitationsView(APIView):
    """
    API endpoint to demonstrate AI memory limitations.
    GET /api/whatsapp/ai/limitations/memory/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get AI memory limitations details"""
        ai_service = WhatsAppAIService()

        try:
            memory_limitations = ai_service.demonstrate_memory_limitations()

            return Response({
                'success': True,
                'memory_limitations': memory_limitations,
                'description': 'AI has no long-term memory beyond recent conversation messages'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIActionLimitationsView(APIView):
    """
    API endpoint to demonstrate AI action limitations.
    GET /api/whatsapp/ai/limitations/actions/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get AI action limitations details"""
        ai_service = WhatsAppAIService()

        try:
            action_limitations = ai_service.demonstrate_action_limitations()

            return Response({
                'success': True,
                'action_limitations': action_limitations,
                'description': 'AI cannot take direct actions without explicit user confirmation'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AILearningLimitationsView(APIView):
    """
    API endpoint to demonstrate AI learning limitations.
    GET /api/whatsapp/ai/limitations/learning/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get AI learning limitations details"""
        ai_service = WhatsAppAIService()

        try:
            learning_limitations = ai_service.demonstrate_learning_limitations()

            return Response({
                'success': True,
                'learning_limitations': learning_limitations,
                'description': 'AI does not learn or adapt over time without explicit implementation'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIExtensionPointsView(APIView):
    """
    API endpoint to view AI extension points for future enhancements.
    GET /api/whatsapp/ai/extensions/
    """
    permission_classes = [IsAdminUser]  # Admin only for extension planning

    def get(self, request):
        """Get AI extension points for future development"""
        ai_service = WhatsAppAIService()

        try:
            capabilities = ai_service.get_ai_capabilities_summary()
            extensions = capabilities.get('extension_points', {})

            return Response({
                'success': True,
                'extension_points': extensions,
                'implementation_status': {
                    'memory_extension': False,
                    'action_extension': False,
                    'learning_extension': False
                },
                'recommended_priorities': [
                    'Implement long-term conversation memory for better context',
                    'Add intent-based action triggers with confirmation flows',
                    'Implement user feedback collection and response optimization'
                ]
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AITestLimitationsView(APIView):
    """
    API endpoint to test AI limitations (admin only).
    POST /api/whatsapp/ai/test-limitations/
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        """Test various AI limitations"""
        ai_service = WhatsAppAIService()
        test_type = request.data.get('test_type')

        try:
            if test_type == 'memory':
                # Test memory limitations
                result = ai_service.demonstrate_memory_limitations()
                test_result = {
                    'test': 'memory_limitations',
                    'result': result,
                    'expected_behavior': 'Should show short-term memory only'
                }

            elif test_type == 'actions':
                # Test action limitations
                intent = request.data.get('intent', 'place_order')
                result = ai_service.extend_action_capabilities(intent, 'test_user', {})
                test_result = {
                    'test': 'action_limitations',
                    'intent_tested': intent,
                    'result': result,
                    'expected_behavior': 'Should block direct actions'
                }

            elif test_type == 'learning':
                # Test learning limitations
                result = ai_service.extend_learning_capabilities({})
                test_result = {
                    'test': 'learning_limitations',
                    'result': result,
                    'expected_behavior': 'Should return False (not implemented)'
                }

            else:
                return Response({
                    'success': False,
                    'error': 'Invalid test_type. Use: memory, actions, or learning'
                }, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                'success': True,
                'test_result': test_result
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)