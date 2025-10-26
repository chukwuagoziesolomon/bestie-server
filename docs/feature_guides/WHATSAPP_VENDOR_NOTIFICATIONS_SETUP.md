# WhatsApp Vendor Notifications Setup Guide

## Overview

This guide explains how to set up WhatsApp notifications for vendors when orders are placed. The system automatically chooses the best service based on your environment:

- **Development (DEBUG=True)**: Uses **Twilio WhatsApp** (easier to test)
- **Production (DEBUG=False)**: Uses **WhatsApp Business API** (more robust)

## 🎯 **Automatic Service Selection**

The system intelligently chooses the WhatsApp service:

| Environment | Service Used | Reason |
|-------------|--------------|---------|
| Development | Twilio WhatsApp | Easy testing, no approval needed |
| Production | WhatsApp Business API | More reliable, better for scale |

## 🚀 **Quick Setup**

### **Step 1: Install Twilio (for development)**
```bash
# Run the setup script
python bestyy/scripts/setup_twilio.py

# Or install manually
pip install twilio
```

### **Step 2: Configure Environment Variables**

Add these to your `.env` file:

```bash
# Development (Twilio WhatsApp)
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Production (WhatsApp Business API)
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_VERIFY_TOKEN=your_verify_token_here

# Environment
DEBUG=True  # Set to False for production
```

### **Step 3: Test Your Setup**
```bash
# Check which service is being used
curl -X GET http://localhost:8000/api/user/whatsapp/config/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🔧 **Detailed Setup**

## 🚀 **Option 1: WhatsApp Business API (Production)**

### Setup Steps

#### 1. **Configure Environment Variables**

Add these to your `.env` file:

```bash
# WhatsApp Business API Configuration
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_VERIFY_TOKEN=your_verify_token_here
```

#### 2. **Get Your WhatsApp Business API Credentials**

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create a new app or use existing one
3. Add WhatsApp Business API product
4. Get your credentials:
   - **Access Token**: From your app dashboard
   - **Phone Number ID**: From WhatsApp Business API settings
   - **Verify Token**: Create your own (e.g., "bestyy_verify_2024")

#### 3. **Configure Webhook (Already Done)**

Your existing webhook at `/api/whatsapp/webhook/` is already configured for receiving messages.

#### 4. **Test WhatsApp Notifications**

```bash
# Check service configuration and which service is active
curl -X GET http://localhost:8000/api/user/whatsapp/config/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Example response:
# {
#   "success": true,
#   "environment": {
#     "is_production": false,
#     "debug_mode": true
#   },
#   "current_service": "twilio",
#   "service_preference": {
#     "development": "twilio",
#     "production": "whatsapp_business_api"
#   }
# }

# Test sending notification
curl -X POST http://localhost:8000/api/user/whatsapp/test/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_id": 1,
    "message_type": "order_notification"
  }'
```

## 🔄 **Option 2: Twilio WhatsApp (Alternative)**

### Setup Steps

#### 1. **Configure Environment Variables**

Add these to your `.env` file:

```bash
# Twilio WhatsApp Configuration
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

#### 2. **Get Twilio Credentials**

