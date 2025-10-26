"""
Celery tasks for production-grade background job processing.
These tasks can be scheduled using Celery Beat for automated operations.
"""
from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_menu_update_reminders():
    """
    Celery task to send WhatsApp menu update reminders to vendors.
    This can be scheduled to run daily using Celery Beat.
    """
    try:
        from bestyy.core_features.user.services.menu_reminder_service import MenuReminderService
        
        logger.info('Starting scheduled menu update reminders task')
        MenuReminderService.send_reminders()
        logger.info('Completed scheduled menu update reminders task')
        
        return {
            'success': True,
            'message': 'Menu update reminders sent successfully',
            'timestamp': timezone.now().isoformat()
        }
            except Exception as e:
        logger.error(f'Menu update reminders task failed: {str(e)}')
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }

@shared_task
def update_vendor_popularity_metrics():
    """
    Celery task to update vendor popularity metrics.
    This can be scheduled to run periodically to keep metrics fresh.
    """
    try:
        from bestyy.core_features.user.services.popularity_update_service import VendorPopularityUpdateService
        from bestyy.core_features.user.models import VendorProfile
        
        logger.info('Starting vendor popularity metrics update task')
        
        # Update metrics for all vendors
        vendors = VendorProfile.objects.filter(verification_status='approved')
        updated_count = 0
        
        for vendor in vendors:
            try:
                VendorPopularityUpdateService.update_vendor_metrics(vendor)
                updated_count += 1
            except Exception as e:
                logger.error(f'Failed to update metrics for vendor {vendor.id}: {str(e)}')
        
        logger.info(f'Completed vendor popularity metrics update task. Updated {updated_count} vendors.')
        
        return {
            'success': True,
            'message': f'Updated popularity metrics for {updated_count} vendors',
            'updated_count': updated_count,
            'timestamp': timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f'Vendor popularity metrics update task failed: {str(e)}')
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }