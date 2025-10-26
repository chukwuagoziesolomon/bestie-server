"""
WhatsApp verification notification service
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class WhatsAppVerificationService:
    """
    Service for sending WhatsApp verification notifications
    """
    
    @staticmethod
    def create_verification_message(user_type: str, user_profile, status: str, admin_notes: Optional[str] = None) -> str:
        """Create verification status change message"""
        business_name = getattr(user_profile, 'business_name', user_profile.user.get_full_name())
        
        if status == 'approved':
            if user_type == 'vendor':
                return f"""🎉 *CONGRATULATIONS!*

Your vendor account has been *APPROVED* on Bestyy!

🏪 *Business:* {business_name}
✅ *Status:* VERIFIED & APPROVED
📅 *Date:* {user_profile.verification_date.strftime('%B %d, %Y') if hasattr(user_profile, 'verification_date') and user_profile.verification_date else 'Today'}

🚀 *What's Next?*
• Your restaurant is now live on Bestyy
• Customers can find and order from you
• Complete your menu setup
• Start receiving orders immediately

📱 *Quick Setup:*
1. Upload your menu items
2. Add high-quality food photos
3. Set delivery areas
4. Configure payment settings

💡 *Pro Tips:*
• Keep menu updated and accurate
• Respond quickly to orders
• Maintain high food quality
• Use attractive food photos

📞 *Need Help?*
Contact us:
• Email: support@bestyy.com
• Phone: +234-XXX-XXXX

Welcome to the Bestyy family! 🍽️

---
*Bestyy - Food Delivery Platform*"""
            else:  # courier
                return f"""🎉 *CONGRATULATIONS!*

Your courier account has been *APPROVED* on Bestyy!

👤 *Name:* {user_profile.user.get_full_name()}
✅ *Status:* VERIFIED & APPROVED
📅 *Date:* {user_profile.verification_date.strftime('%B %d, %Y') if hasattr(user_profile, 'verification_date') and user_profile.verification_date else 'Today'}

🚀 *What's Next?*
• Download the Bestyy Courier app
• Complete your profile setup
• Set your availability schedule
• Start accepting delivery requests

📱 *Quick Setup:*
1. Download Bestyy Courier app
2. Set your working hours
3. Choose delivery areas
4. Update your vehicle info

💡 *Pro Tips:*
• Always be professional
• Keep your vehicle in good condition
• Communicate clearly with customers
• Deliver orders on time

📞 *Need Help?*
Contact us:
• Email: support@bestyy.com
• Phone: +234-XXX-XXXX

Welcome to the Bestyy delivery team! 🚚

---
*Bestyy - Food Delivery Platform*"""
        
        elif status == 'rejected':
            if user_type == 'vendor':
                return f"""📋 *Vendor Application Update*

Dear {business_name},

Thank you for your interest in joining Bestyy as a vendor partner.

❌ *Status:* NOT APPROVED
📅 *Date:* {user_profile.verification_date.strftime('%B %d, %Y') if hasattr(user_profile, 'verification_date') and user_profile.verification_date else 'Today'}

📝 *Reason:*
{admin_notes or 'Your application did not meet our current verification requirements.'}

🔄 *Next Steps:*
• Review the feedback above
• Address any issues mentioned
• Update your application
• Resubmit with correct information

📞 *Need Clarification?*
Contact us:
• Email: support@bestyy.com
• Phone: +234-XXX-XXXX

We encourage you to reapply once you address the concerns mentioned above.

Best regards,
Bestyy Team

---
*Bestyy - Food Delivery Platform*"""
            else:  # courier
                return f"""📋 *Courier Application Update*

Dear {user_profile.user.get_full_name()},

Thank you for your interest in joining Bestyy as a delivery courier.

❌ *Status:* NOT APPROVED
📅 *Date:* {user_profile.verification_date.strftime('%B %d, %Y') if hasattr(user_profile, 'verification_date') and user_profile.verification_date else 'Today'}

📝 *Reason:*
{admin_notes or 'Your application did not meet our current verification requirements.'}

🔄 *Next Steps:*
• Review the feedback above
• Address any issues mentioned
• Update your application
• Resubmit with correct information

📞 *Need Clarification?*
Contact us:
• Email: support@bestyy.com
• Phone: +234-XXX-XXXX

We encourage you to reapply once you address the concerns mentioned above.

Best regards,
Bestyy Team

---
*Bestyy - Food Delivery Platform*"""
        
        else:  # Other status updates
            return f"""📋 *{user_type.title()} Account Status Update*

Dear {business_name if user_type == 'vendor' else user_profile.user.get_full_name()},

Your {user_type} account status has been updated.

📊 *New Status:* {status.upper()}
📅 *Date:* {user_profile.verification_date.strftime('%B %d, %Y') if hasattr(user_profile, 'verification_date') and user_profile.verification_date else 'Today'}

📞 *Need More Information?*
Contact us:
• Email: support@bestyy.com
• Phone: +234-XXX-XXXX

Best regards,
Bestyy Team

---
*Bestyy - Food Delivery Platform*"""






