"""
Courier verification status API endpoints
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import Http404

from bestyy.core_features.user.models import CourierProfile


class CourierVerificationStatusView(APIView):
    """
    Endpoint for couriers to check their verification status.
    
    GET /api/user/couriers/verification-status/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """Get courier verification status"""
        try:
            courier_profile = request.user.courier_profile
            
            return Response({
                'success': True,
                'data': {
                    'courier_id': courier_profile.id,
                    'user_id': request.user.id,
                    'full_name': request.user.get_full_name(),
                    'email': request.user.email,
                    'phone': request.user.phone,
                    'verification_status': courier_profile.verification_status,
                    'verified': courier_profile.verification_status == 'approved',
                    'verification_date': courier_profile.verification_date.isoformat() if courier_profile.verification_date else None,
                    'verification_notes': getattr(courier_profile, 'verification_notes', None),
                    'verification_preference': getattr(courier_profile, 'verification_preference', 'NIN'),
                    'message': self._get_status_message(courier_profile.verification_status),
                    'next_steps': self._get_next_steps(courier_profile.verification_status),
                    'required_documents': self._get_required_documents(),
                    'support_contact': {
                        'email': 'support@bestyy.com',
                        'phone': '+234-XXX-XXXX',
                        'whatsapp': '+234-XXX-XXXX'
                    }
                }
            })
            
        except CourierProfile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'No courier profile found for this user. Please complete your courier registration first.'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def _get_status_message(self, status):
        """Get user-friendly status message"""
        messages = {
            'pending': 'Your courier application is under review. We will notify you once the review is complete.',
            'approved': 'Congratulations! Your courier account has been approved and verified.',
            'rejected': 'Your courier application was not approved. Please check the notes below for details.',
            'suspended': 'Your courier account has been temporarily suspended. Contact support for assistance.',
            'incomplete': 'Your courier application is incomplete. Please provide all required information.',
        }
        return messages.get(status, 'Unknown status')
    
    def _get_next_steps(self, status):
        """Get next steps based on verification status"""
        if status == 'pending':
            return [
                'Wait for review completion (usually within 24-48 hours)',
                'Ensure all documents are clear and valid',
                'Check your email and phone for updates'
            ]
        elif status == 'approved':
            return [
                'Download the Bestyy Courier mobile app',
                'Complete your profile setup',
                'Set your availability schedule',
                'Start accepting delivery requests'
            ]
        elif status == 'rejected':
            return [
                'Review the rejection reason below',
                'Address any issues mentioned',
                'Update your application with correct information',
                'Resubmit your application'
            ]
        elif status == 'incomplete':
            return [
                'Complete all required fields in your application',
                'Upload all required documents',
                'Verify your contact information',
                'Submit your completed application'
            ]
        else:
            return ['Contact support for assistance']
    
    def _get_required_documents(self):
        """Get list of required verification documents"""
        return [
            {
                'name': 'Government-issued ID',
                'type': 'NIN, Driver\'s License, or International Passport',
                'required': True,
                'description': 'Clear photo of your valid government-issued identification'
            },
            {
                'name': 'Proof of Address',
                'type': 'Utility Bill or Bank Statement',
                'required': True,
                'description': 'Recent utility bill or bank statement (not older than 3 months)'
            },
            {
                'name': 'Vehicle Registration',
                'type': 'Vehicle Documents',
                'required': True,
                'description': 'Valid vehicle registration documents if using a vehicle'
            },
            {
                'name': 'Driver\'s License',
                'type': 'Valid Driver\'s License',
                'required': True,
                'description': 'Valid driver\'s license if using a vehicle for delivery'
            },
            {
                'name': 'Profile Photo',
                'type': 'Clear Headshot',
                'required': True,
                'description': 'Clear, professional headshot photo'
            }
        ]


class CourierVerificationHistoryView(APIView):
    """
    Endpoint for couriers to view their verification history and timeline.
    
    GET /api/user/couriers/verification-history/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """Get courier verification history"""
        try:
            courier_profile = request.user.courier_profile
            
            # Create verification timeline
            timeline = []
            
            # Application submission
            timeline.append({
                'date': courier_profile.created_at.isoformat(),
                'status': 'submitted',
                'title': 'Application Submitted',
                'description': 'Your courier application was submitted for review',
                'icon': '📋'
            })
            
            # Verification status updates
            if courier_profile.verification_date:
                timeline.append({
                    'date': courier_profile.verification_date.isoformat(),
                    'status': courier_profile.verification_status,
                    'title': f'Application {courier_profile.verification_status.title()}',
                    'description': self._get_timeline_description(courier_profile.verification_status, courier_profile),
                    'icon': self._get_status_icon(courier_profile.verification_status)
                })
            
            # If still pending, add estimated review time
            if courier_profile.verification_status == 'pending':
                timeline.append({
                    'date': None,
                    'status': 'estimated',
                    'title': 'Estimated Review Completion',
                    'description': 'Your application will be reviewed within 24-48 hours',
                    'icon': '⏰'
                })
            
            return Response({
                'success': True,
                'data': {
                    'courier_id': courier_profile.id,
                    'current_status': courier_profile.verification_status,
                    'application_date': courier_profile.created_at.isoformat(),
                    'verification_date': courier_profile.verification_date.isoformat() if courier_profile.verification_date else None,
                    'timeline': timeline,
                    'verification_notes': getattr(courier_profile, 'verification_notes', None),
                    'estimated_review_time': '24-48 hours' if courier_profile.verification_status == 'pending' else None
                }
            })
            
        except CourierProfile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'No courier profile found for this user'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def _get_timeline_description(self, status, courier_profile):
        """Get timeline description based on status"""
        if status == 'approved':
            return 'Your courier account has been verified and approved. You can now start accepting delivery requests.'
        elif status == 'rejected':
            notes = getattr(courier_profile, 'verification_notes', 'No specific reason provided')
            return f'Your application was not approved. Reason: {notes}'
        elif status == 'pending':
            return 'Your application is currently being reviewed by our verification team.'
        else:
            return f'Application status updated to {status}'
    
    def _get_status_icon(self, status):
        """Get status icon for timeline"""
        icons = {
            'approved': '✅',
            'rejected': '❌',
            'pending': '⏳',
            'suspended': '⏸️',
            'incomplete': '📝'
        }
        return icons.get(status, '📋')






