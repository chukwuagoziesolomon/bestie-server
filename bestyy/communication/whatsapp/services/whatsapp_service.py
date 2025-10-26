"""
WhatsApp and SMS service using Twilio API
"""
import os
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from django.conf import settings
from decouple import config

logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    Service for sending WhatsApp messages and SMS using Twilio API
    """

    def __init__(self):
        # Get Twilio credentials from environment
        self.account_sid = config('TWILIO_ACCOUNT_SID', default='')
        self.auth_token = config('TWILIO_AUTH_TOKEN', default='')
        self.from_whatsapp = config('TWILIO_WHATSAPP_NUMBER', default='whatsapp:+14155238886')  # Default Twilio sandbox number
        self.from_sms = config('TWILIO_SMS_NUMBER', default='')

        # Initialize Twilio client
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            logger.warning("Twilio credentials not found. WhatsApp/SMS services will not work.")
            self.client = None

    def send_message(self, to, message, message_type='whatsapp', **kwargs):
        """
        Send a message via WhatsApp or SMS

        Args:
            to (str): Recipient phone number (with country code)
            message (str): Message content
            message_type (str): 'whatsapp' or 'sms'
            **kwargs: Additional parameters

        Returns:
            dict: {'success': bool, 'message': str, 'sid': str}
        """
        if not self.client:
            logger.error("Twilio client not initialized")
            return {'success': False, 'message': 'Twilio service not configured'}

        try:
            # Format phone number (ensure it starts with +)
            if not to.startswith('+'):
                # Try to add Nigerian country code if not present
                if to.startswith('0'):
                    to = '+234' + to[1:]
                else:
                    to = '+' + to

            if message_type.lower() == 'whatsapp':
                return self._send_whatsapp_message(to, message, **kwargs)
            elif message_type.lower() == 'sms':
                return self._send_sms_message(to, message, **kwargs)
            else:
                return {'success': False, 'message': f'Invalid message type: {message_type}'}

        except Exception as e:
            logger.error(f"Failed to send {message_type} message to {to}: {str(e)}")
            return {'success': False, 'message': f'Failed to send message: {str(e)}'}

    def _send_whatsapp_message(self, to, message, **kwargs):
        """
        Send WhatsApp message using Twilio
        """
        try:
            message_obj = self.client.messages.create(
                from_=self.from_whatsapp,
                body=message,
                to=f'whatsapp:{to}',
                **kwargs
            )

            logger.info(f"WhatsApp message sent successfully to {to}, SID: {message_obj.sid}")
            return {
                'success': True,
                'message': 'WhatsApp message sent successfully',
                'sid': message_obj.sid,
                'status': message_obj.status
            }

        except TwilioException as e:
            logger.error(f"Twilio WhatsApp error: {str(e)}")
            return {'success': False, 'message': f'WhatsApp send failed: {str(e)}'}
        except Exception as e:
            logger.error(f"Unexpected WhatsApp error: {str(e)}")
            return {'success': False, 'message': f'Unexpected error: {str(e)}'}

    def _send_sms_message(self, to, message, **kwargs):
        """
        Send SMS message using Twilio
        """
        if not self.from_sms:
            return {'success': False, 'message': 'SMS sender number not configured'}

        try:
            message_obj = self.client.messages.create(
                from_=self.from_sms,
                body=message,
                to=to,
                **kwargs
            )

            logger.info(f"SMS sent successfully to {to}, SID: {message_obj.sid}")
            return {
                'success': True,
                'message': 'SMS sent successfully',
                'sid': message_obj.sid,
                'status': message_obj.status
            }

        except TwilioException as e:
            logger.error(f"Twilio SMS error: {str(e)}")
            return {'success': False, 'message': f'SMS send failed: {str(e)}'}
        except Exception as e:
            logger.error(f"Unexpected SMS error: {str(e)}")
            return {'success': False, 'message': f'Unexpected error: {str(e)}'}

    def send_verification_code(self, to, code, method='whatsapp'):
        """
        Send verification code via WhatsApp or SMS

        Args:
            to (str): Phone number
            code (str): Verification code
            method (str): 'whatsapp' or 'sms'

        Returns:
            dict: Result of send operation
        """
        message = f"""🔔 Bestyy Verification Code

Hi there!

Your verification code is: *{code}*

This code will expire in 10 minutes.

If you didn't request this code, please ignore this message.

Best regards,
Bestyy Team"""

        return self.send_message(to, message, message_type=method)

    def send_notification(self, to, title, message, method='whatsapp'):
        """
        Send notification message

        Args:
            to (str): Phone number
            title (str): Notification title
            message (str): Notification content
            method (str): 'whatsapp' or 'sms'
        """
        full_message = f"""🔔 {title}

{message}

Best regards,
Bestyy Team"""

        return self.send_message(to, full_message, message_type=method)

    def get_message_status(self, message_sid):
        """
        Get the status of a sent message

        Args:
            message_sid (str): Twilio message SID

        Returns:
            dict: Message status information
        """
        if not self.client:
            return {'success': False, 'message': 'Twilio service not configured'}

        try:
            message = self.client.messages(message_sid).fetch()
            return {
                'success': True,
                'sid': message.sid,
                'status': message.status,
                'to': message.to,
                'from': message.from_,
                'date_sent': message.date_sent,
                'error_code': message.error_code,
                'error_message': message.error_message
            }
        except TwilioException as e:
            logger.error(f"Failed to get message status for {message_sid}: {str(e)}")
            return {'success': False, 'message': f'Failed to get status: {str(e)}'}