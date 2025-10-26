# Email Notifications for Vendor Orders

## 📧 Overview

The Bestyy platform now includes **email notifications** for vendors when new orders are placed. Vendors receive detailed email notifications containing order information, customer details, and delivery instructions.

## 🔧 Configuration

### Development Mode (Default)
In development mode, emails are printed to the console instead of being sent via SMTP:

```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

### Production Mode
For production, configure SMTP settings in your environment variables:

```bash
# SMTP Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@bestyy.com
```

## 📋 Email Content

### Subject Line
```
New Order - {vendor_business_name}
```

### Email Body Includes:
- **Order Summary**: Customer name, total amount, order time
- **Order Contents**: Detailed items with quantities, prices, customizations, special instructions
- **Delivery Information**: Address, landmark, delivery instructions
- **Payment Method**: Cash on delivery or online payment
- **Professional Footer**: Bestyy team signature with no-reply notice

### Example Email Content:
```
Dear Burger Palace,

You have received a new order!

ORDER SUMMARY:
==============
Customer: John Doe
Total Amount: ₦4,000.00
Order Time: 2024-01-15 10:30:00

ORDER CONTENTS:
===============

• Classic Beef Burger x1
  Base Price: ₦2,500.00
  Total: ₦3,200.00
  Customizations:
    - Large Size (+₦500.00)
    - Extra Cheese (+₦200.00)
  Special Instructions: No onions please

• French Fries x1
  Base Price: ₦800.00
  Total: ₦800.00
  Special Instructions: Extra crispy

DELIVERY ADDRESS:
================
123 Independence Layout
Enugu, Enugu State
400001
Landmark: Near Central Bank

Delivery Instructions: Please call when you arrive

PAYMENT METHOD: Cash on Delivery

Please prepare this order and confirm when ready for delivery.

Best regards,
Bestyy Team

---
This is an automated notification. Please do not reply to this email.
For support, contact us through the Bestyy platform.
```

## 🚀 API Integration

### Order Placement Response
When an order is placed via `POST /api/user/orders/place/`, the response now includes email notification status:

```json
{
  "success": true,
  "order": {
    "id": 123,
    "order_number": "#123",
    "total_amount": 4000,
    "status": "pending"
  },
  "notifications": {
    "whatsapp": {
      "success": true,
      "message": "WhatsApp notification sent successfully",
      "service_used": "twilio"
    },
    "websocket": {
      "success": true,
      "message": "WebSocket notification sent successfully"
    },
    "email": {
      "success": true,
      "message": "Email sent to vendor@burgerpalace.com",
      "vendor_email": "vendor@burgerpalace.com"
    }
  }
}
```

## 🔍 Testing

### Test Email Notifications
Run the test script to verify email functionality:

```bash
python test_email_notifications.py
```

### Manual Testing
1. Place an order through the API
2. Check the response for email notification status
3. In development: Check console output for email content
4. In production: Check vendor's email inbox

## 📝 Vendor Email Requirements

For email notifications to work, vendors must have:
- `email` field in their VendorProfile model, OR
- `contact_email` field in their VendorProfile model

The system will use the first available email address.

## ⚙️ Email Settings Configuration

### Gmail Setup
1. Enable 2-factor authentication on your Gmail account
2. Generate an "App Password" for Bestyy
3. Use the app password in `EMAIL_HOST_PASSWORD`

### Other SMTP Providers
- **Outlook/Hotmail**: `smtp-mail.outlook.com`, port 587
- **Yahoo**: `smtp.mail.yahoo.com`, port 587
- **Custom SMTP**: Configure according to your provider's settings

## 🛠️ Troubleshooting

### Common Issues

1. **Email not sent**: Check vendor's email address in database
2. **SMTP authentication failed**: Verify email credentials and app passwords
3. **Connection timeout**: Check firewall settings and SMTP port
4. **Email in spam**: Configure SPF, DKIM records for your domain

### Debug Mode
Enable debug logging to see email sending details:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'loggers': {
        'django.core.mail': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

## 📊 Monitoring

### Email Delivery Status
Monitor email delivery through:
- Django logs for SMTP errors
- Email provider's delivery reports
- API response notifications status

### Vendor Email Preferences
Consider adding vendor email preferences in the future:
- Email notification on/off toggle
- Email frequency settings
- Custom email templates

## 🔒 Security Considerations

1. **No-reply emails**: Use dedicated no-reply email addresses
2. **Email validation**: Validate vendor email addresses during registration
3. **Rate limiting**: Implement email rate limiting to prevent spam
4. **Content filtering**: Sanitize order data before including in emails

## 📈 Future Enhancements

- HTML email templates with styling
- Email templates customization per vendor
- Email delivery tracking and analytics
- Bulk email notifications for multiple orders
- Email attachments (receipts, invoices)
