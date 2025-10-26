from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from bestyy.core_features.user.models import VendorProfile, MenuUpdateReminderLog

class MenuReminderService:
    @staticmethod
    def get_vendors_needing_reminder():
        """
        Get vendors who need menu update reminders:
        1. Vendors who have NEVER set menu items (last_menu_update is NULL)
        2. Vendors who haven't updated their menu in >24 hours
        """
        one_day_ago = timezone.now() - timedelta(hours=24)
        return VendorProfile.objects.filter(
            verification_status='approved',
            is_suspended=False
        ).filter(
            # Either never set menu items OR haven't updated in >24h
            Q(last_menu_update__isnull=True) | Q(last_menu_update__lt=one_day_ago)
        )

    @staticmethod
    def send_reminders():
        vendors = MenuReminderService.get_vendors_needing_reminder()
        for vendor in vendors:
            phone = vendor.phone  # Or vendor.whatsapp_phone if present
            if phone:
                # Different messages based on whether they've ever set menu items
                if vendor.last_menu_update is None:
                    message = (
                        f"Hello {vendor.business_name},\n"
                        "Welcome to Bestyy! To start receiving customer orders, please add your menu items in your vendor dashboard. "
                        "Customers can only see vendors with active menus. Get started today!"
                    )
                else:
                    message = (
                        f"Hello {vendor.business_name},\n"
                        "To stay recommended to customers, please update your menu in your dashboard. "
                        "Menus not updated in the last 2 days are excluded from recommendations."
                    )
                
                # Send WhatsApp reminder
                result = MenuReminderService._send_whatsapp(phone, message)
                MenuUpdateReminderLog.objects.create(
                    vendor=vendor,
                    reminder_type='whatsapp',
                    status='sent' if result else 'failed',
                    message_body=message
                )

    @staticmethod
    def _send_whatsapp(phone, message):
        # Production-grade WhatsApp integration using existing WhatsApp service
        try:
            from bestyy.communication.whatsapp.services import WhatsAppService
            from django.conf import settings
            
            # Use existing WhatsApp service for production reliability
            whatsapp_service = WhatsAppService()
            result = whatsapp_service.send_message(
                to=phone,
                message=message
            )
            
            if result.get('success'):
                logger.info(f'WhatsApp menu reminder sent successfully to {phone}')
                return True
            else:
                logger.error(f'WhatsApp menu reminder failed to {phone}: {result.get("error", "Unknown error")}')
                return False
                
        except Exception as e:
            logger.error(f'Failed to send WhatsApp menu reminder to {phone}: {str(e)}')
            return False
