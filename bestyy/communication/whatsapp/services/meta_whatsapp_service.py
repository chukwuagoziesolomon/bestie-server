"""
Meta WhatsApp Business API service
"""
import requests
import json
import logging
from django.conf import settings
from decouple import config

logger = logging.getLogger(__name__)


class MetaWhatsAppService:
    """
    Service for sending WhatsApp messages using Meta WhatsApp Business API
    """

    def __init__(self):
        # Get Meta WhatsApp credentials from Django settings
        self.access_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '')
        self.phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')
        self.api_version = 'v18.0'
        self.base_url = f'https://graph.facebook.com/{self.api_version}'

        if not self.access_token or not self.phone_number_id:
            logger.warning("Meta WhatsApp credentials not found. Meta WhatsApp services will not work.")

    def send_message(self, to, message, message_type='text', **kwargs):
        """
        Send a message via Meta WhatsApp Business API

        Args:
            to (str): Recipient phone number (with country code, no +)
            message (str): Message content
            message_type (str): 'text', 'image', 'document', etc.
            **kwargs: Additional parameters

        Returns:
            dict: {'success': bool, 'message': str, 'message_id': str}
        """
        if not self.access_token or not self.phone_number_id:
            logger.error("Meta WhatsApp service not configured")
            return {'success': False, 'message': 'Meta WhatsApp service not configured'}

        try:
            # Format phone number (ensure no + prefix)
            if to.startswith('+'):
                to = to[1:]

            url = f'{self.base_url}/{self.phone_number_id}/messages'
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            # Prepare message payload based on type
            if message_type == 'text':
                payload = self._prepare_text_message(to, message)
            elif message_type == 'image':
                payload = self._prepare_image_message(to, message, **kwargs)
            elif message_type == 'document':
                payload = self._prepare_document_message(to, message, **kwargs)
            else:
                return {'success': False, 'message': f'Unsupported message type: {message_type}'}

            # Send the message
            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                response_data = response.json()
                message_id = response_data.get('messages', [{}])[0].get('id')

                logger.info(f"Meta WhatsApp message sent successfully to {to}, ID: {message_id}")
                return {
                    'success': True,
                    'message': 'Message sent successfully',
                    'message_id': message_id,
                    'response': response_data
                }
            else:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', 'Unknown error')

                logger.error(f"Meta WhatsApp API error: {response.status_code} - {error_message}")
                return {
                    'success': False,
                    'message': f'Failed to send message: {error_message}',
                    'error_code': response.status_code,
                    'error_data': error_data
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"Meta WhatsApp API request error: {str(e)}")
            return {'success': False, 'message': f'Request error: {str(e)}'}
        except Exception as e:
            logger.error(f"Unexpected Meta WhatsApp error: {str(e)}")
            return {'success': False, 'message': f'Unexpected error: {str(e)}'}

    def _prepare_text_message(self, to, message):
        """Prepare text message payload"""
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "body": message
            }
        }

    def _prepare_image_message(self, to, image_url, caption=None):
        """Prepare image message payload"""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": {
                "link": image_url
            }
        }
        if caption:
            payload["image"]["caption"] = caption
        return payload

    def _prepare_document_message(self, to, document_url, filename=None, caption=None):
        """Prepare document message payload"""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "document",
            "document": {
                "link": document_url
            }
        }
        if filename:
            payload["document"]["filename"] = filename
        if caption:
            payload["document"]["caption"] = caption
        return payload

    def send_template_message(self, to, template_name, language_code='en', components=None):
        """
        Send a WhatsApp template message

        Args:
            to (str): Recipient phone number (no + prefix)
            template_name (str): Template name
            language_code (str): Language code (default: 'en')
            components (list): Template components

        Returns:
            dict: Send result
        """
        if not self.access_token or not self.phone_number_id:
            return {'success': False, 'message': 'Meta WhatsApp service not configured'}

        try:
            if to.startswith('+'):
                to = to[1:]

            url = f'{self.base_url}/{self.phone_number_id}/messages'
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": language_code
                    }
                }
            }

            if components:
                payload["template"]["components"] = components

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                response_data = response.json()
                message_id = response_data.get('messages', [{}])[0].get('id')

                logger.info(f"Meta WhatsApp template message sent successfully to {to}, ID: {message_id}")
                return {
                    'success': True,
                    'message': 'Template message sent successfully',
                    'message_id': message_id,
                    'response': response_data
                }
            else:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', 'Unknown error')

                logger.error(f"Meta WhatsApp template API error: {response.status_code} - {error_message}")
                return {
                    'success': False,
                    'message': f'Failed to send template message: {error_message}',
                    'error_code': response.status_code,
                    'error_data': error_data
                }

        except Exception as e:
            logger.error(f"Error sending Meta WhatsApp template message: {str(e)}")
            return {'success': False, 'message': f'Error: {str(e)}'}

    def get_message_status(self, message_id):
        """
        Get the status of a sent message

        Args:
            message_id (str): WhatsApp message ID

        Returns:
            dict: Message status information
        """
        if not self.access_token:
            return {'success': False, 'message': 'Meta WhatsApp service not configured'}

        try:
            url = f'{self.base_url}/{message_id}'
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                status_data = response.json()
                return {
                    'success': True,
                    'message_id': message_id,
                    'status': status_data.get('status'),
                    'timestamp': status_data.get('timestamp'),
                    'recipient_id': status_data.get('recipient_id'),
                    'data': status_data
                }
            else:
                return {
                    'success': False,
                    'message': f'Failed to get message status: {response.status_code}',
                    'error_data': response.json()
                }

        except Exception as e:
            logger.error(f"Error getting message status: {str(e)}")
            return {'success': False, 'message': f'Error: {str(e)}'}
