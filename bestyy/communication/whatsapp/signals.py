from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
import logging

from .models import WhatsAppMessage, WhatsAppConversation

logger = logging.getLogger(__name__)


@receiver(post_save, sender=WhatsAppMessage)
def update_conversation_last_message(sender, instance, created, **kwargs):
    """
    Update conversation's last_message_at when a new message is created
    """
    if created:
        try:
            conversation = instance.conversation
            conversation.last_message_at = instance.timestamp
            conversation.save(update_fields=['last_message_at'])
            logger.debug(f"Updated last_message_at for conversation {conversation.id}")
        except Exception as e:
            logger.error(f"Error updating conversation last_message_at: {str(e)}")


@receiver(post_save, sender=WhatsAppMessage)
def log_message_creation(sender, instance, created, **kwargs):
    """
    Log when new messages are created
    """
    if created:
        logger.info(
            f"New WhatsApp message created: {instance.id} - "
            f"{instance.direction} - {instance.message_type} - "
            f"From: {instance.conversation.phone_number}"
        )


@receiver(pre_save, sender=WhatsAppMessage)
def validate_message_data(sender, instance, **kwargs):
    """
    Validate message data before saving
    """
    # Ensure message_id is unique
    if instance.message_id:
        existing = WhatsAppMessage.objects.filter(
            message_id=instance.message_id
        ).exclude(id=instance.id)
        
        if existing.exists():
            logger.warning(f"Duplicate message_id detected: {instance.message_id}")
    
    # Ensure timestamp is set
    if not instance.timestamp:
        instance.timestamp = timezone.now()
        logger.debug(f"Set timestamp for message {instance.id}")


@receiver(post_save, sender=WhatsAppConversation)
def log_conversation_creation(sender, instance, created, **kwargs):
    """
    Log when new conversations are created
    """
    if created:
        logger.info(
            f"New WhatsApp conversation created: {instance.id} - "
            f"Phone: {instance.phone_number}"
        )
