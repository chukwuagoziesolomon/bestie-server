"""
Management command to test email configuration and send test emails.
"""
import logging
from django.core.management.base import BaseCommand
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test email configuration and send test emails'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            help='Email address to send test to',
            default='test@example.com'
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['plain', 'html', 'vendor', 'courier'],
            default='plain',
            help='Type of test email to send'
        )

    def handle(self, *args, **options):
        recipient = options['to']
        email_type = options['type']

        self.stdout.write(
            self.style.SUCCESS(f'Testing email configuration...')
        )
        self.stdout.write(f'SMTP Host: {settings.EMAIL_HOST}')
        self.stdout.write(f'SMTP Port: {settings.EMAIL_PORT}')
        self.stdout.write(f'From Email: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'Test Recipient: {recipient}')
        self.stdout.write(f'Email Type: {email_type}')
        self.stdout.write('---')

        try:
            if email_type == 'plain':
                self._send_plain_test_email(recipient)
            elif email_type == 'html':
                self._send_html_test_email(recipient)
            elif email_type == 'vendor':
                self._send_vendor_test_email(recipient)
            elif email_type == 'courier':
                self._send_courier_test_email(recipient)

            self.stdout.write(
                self.style.SUCCESS('Email sent successfully!')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Email failed: {str(e)}')
            )
            logger.error(f'Email test failed: {str(e)}')

    def _send_plain_test_email(self, recipient):
        """Send a plain text test email."""
        subject = '[Bestyy] Email Configuration Test'
        message = """
        Hello!

        This is a test email to verify your SMTP configuration is working correctly.

        If you received this email, your email settings are properly configured!

        Best regards,
        Bestyy Team
        """

        send_mail(
            subject=subject,
            message=message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )

    def _send_html_test_email(self, recipient):
        """Send an HTML test email."""
        subject = '[Bestyy] HTML Email Test'

        html_message = """
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; text-align: center;">
                <h1 style="color: #333; margin: 0;">Bestyy Email Test</h1>
                <p style="color: #666; margin: 10px 0;">HTML Email Configuration Test</p>
            </div>
            <div style="padding: 20px;">
                <h2 style="color: #333;">Hello!</h2>
                <p>This is a test HTML email to verify your SMTP configuration is working correctly.</p>
                <p>If you can see this formatted content, your HTML email settings are properly configured!</p>
                <div style="background-color: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>Test Details:</strong><br>
                    • SMTP Host: """ + str(settings.EMAIL_HOST) + """<br>
                    • SMTP Port: """ + str(settings.EMAIL_PORT) + """<br>
                    • From Email: """ + str(settings.DEFAULT_FROM_EMAIL) + """<br>
                </div>
                <p>Best regards,<br><strong>Bestyy Team</strong></p>
            </div>
        </body>
        </html>
        """

        email = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)

    def _send_vendor_test_email(self, recipient):
        """Send a vendor notification test email."""
        subject = '[Bestyy] New Order Notification - Test'

        # Mock order data
        order_data = {
            'order_number': '#TEST-123',
            'customer_name': 'John Doe',
            'customer_phone': '+2348012345678',
            'total_amount': '₦5,800.00',
            'items': [
                {
                    'name': 'Jollof Rice',
                    'quantity': 2,
                    'price': '₦2,500.00',
                    'special_instructions': 'No onions please'
                },
                {
                    'name': 'Chicken',
                    'quantity': 1,
                    'price': '₦800.00',
                    'special_instructions': None
                }
            ],
            'delivery_address': '123 Victoria Island, Lagos',
            'special_instructions': 'Call when you arrive',
            'estimated_delivery': '30-45 minutes'
        }

        html_message = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f8f9fa;">
            <div style="background-color: #28a745; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">🛒 New Order Received!</h1>
                <p style="margin: 5px 0;">Order {order_data['order_number']}</p>
            </div>
            <div style="background-color: white; padding: 20px; margin: 20px; border-radius: 8px;">
                <h2 style="color: #333; margin-top: 0;">Customer Details</h2>
                <p><strong>Name:</strong> {order_data['customer_name']}</p>
                <p><strong>Phone:</strong> {order_data['customer_phone']}</p>
                <p><strong>Delivery Address:</strong> {order_data['delivery_address']}</p>
                {f"<p><strong>Special Instructions:</strong> {order_data['special_instructions']}</p>" if order_data['special_instructions'] else ""}

                <h3 style="color: #333; border-bottom: 2px solid #28a745; padding-bottom: 5px;">Order Items</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background-color: #f8f9fa;">
                            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Item</th>
                            <th style="border: 1px solid #ddd; padding: 8px; text-align: center;">Qty</th>
                            <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Price</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        for item in order_data['items']:
            html_message += f"""
                        <tr>
                            <td style="border: 1px solid #ddd; padding: 8px;">
                                <strong>{item['name']}</strong>
                                {f"<br><small style='color: #666;'>{item['special_instructions']}</small>" if item['special_instructions'] else ""}
                            </td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{item['quantity']}</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{item['price']}</td>
                        </tr>
            """

        html_message += f"""
                    </tbody>
                    <tfoot>
                        <tr style="background-color: #f8f9fa; font-weight: bold;">
                            <td colspan="2" style="border: 1px solid #ddd; padding: 8px; text-align: right;">Total:</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{order_data['total_amount']}</td>
                        </tr>
                    </tfoot>
                </table>

                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h4 style="margin: 0; color: #856404;">⏰ Delivery Information</h4>
                    <p style="margin: 5px 0;">Estimated delivery time: <strong>{order_data['estimated_delivery']}</strong></p>
                    <p style="margin: 5px 0;">Please prepare the order and confirm when ready for pickup.</p>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="#" style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">Accept Order</a>
                    <a href="#" style="background-color: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; margin-left: 10px;">Reject Order</a>
                </div>
            </div>
            <div style="text-align: center; color: #666; font-size: 12px; padding: 20px;">
                <p>This is an automated notification from Bestyy.</p>
                <p>Bestyy - Connecting Customers with Local Vendors</p>
            </div>
        </body>
        </html>
        """

        email = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)

    def _send_courier_test_email(self, recipient):
        """Send a courier notification test email."""
        subject = '[Bestyy] Delivery Assignment - Test'

        # Mock delivery data
        delivery_data = {
            'order_number': '#TEST-123',
            'vendor_name': 'Burger Palace',
            'vendor_phone': '+2348012345678',
            'customer_name': 'John Doe',
            'customer_phone': '+2348098765432',
            'pickup_address': '123 Victoria Island, Lagos',
            'delivery_address': '456 Lekki Phase 1, Lagos',
            'total_amount': '₦5,800.00',
            'delivery_fee': '₦500.00',
            'estimated_distance': '3.2 km',
            'estimated_time': '15-20 minutes'
        }

        html_message = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f8f9fa;">
            <div style="background-color: #007bff; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">🚚 New Delivery Assignment!</h1>
                <p style="margin: 5px 0;">Order {delivery_data['order_number']}</p>
            </div>
            <div style="background-color: white; padding: 20px; margin: 20px; border-radius: 8px;">
                <h2 style="color: #333; margin-top: 0;">Delivery Details</h2>

                <div style="display: flex; justify-content: space-between; margin: 20px 0;">
                    <div style="flex: 1; margin-right: 10px;">
                        <h3 style="color: #28a745; margin: 0;">📍 Pickup Location</h3>
                        <p style="margin: 5px 0;"><strong>{delivery_data['vendor_name']}</strong></p>
                        <p style="margin: 5px 0;">{delivery_data['pickup_address']}</p>
                        <p style="margin: 5px 0;">📞 {delivery_data['vendor_phone']}</p>
                    </div>
                    <div style="flex: 1; margin-left: 10px;">
                        <h3 style="color: #dc3545; margin: 0;">🏠 Delivery Location</h3>
                        <p style="margin: 5px 0;"><strong>{delivery_data['customer_name']}</strong></p>
                        <p style="margin: 5px 0;">{delivery_data['delivery_address']}</p>
                        <p style="margin: 5px 0;">📞 {delivery_data['customer_phone']}</p>
                    </div>
                </div>

                <div style="background-color: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h4 style="margin: 0; color: #333;">📊 Delivery Information</h4>
                    <p style="margin: 5px 0;"><strong>Distance:</strong> {delivery_data['estimated_distance']}</p>
                    <p style="margin: 5px 0;"><strong>Estimated Time:</strong> {delivery_data['estimated_time']}</p>
                    <p style="margin: 5px 0;"><strong>Order Value:</strong> {delivery_data['total_amount']}</p>
                    <p style="margin: 5px 0;"><strong>Delivery Fee:</strong> {delivery_data['delivery_fee']}</p>
                </div>

                <div style="background-color: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h4 style="margin: 0; color: #155724;">✅ Instructions</h4>
                    <ol style="margin: 10px 0; padding-left: 20px;">
                        <li>Contact the vendor to confirm order readiness</li>
                        <li>Pick up the order from the vendor location</li>
                        <li>Call the customer when approaching delivery location</li>
                        <li>Collect payment from customer</li>
                        <li>Mark delivery as completed in the app</li>
                    </ol>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="#" style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">Accept Delivery</a>
                    <a href="#" style="background-color: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; margin-left: 10px;">Decline Delivery</a>
                </div>
            </div>
            <div style="text-align: center; color: #666; font-size: 12px; padding: 20px;">
                <p>This is an automated notification from Bestyy.</p>
                <p>Bestyy - Connecting Customers with Local Vendors</p>
            </div>
        </body>
        </html>
        """

        email = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)