1. Sign up at [Twilio](https://www.twilio.com/)
2. Get your Account SID and Auth Token from dashboard
3. Set up WhatsApp sandbox or business number

#### 3. **Install Twilio SDK**

```bash
pip install twilio
```

## 📱 **How It Works**

### When an Order is Placed:

1. **User places order** → Order created in database
2. **System gets vendor's WhatsApp number** → From vendor profile
3. **WhatsApp notification sent** → Using Business API or Twilio
4. **Automatic reply sent** → Confirmation message to vendor
5. **WebSocket notification** → Real-time update to vendor dashboard

### WhatsApp Message Example:

```
🍽️ NEW ORDER NOTIFICATION

📋 Order Details:
Order ID: #123
Customer: John Doe
Phone: +234-123-456-7890

🏪 Vendor: Burger Palace
📍 Address: 123 Independence Layout, Enugu

📦 Order Items:
• Classic Beef Burger x1 - ₦4000
  - Regular (Free)
  - Extra Cheese (+₦1500)
  📝 Note: No onions, extra spicy

💰 Total Amount: ₦4000
🕐 Order Time: 2024-01-15 10:30
🚚 Delivery Time: 15-25 min

Please prepare this order and confirm when ready for delivery.

Thank you! 🙏
```

### Automatic Reply Example:

```
🤖 AUTOMATIC REPLY - ORDER CONFIRMATION

✅ Order #123 has been automatically confirmed and added to your queue.

📋 Quick Summary:
• Customer: John Doe
• Total: ₦4000
• Items: 1 item(s)
• Time: 10:30

🚀 Next Steps:
1. Check your vendor dashboard for full details
2. Start preparing the order
3. Update status when ready

💡 Tip: Reply with "READY" when order is prepared, or "DELAY" if you need more time.

---
This is an automatic message from Bestyy Order Management System
```

## 🛠 **API Endpoints**

### Test WhatsApp Configuration
**GET** `/api/user/whatsapp/config/`

```json
{
  "success": true,
  "configuration": {
    "whatsapp_business_api": {
      "access_token_configured": true,
      "phone_number_id_configured": true,
      "verify_token_configured": true
    },
    "twilio_whatsapp": {
      "account_sid_configured": false,
      "auth_token_configured": false,
      "whatsapp_from_configured": false
    }
  },
  "available_services": {
    "whatsapp_business_api": true,
    "twilio_whatsapp": false
  },
  "recommended_service": "whatsapp_business_api"
}
```

### Test WhatsApp Notification
**POST** `/api/user/whatsapp/test/`

```json
{
  "vendor_id": 1,
  "message_type": "order_notification"
}
```

Or test with specific phone number:

```json
{
  "phone_number": "+234-123-456-7890",
  "message_type": "automatic_reply"
}
```

## 🔧 **Vendor Setup**

### Add WhatsApp Number to Vendor Profile

Vendors need to add their WhatsApp number to their profile:

```python
# In vendor profile
vendor.whatsapp_number = "+234-123-456-7890"
vendor.save()
```

### Vendor Profile Fields

The system looks for WhatsApp number in this order:
1. `vendor.whatsapp_number`
2. `vendor.contact_phone`
3. `vendor.user.phone`

## 📋 **Complete Flow**

### 1. **Order Placement**
```python
# When user places order
POST /api/user/orders/place/
{
  "cart_id": 1,
  "delivery_address_id": 5,
  "payment_method": "cash"
}
```

### 2. **Automatic Notifications Sent**
- ✅ WhatsApp notification to vendor
- ✅ Automatic reply to vendor
- ✅ WebSocket notification to vendor dashboard
- ✅ Order confirmation to customer

### 3. **Vendor Response Options**
- Vendor can reply via WhatsApp
- Vendor can update order status via API
- Vendor can view details in dashboard

## 🚨 **Troubleshooting**

### Common Issues

#### 1. **"WhatsApp configuration not available"**
- Check your `.env` file has correct credentials
- Verify API tokens are valid
- Test with `/api/user/whatsapp/config/`

#### 2. **"Vendor WhatsApp number not available"**
- Ensure vendor has `whatsapp_number` or `contact_phone` set
- Check phone number format (should include country code)

#### 3. **"WhatsApp API error: 400"**
- Phone number format incorrect
- Message content too long
- Invalid access token

#### 4. **Messages not delivered**
- Check WhatsApp Business API status
- Verify phone number is registered on WhatsApp
- Check webhook configuration

### Testing Commands

```bash
# Check configuration
curl -X GET http://localhost:8000/api/user/whatsapp/config/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test with vendor ID
curl -X POST http://localhost:8000/api/user/whatsapp/test/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"vendor_id": 1}'

# Test with phone number
curl -X POST http://localhost:8000/api/user/whatsapp/test/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+234-123-456-7890"}'
```

## 📊 **Monitoring**

### Check Notification Status

After placing an order, check the response:

```json
{
  "success": true,
  "message": "Order placed successfully",
  "notifications": {
    "whatsapp": {
      "success": true,
      "message": "WhatsApp notification sent successfully",
      "message_id": "wamid.xxx"
    },
    "websocket": {
      "success": true,
      "message": "WebSocket notification sent successfully"
    }
  },
  "automatic_replies": {
    "whatsapp": {
      "success": true,
      "message": "Automatic WhatsApp reply sent successfully",
      "message_id": "wamid.yyy"
    },
    "websocket": {
      "success": true,
      "message": "Automatic WebSocket reply sent successfully"
    }
  }
}
```

## 🎯 **Best Practices**

1. **Always test** with `/api/user/whatsapp/test/` before going live
2. **Monitor message delivery** status
3. **Keep messages concise** (WhatsApp has character limits)
4. **Use emojis** for better readability
5. **Include essential info** only (order ID, customer, items, total)
6. **Provide clear next steps** for vendors

## 🔐 **Security**

- Never expose API tokens in frontend code
- Use environment variables for all credentials
- Validate phone numbers before sending
- Implement rate limiting for WhatsApp API calls
- Log all notification attempts for debugging

This setup ensures vendors get instant WhatsApp notifications when orders are placed, with automatic replies for confirmation! 📱✅
