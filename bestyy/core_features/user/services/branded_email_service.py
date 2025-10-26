"""
Branded email service for Bestyy - creates professional HTML emails with logo and brand colors
"""
import logging
from django.conf import settings
from django.core.mail import EmailMessage
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class BrandedEmailService:
    """
    Service for sending branded HTML emails with Bestyy logo and colors
    """

    # Bestyy brand colors
    PRIMARY_GRADIENT = "linear-gradient(90deg, #23C7B2 0%, #25AC9B 100%)"
    PRIMARY_COLOR = "#23C7B2"
    SECONDARY_COLOR = "#25AC9B"
    ACCENT_COLOR = "#FF6B35"  # Orange accent
    TEXT_COLOR = "#2D3748"
    LIGHT_BG = "#F7FAFC"

    @staticmethod
    def get_base_template() -> str:
        """Get the base HTML template with Bestyy branding"""
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Bestyy</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: {BrandedEmailService.TEXT_COLOR};
                    margin: 0;
                    padding: 0;
                    background-color: #f8f9fa;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    background: {BrandedEmailService.PRIMARY_GRADIENT};
                    padding: 30px 20px;
                    text-align: center;
                    color: white;
                }}
                .logo {{
                    max-width: 150px;
                    height: auto;
                    margin-bottom: 10px;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                    font-weight: 600;
                }}
                .content {{
                    padding: 30px 20px;
                }}
                .status-badge {{
                    display: inline-block;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 14px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                .status-approved {{
                    background-color: #D4EDDA;
                    color: #155724;
                }}
                .status-rejected {{
                    background-color: #F8D7DA;
                    color: #721C24;
                }}
                .status-pending {{
                    background-color: #FFF3CD;
                    color: #856404;
                }}
                .info-box {{
                    background-color: {BrandedEmailService.LIGHT_BG};
                    border-left: 4px solid {BrandedEmailService.PRIMARY_COLOR};
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                }}
                .action-button {{
                    display: inline-block;
                    background: {BrandedEmailService.PRIMARY_GRADIENT};
                    color: white;
                    text-decoration: none;
                    padding: 12px 24px;
                    border-radius: 8px;
                    font-weight: 600;
                    margin: 10px 5px;
                    text-align: center;
                    transition: opacity 0.3s ease;
                }}
                .action-button:hover {{
                    opacity: 0.9;
                }}
                .footer {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #718096;
                    font-size: 14px;
                    border-top: 1px solid #e2e8f0;
                }}
                .social-links {{
                    margin: 15px 0;
                }}
                .social-links a {{
                    color: {BrandedEmailService.PRIMARY_COLOR};
                    text-decoration: none;
                    margin: 0 10px;
                    font-weight: 500;
                }}
                .contact-info {{
                    margin: 15px 0;
                }}
                .contact-info p {{
                    margin: 5px 0;
                }}
                @media (max-width: 600px) {{
                    .container {{
                        margin: 10px;
                        border-radius: 8px;
                    }}
                    .header {{
                        padding: 20px 15px;
                    }}
                    .content {{
                        padding: 20px 15px;
                    }}
                    .action-button {{
                        display: block;
                        margin: 10px 0;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="{settings.BASE_URL}/static/images/logo.png" alt="Bestyy Logo" class="logo">
                    <h1>Bestyy</h1>
                    <p>Connecting Customers with Local Vendors</p>
                </div>
                <div class="content">
                    {{CONTENT}}
                </div>
                <div class="footer">
                    <div class="contact-info">
                        <p><strong>Need Help?</strong></p>
                        <p>📧 support@bestyy.com | 📞 +234-XXX-XXXX</p>
                    </div>
                    <div class="social-links">
                        <a href="#">Facebook</a> |
                        <a href="#">Twitter</a> |
                        <a href="#">Instagram</a>
                    </div>
                    <p>This is an automated notification from Bestyy.<br>
                    © 2024 Bestyy. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def create_verification_email(
        user_type: str,
        user_profile,
        status: str,
        admin_notes: Optional[str] = None
    ) -> str:
        """Create branded verification email HTML"""
        business_name = getattr(user_profile, 'business_name', user_profile.user.get_full_name())

        if status == 'approved':
            status_class = 'status-approved'
            status_text = 'APPROVED'
            icon = '✅'
            title = f'Welcome to Bestyy!'
            subtitle = f'Your {user_type.title()} account has been approved!'

            if user_type == 'vendor':
                content = f"""
                <h2 style="color: {BrandedEmailService.TEXT_COLOR}; margin-top: 0;">{icon} {title}</h2>
                <p>Dear {business_name},</p>
                <p>We're thrilled to inform you that your vendor account has been successfully verified and approved!</p>

                <div class="status-badge {status_class}">{status_text}</div>

                <div class="info-box">
                    <h3 style="margin-top: 0; color: {BrandedEmailService.PRIMARY_COLOR};">🚀 What's Next?</h3>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>Your restaurant is now live on Bestyy platform</li>
                        <li>Customers can find and order from your establishment</li>
                        <li>Access all vendor dashboard features</li>
                        <li>Start receiving orders immediately</li>
                    </ul>
                </div>

                <div class="info-box">
                    <h3 style="margin-top: 0; color: {BrandedEmailService.PRIMARY_COLOR};">📱 Quick Actions</h3>
                    <ol style="margin: 10px 0; padding-left: 20px;">
                        <li>Complete your menu setup</li>
                        <li>Upload high-quality food images</li>
                        <li>Set delivery areas and timing</li>
                        <li>Configure payment settings</li>
                    </ol>
                </div>

                <a href="{settings.BASE_URL}/vendor/dashboard" class="action-button">Access Dashboard</a>
                """
            else:  # courier
                content = f"""
                <h2 style="color: {BrandedEmailService.TEXT_COLOR}; margin-top: 0;">{icon} {title}</h2>
                <p>Dear {user_profile.user.get_full_name()},</p>
                <p>We're excited to welcome you to the Bestyy delivery team!</p>

                <div class="status-badge {status_class}">{status_text}</div>

                <div class="info-box">
                    <h3 style="margin-top: 0; color: {BrandedEmailService.PRIMARY_COLOR};">🚀 What's Next?</h3>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>Receive delivery requests</li>
                        <li>Access the courier mobile app</li>
                        <li>Start earning by delivering orders</li>
                        <li>View available delivery opportunities</li>
                    </ul>
                </div>

                <div class="info-box">
                    <h3 style="margin-top: 0; color: {BrandedEmailService.PRIMARY_COLOR};">📱 Quick Actions</h3>
                    <ol style="margin: 10px 0; padding-left: 20px;">
                        <li>Download the Bestyy Courier app</li>
                        <li>Complete your profile setup</li>
                        <li>Set availability schedule</li>
                        <li>Choose preferred delivery areas</li>
                    </ol>
                </div>

                <a href="{settings.BASE_URL}/courier/dashboard" class="action-button">Access Dashboard</a>
                """

        elif status == 'rejected':
            status_class = 'status-rejected'
            status_text = 'NOT APPROVED'
            icon = '❌'
            title = f'{user_type.title()} Application Update'
            subtitle = f'Your application requires attention'

            content = f"""
            <h2 style="color: {BrandedEmailService.TEXT_COLOR}; margin-top: 0;">{icon} {title}</h2>
            <p>Dear {business_name},</p>
            <p>Thank you for your interest in joining Bestyy. After reviewing your application, we regret to inform you that it was not approved at this time.</p>

            <div class="status-badge {status_class}">{status_text}</div>

            <div class="info-box">
                <h3 style="margin-top: 0; color: {BrandedEmailService.PRIMARY_COLOR};">📝 Reason for Decision:</h3>
                <p style="margin: 10px 0;">{admin_notes or 'Your application did not meet our current verification requirements.'}</p>
            </div>

            <div class="info-box">
                <h3 style="margin-top: 0; color: {BrandedEmailService.PRIMARY_COLOR};">🔄 Next Steps:</h3>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>Review the feedback provided above</li>
                    <li>Address any issues mentioned</li>
                    <li>Resubmit your application with updated information</li>
                    <li>Ensure all documents are clear and valid</li>
                </ul>
            </div>

            <a href="{settings.BASE_URL}/apply" class="action-button">Reapply Now</a>
            """

        else:
            status_class = 'status-pending'
            status_text = status.upper()
            icon = '📋'
            title = f'{user_type.title()} Account Status Update'
            subtitle = f'Your account status has been updated'

            content = f"""
            <h2 style="color: {BrandedEmailService.TEXT_COLOR}; margin-top: 0;">{icon} {title}</h2>
            <p>Dear {business_name},</p>
            <p>This is to inform you that there has been an update to your {user_type} account status.</p>

            <div class="status-badge {status_class}">{status_text}</div>

            <div class="info-box">
                <p>If you have any questions about this status update, please don't hesitate to contact our support team.</p>
            </div>

            <a href="{settings.BASE_URL}/support" class="action-button">Contact Support</a>
            """

        return BrandedEmailService.get_base_template().replace('{{CONTENT}}', content)

    @staticmethod
    def create_order_notification_email(order_data: Dict) -> str:
        """Create branded order notification email for vendors"""
        items_html = ""
        for item in order_data.get('items', []):
            items_html += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e2e8f0;">
                    <strong>{item['name']}</strong>
                    {f"<br><small style='color: #718096;'>{item['special_instructions']}</small>" if item.get('special_instructions') else ""}
                </td>
                <td style="padding: 8px; border-bottom: 1px solid #e2e8f0; text-align: center;">{item['quantity']}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e2e8f0; text-align: right;">₦{item['price']}</td>
            </tr>
            """

        content = f"""
        <h2 style="color: {BrandedEmailService.TEXT_COLOR}; margin-top: 0;">🛒 New Order Received!</h2>
        <p style="font-size: 18px; margin: 10px 0;"><strong>Order #{order_data['order_number']}</strong></p>

        <div class="info-box">
            <h3 style="margin-top: 0; color: {BrandedEmailService.PRIMARY_COLOR};">👤 Customer Details</h3>
            <p style="margin: 5px 0;"><strong>Name:</strong> {order_data['customer_name']}</p>
            <p style="margin: 5px 0;"><strong>Phone:</strong> {order_data['customer_phone']}</p>
            <p style="margin: 5px 0;"><strong>Address:</strong> {order_data['delivery_address']}</p>
            {f"<p style='margin: 5px 0;'><strong>Instructions:</strong> {order_data['special_instructions']}</p>" if order_data.get('special_instructions') else ""}
        </div>

        <h3 style="color: {BrandedEmailService.PRIMARY_COLOR}; margin: 30px 0 15px 0;">📋 Order Items</h3>
        <table style="width: 100%; border-collapse: collapse; background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
            <thead>
                <tr style="background-color: {BrandedEmailService.LIGHT_BG};">
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: {BrandedEmailService.TEXT_COLOR};">Item</th>
                    <th style="padding: 12px; text-align: center; font-weight: 600; color: {BrandedEmailService.TEXT_COLOR};">Qty</th>
                    <th style="padding: 12px; text-align: right; font-weight: 600; color: {BrandedEmailService.TEXT_COLOR};">Price</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
            <tfoot>
                <tr style="background-color: {BrandedEmailService.LIGHT_BG}; font-weight: 600;">
                    <td colspan="2" style="padding: 12px; text-align: right;">Total:</td>
                    <td style="padding: 12px; text-align: right; color: {BrandedEmailService.PRIMARY_COLOR};">{order_data['total_amount']}</td>
                </tr>
            </tfoot>
        </table>

        <div class="info-box">
            <h3 style="margin-top: 0; color: {BrandedEmailService.PRIMARY_COLOR};">⏰ Delivery Information</h3>
            <p style="margin: 5px 0;"><strong>Estimated Time:</strong> {order_data.get('estimated_delivery', '30-45 minutes')}</p>
            <p style="margin: 5px 0;">Please prepare the order and confirm when ready for pickup.</p>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="#" class="action-button" style="margin-right: 10px;">Accept Order</a>
            <a href="#" class="action-button" style="background: #dc3545;">Reject Order</a>
        </div>
        """

        return BrandedEmailService.get_base_template().replace('{{CONTENT}}', content)

    @staticmethod
    def send_branded_email(
        subject: str,
        html_content: str,
        recipient_list: list,
        from_email: Optional[str] = None
    ) -> Dict:
        """Send branded HTML email"""
        try:
            if not from_email:
                from_email = settings.DEFAULT_FROM_EMAIL

            email = EmailMessage(
                subject=subject,
                body=html_content,
                from_email=from_email,
                to=recipient_list,
            )
            email.content_subtype = "html"
            email.send(fail_silently=False)

            logger.info(f"Branded email sent successfully to {recipient_list}")

            return {
                'success': True,
                'message': f'Branded HTML email sent to {recipient_list}',
                'recipients': recipient_list
            }

        except Exception as e:
            logger.error(f"Branded email failed: {str(e)}")
            return {
                'success': False,
                'message': f'Email failed: {str(e)}'
            }