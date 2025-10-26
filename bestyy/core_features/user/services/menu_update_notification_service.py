"""
Service to notify vendors when they need to update their menu items.
This service checks for vendors whose menus haven't been updated in 2 days
and sends notifications via webhook, WhatsApp, and email.
"""
from django.utils import timezone
from django.db.models import F
from datetime import timedelta
from user.models import VendorProfile
import logging

logger = logging.getLogger(__name__)


class MenuUpdateNotificationService:
    """
    Service to handle menu update notifications for vendors.
    """

    @staticmethod
    def check_and_notify_stale_menus():
        """
        Check for vendors whose menus haven't been updated in 2 days
        and send notifications.
        """
        two_days_ago = timezone.now() - timedelta(days=2)

        # Find vendors with stale menus
        stale_vendors = VendorProfile.objects.filter(
            verification_status='approved',
            is_suspended=False,
            last_menu_update__lt=two_days_ago
        ).select_related('user')

        notified_count = 0
        for vendor in stale_vendors:
            try:
                MenuUpdateNotificationService._notify_vendor_menu_update(vendor)
                notified_count += 1
            except Exception as e:
                logger.error(f"Failed to notify vendor {vendor.id} about menu update: {str(e)}")
                continue

        return notified_count

    @staticmethod
    def _notify_vendor_menu_update(vendor: VendorProfile):
        """
        Send menu update notification to a vendor via multiple channels.
        """
        user = vendor.user
        message = MenuUpdateNotificationService._build_menu_update_message(vendor)

        # Send WhatsApp notification
        try:
            MenuUpdateNotificationService._send_whatsapp_notification(user, message)
        except Exception as e:
            logger.error(f"WhatsApp notification failed for vendor {vendor.id}: {str(e)}")

        # Send email notification
        try:
            MenuUpdateNotificationService._send_email_notification(user, message)
        except Exception as e:
            logger.error(f"Email notification failed for vendor {vendor.id}: {str(e)}")

        # Send webhook notification (if configured)
        try:
            MenuUpdateNotificationService._send_webhook_notification(vendor, message)
        except Exception as e:
            logger.error(f"Webhook notification failed for vendor {vendor.id}: {str(e)}")

    @staticmethod
    def _build_menu_update_message(vendor: VendorProfile) -> str:
        """
        Build the menu update notification message.
        """
        days_since_update = MenuUpdateNotificationService._days_since_menu_update(vendor)

        message = f"""
🔔 Menu Update Required - {vendor.business_name}

Your menu hasn't been updated in {days_since_update} days. To keep appearing in recommendations:

✅ Update your menu items
✅ Add new dishes or specials
✅ Update prices if needed
✅ Mark items as available/unavailable

Action Required: Update your menu within 24 hours to avoid being hidden from customer recommendations.

Update now: [Your Vendor Dashboard Link]

Bestyy Team
        """.strip()

        return message

    @staticmethod
    def _days_since_menu_update(vendor: VendorProfile) -> int:
        """
        Calculate days since menu was last updated.
        """
        if not vendor.last_menu_update:
            return 999  # Very old if never updated

        delta = timezone.now() - vendor.last_menu_update
        return delta.days

    @staticmethod
    def _send_whatsapp_notification(user, message: str):
        """
        Send WhatsApp notification to vendor.
        """
        # Use existing WhatsApp service
        from whatsapp_ai.services.whatsapp_service import WhatsAppService

        whatsapp_service = WhatsAppService()
        whatsapp_service.send_message(
            to=user.phone,
            message=message,
            message_type='notification'
        )

    @staticmethod
    def _send_email_notification(user, message: str):
        """
        Send email notification to vendor.
        """
        from django.core.mail import send_mail
        from django.conf import settings

        subject = f"Menu Update Required - {user.vendor_profile.business_name}"

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True
        )

    @staticmethod
    def _send_webhook_notification(vendor: VendorProfile, message: str):
        """
        Send webhook notification to vendor's configured endpoint.
        """
        # This would require adding webhook_url field to VendorProfile
        # For now, we'll implement a basic webhook system
        import requests
        import json

        webhook_url = getattr(vendor, 'webhook_url', None)
        if not webhook_url:
            return

        payload = {
            'event_type': 'menu_update_required',
            'vendor_id': vendor.id,
            'business_name': vendor.business_name,
            'message': message,
            'last_menu_update': vendor.last_menu_update.isoformat() if vendor.last_menu_update else None,
            'timestamp': timezone.now().isoformat()
        }

        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Bestyy-Webhook/1.0'
        }

        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers=headers,
            timeout=10
        )

        if response.status_code not in [200, 201, 202]:
            raise Exception(f"Webhook failed with status {response.status_code}")

    @staticmethod
    def get_stale_menu_vendors():
        """
        Get list of vendors with stale menus for reporting.
        """
        two_days_ago = timezone.now() - timedelta(days=2)

        return VendorProfile.objects.filter(
            verification_status='approved',
            is_suspended=False,
            last_menu_update__lt=two_days_ago
        ).select_related('user').annotate(
            days_stale=timezone.now() - F('last_menu_update')
        ).order_by('last_menu_update')

    @staticmethod
    def force_menu_update_notification(vendor_id: int):
        """
        Manually trigger menu update notification for a specific vendor.
        Useful for testing or admin actions.
        """
        try:
            vendor = VendorProfile.objects.get(id=vendor_id)
            MenuUpdateNotificationService._notify_vendor_menu_update(vendor)
            return True
        except VendorProfile.DoesNotExist:
            return False