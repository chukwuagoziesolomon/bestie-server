"""
Verification notification service for sending notifications when vendor/courier verification status changes
"""
import logging
from django.conf import settings
from django.core.mail import send_mail
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from typing import Dict, Optional
from .whatsapp_vendor_service import WhatsAppVendorNotificationService
from .branded_email_service import BrandedEmailService

logger = logging.getLogger(__name__)


class VerificationNotificationService:
    """
    Service for sending verification status change notifications
    """
    
    @staticmethod
    def send_verification_notification(
        user_type: str,  # 'vendor' or 'courier'
        user_profile,
        old_status: str,
        new_status: str,
        admin_notes: Optional[str] = None
    ) -> Dict:
        """
        Send verification status change notification
        
        Args:
            user_type: 'vendor' or 'courier'
            user_profile: VendorProfile or CourierProfile instance
            old_status: Previous verification status
            new_status: New verification status
            admin_notes: Admin notes (for rejections)
            
        Returns:
            Dictionary with notification results
        """
        user = user_profile.user
        
        results = {
            'whatsapp': {'success': False, 'message': ''},
            'websocket': {'success': False, 'message': ''},
            'email': {'success': False, 'message': ''}
        }
        
        # Send WhatsApp notification
        try:
            whatsapp_service = WhatsAppVendorNotificationService()
            user_phone = getattr(user_profile, 'whatsapp_number', None) or getattr(user_profile, 'contact_phone', None) or user.phone
            
            if user_phone:
                whatsapp_result = whatsapp_service.send_verification_notification(
                    user_phone, user_type, user_profile, new_status, admin_notes
                )
                results['whatsapp'] = whatsapp_result
            else:
                results['whatsapp'] = {
                    'success': False,
                    'message': f'{user_type.title()} phone number not available'
                }
        except Exception as e:
            logger.error(f"WhatsApp verification notification failed: {str(e)}")
            results['whatsapp'] = {
                'success': False,
                'message': f'WhatsApp notification failed: {str(e)}'
            }
        
        # Send WebSocket notification
        try:
            websocket_result = VerificationNotificationService._send_websocket_notification(
                user_type, user_profile, new_status, admin_notes
            )
            results['websocket'] = websocket_result
        except Exception as e:
            logger.error(f"WebSocket verification notification failed: {str(e)}")
            results['websocket'] = {
                'success': False,
                'message': f'WebSocket notification failed: {str(e)}'
            }
        
        # Send email notification
        try:
            email_result = VerificationNotificationService._send_email_notification(
                user_type, user_profile, new_status, admin_notes
            )
            results['email'] = email_result
        except Exception as e:
            logger.error(f"Email verification notification failed: {str(e)}")
            results['email'] = {
                'success': False,
                'message': f'Email notification failed: {str(e)}'
            }
        
        return results
    
    @staticmethod
    def _send_websocket_notification(
        user_type: str,
        user_profile,
        new_status: str,
        admin_notes: Optional[str] = None
    ) -> Dict:
        """
        Send WebSocket verification notification
        """
        try:
            # Get channel layer
            channel_layer = get_channel_layer()
            if not channel_layer:
                return {
                    'success': False,
                    'message': 'WebSocket channel layer not available'
                }
            
            # Prepare notification data
            notification_data = {
                'type': 'verification.status_changed',
                'user_type': user_type,
                'status': new_status,
                'business_name': getattr(user_profile, 'business_name', user_profile.user.get_full_name()),
                'admin_notes': admin_notes,
                'timestamp': user_profile.verification_date.isoformat() if hasattr(user_profile, 'verification_date') and user_profile.verification_date else None
            }
            
            # Send to user's WebSocket group
            if user_type == 'vendor':
                group_name = f'vendor_{user_profile.id}'
            else:  # courier
                group_name = f'courier_{user_profile.id}'
            
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'verification_notification',
                    'data': notification_data
                }
            )
            
            return {
                'success': True,
                'message': 'WebSocket verification notification sent successfully'
            }
            
        except Exception as e:
            logger.error(f"WebSocket verification notification error: {str(e)}")
            return {
                'success': False,
                'message': f'WebSocket verification notification failed: {str(e)}'
            }
    
    @staticmethod
    def _send_email_notification(
        user_type: str,
        user_profile,
        new_status: str,
        admin_notes: Optional[str] = None
    ) -> Dict:
        """
        Send branded HTML email verification notification
        """
        try:
            user = user_profile.user
            user_email = user.email

            if not user_email:
                return {
                    'success': False,
                    'message': f'{user_type.title()} email address not available'
                }

            # Create email subject and branded HTML content
            if new_status == 'approved':
                subject = f"Welcome to Bestyy! {user_type.title()} Account Approved"
            elif new_status == 'rejected':
                subject = f"Bestyy {user_type.title()} Application Update"
            else:
                subject = f"Bestyy {user_type.title()} Account Status Update"

            # Create branded HTML email
            html_content = BrandedEmailService.create_verification_email(
                user_type=user_type,
                user_profile=user_profile,
                status=new_status,
                admin_notes=admin_notes
            )

            # Send branded HTML email
            result = BrandedEmailService.send_branded_email(
                subject=subject,
                html_content=html_content,
                recipient_list=[user_email]
            )

            if result['success']:
                logger.info(f"Branded verification email sent to {user_type} {user_profile.id} for status {new_status}")

            return result

        except Exception as e:
            logger.error(f"Branded email verification notification failed: {str(e)}")
            return {
                'success': False,
                'message': f'Email notification failed: {str(e)}'
            }
    
    @staticmethod
    def _create_approval_email_body(user_type: str, user_profile) -> str:
        """Create email body for approval notification"""
        business_name = getattr(user_profile, 'business_name', user_profile.user.get_full_name())
        
        if user_type == 'vendor':
            return f"""
🎉 Congratulations! Your Vendor Account Has Been Approved!

Dear {business_name},

We are excited to inform you that your vendor account has been successfully verified and approved on Bestyy!

✅ *Account Status: APPROVED*
📅 *Approval Date: {user_profile.verification_date.strftime('%B %d, %Y at %I:%M %p') if hasattr(user_profile, 'verification_date') and user_profile.verification_date else 'Recently'}*

🚀 *What's Next?*
- Your restaurant is now live on Bestyy platform
- Customers can now find and order from your establishment
- You can access all vendor dashboard features
- Start receiving orders immediately

📱 *Quick Actions:*
1. Complete your menu setup
2. Upload high-quality food images
3. Set your delivery areas and timing
4. Configure your payment settings

💡 *Pro Tips for Success:*
- Keep your menu updated and accurate
- Respond quickly to customer orders
- Maintain high food quality standards
- Use attractive food photography

📞 *Need Help?*
Our support team is here to assist you. Contact us through:
- Email: support@bestyy.com
- Phone: +234-XXX-XXXX
- In-app chat support

Welcome to the Bestyy family! We're excited to partner with you in delivering amazing food experiences to our customers.

Best regards,
The Bestyy Team

---
This is an automated notification. For support, contact us through the Bestyy platform.
"""
        else:  # courier
            return f"""
🎉 Congratulations! Your Courier Account Has Been Approved!

Dear {user_profile.user.get_full_name()},

We are excited to inform you that your courier account has been successfully verified and approved on Bestyy!

✅ *Account Status: APPROVED*
📅 *Approval Date: {user_profile.verification_date.strftime('%B %d, %Y at %I:%M %p') if hasattr(user_profile, 'verification_date') and user_profile.verification_date else 'Recently'}*

🚀 *What's Next?*
- You can now receive delivery requests
- Access the courier mobile app
- Start earning by delivering orders
- View available delivery opportunities

📱 *Quick Actions:*
1. Download the Bestyy Courier app
2. Complete your profile setup
3. Set your availability schedule
4. Choose your preferred delivery areas

💡 *Pro Tips for Success:*
- Always maintain professional appearance
- Keep your vehicle/delivery method in good condition
- Communicate clearly with customers
- Deliver orders on time and with care

📞 *Need Help?*
Our support team is here to assist you. Contact us through:
- Email: support@bestyy.com
- Phone: +234-XXX-XXXX
- In-app chat support

Welcome to the Bestyy delivery team! We're excited to have you help us deliver amazing food experiences.

Best regards,
The Bestyy Team

---
This is an automated notification. For support, contact us through the Bestyy platform.
"""
    
    @staticmethod
    def _create_rejection_email_body(user_type: str, user_profile, admin_notes: Optional[str] = None) -> str:
        """Create email body for rejection notification"""
        business_name = getattr(user_profile, 'business_name', user_profile.user.get_full_name())
        
        if user_type == 'vendor':
            return f"""
📋 Vendor Account Application Update

Dear {business_name},

Thank you for your interest in joining Bestyy as a vendor partner. After reviewing your application, we regret to inform you that your vendor account application was not approved at this time.

❌ *Account Status: NOT APPROVED*
📅 *Review Date: {user_profile.verification_date.strftime('%B %d, %Y at %I:%M %p') if hasattr(user_profile, 'verification_date') and user_profile.verification_date else 'Recently'}*

📝 *Reason for Rejection:*
{admin_notes or 'Your application did not meet our current verification requirements.'}

🔄 *Next Steps:*
- Review the feedback provided above
- Address any issues mentioned
- Resubmit your application with updated information
- Ensure all required documents are clear and valid

📞 *Need Clarification?*
Our support team is available to help you understand the requirements better:
- Email: support@bestyy.com
- Phone: +234-XXX-XXXX
- In-app chat support

We encourage you to reapply once you have addressed the concerns mentioned above. We look forward to potentially welcoming you to the Bestyy platform in the future.

Best regards,
The Bestyy Team

---
This is an automated notification. For support, contact us through the Bestyy platform.
"""
        else:  # courier
            return f"""
📋 Courier Account Application Update

Dear {user_profile.user.get_full_name()},

Thank you for your interest in joining Bestyy as a delivery courier. After reviewing your application, we regret to inform you that your courier account application was not approved at this time.

❌ *Account Status: NOT APPROVED*
📅 *Review Date: {user_profile.verification_date.strftime('%B %d, %Y at %I:%M %p') if hasattr(user_profile, 'verification_date') and user_profile.verification_date else 'Recently'}*

📝 *Reason for Rejection:*
{admin_notes or 'Your application did not meet our current verification requirements.'}

🔄 *Next Steps:*
- Review the feedback provided above
- Address any issues mentioned
- Resubmit your application with updated information
- Ensure all required documents are clear and valid

📞 *Need Clarification?*
Our support team is available to help you understand the requirements better:
- Email: support@bestyy.com
- Phone: +234-XXX-XXXX
- In-app chat support

We encourage you to reapply once you have addressed the concerns mentioned above. We look forward to potentially welcoming you to the Bestyy delivery team in the future.

Best regards,
The Bestyy Team

---
This is an automated notification. For support, contact us through the Bestyy platform.
"""
    
    @staticmethod
    def _create_status_update_email_body(user_type: str, user_profile, status: str) -> str:
        """Create email body for general status update notification"""
        business_name = getattr(user_profile, 'business_name', user_profile.user.get_full_name())
        
        return f"""
📋 {user_type.title()} Account Status Update

Dear {business_name},

This is to inform you that there has been an update to your {user_type} account status.

📊 *Current Status: {status.upper()}*
📅 *Update Date: {user_profile.verification_date.strftime('%B %d, %Y at %I:%M %p') if hasattr(user_profile, 'verification_date') and user_profile.verification_date else 'Recently'}*

📞 *Need More Information?*
Our support team is available to help:
- Email: support@bestyy.com
- Phone: +234-XXX-XXXX
- In-app chat support

Best regards,
The Bestyy Team

---
This is an automated notification. For support, contact us through the Bestyy platform.
"""






