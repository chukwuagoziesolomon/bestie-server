# 📱 Vendor Notification System API

## 🚀 Overview

The vendor notification system sends real-time notifications to vendors when orders are placed through multiple channels:
- **WhatsApp** (via Twilio/WhatsApp Business API)
- **WebSocket** (real-time in-app notifications)
- **Email** (detailed order information)

## 📋 API Endpoints

### **1. Place Order (Triggers Vendor Notifications)**

**POST** `/api/user/orders/place/`

**Request Body:**
```json
{
  "cart_id": 123,
  "delivery_address_id": 456,
  "payment_method": "cash",
  "delivery_instructions": "Please call when you arrive"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Order placed successfully",
  "order": {
    "id": 789,
    "order_number": "#789",
    "status": "pending",
    "vendor": {
      "id": 3,
      "business_name": "Burger Palace",
      "logo": "https://res.cloudinary.com/.../logo.jpg",
      "delivery_time": "30-40 min"
    },
    "total_amount": 2500.00,
    "currency": "NGN",
    "payment_method": "cash",
    "delivery_address": {
      "street": "123 Main Street",
      "city": "Lagos",
      "state": "Lagos State",
      "postal_code": "100001",
      "landmark": "Near the mall"
    },
    "delivery_instructions": "Please call when you arrive",
    "order_date": "2025-09-12T16:30:00Z",
    "estimated_delivery": "2025-09-12T17:00:00Z",
    "items_count": 3
  },
  "notifications": {
    "whatsapp": {
      "success": true,
      "message": "WhatsApp notification sent to +2348123456789",
      "vendor_phone": "+2348123456789"
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
  },
  "automatic_replies": {
    "whatsapp": {
      "success": true,
      "message": "Automatic reply sent to customer",
      "reply_type": "order_confirmation"
    }
  },
  "tracking": {
    "order_id": 789,
    "tracking_url": "/orders/789/track",
    "vendor_contact": {
      "phone": "+2348123456789",
      "whatsapp": "+2348123456789"
    }
  }
}
```

## 🔔 Notification Channels

### **1. WhatsApp Notifications**

**Service**: `VendorNotificationService._send_whatsapp_notification()`

**Message Format:**
```
🍽️ *NEW ORDER NOTIFICATION*

📋 *Order Details:*
Order ID: #789
Customer: John Doe
Phone: +2348123456789

🏪 *Vendor:* Burger Palace
📍 *Address:* 123 Restaurant Street, Lagos

📦 *Order Items:*
• Classic Burger x2
  Base Price: ₦1,200.00
  Customizations:
    - Large (+₦300.00)
    - Extra Cheese (+₦150.00)
  Special Instructions: No onions
  Total: ₦1,650.00

• French Fries x1
  Base Price: ₦800.00
  Total: ₦800.00

💰 *Total Amount:* ₦2,450.00
💳 *Payment:* Cash on Delivery
📅 *Order Time:* 2025-09-12 16:30

🏠 *Delivery Address:*
123 Main Street
Lagos, Lagos State
100001
Landmark: Near the mall

📝 *Special Instructions:* Please call when you arrive

⏰ *Estimated Delivery:* 17:00 (30 minutes)

---
Bestyy - Food Delivery Platform
```

**Response:**
```json
{
  "success": true,
  "message": "WhatsApp notification sent to +2348123456789",
  "vendor_phone": "+2348123456789",
  "message_id": "msg_abc123"
}
```

### **2. WebSocket Notifications**

**Service**: `VendorNotificationService._send_websocket_notification()`

**Connection URL**: `ws://localhost:8000/ws/vendor/`

**Message Format:**
```json
{
  "type": "order.new",
  "data": {
    "order_id": 789,
    "order_number": "#789",
    "customer": {
      "name": "John Doe",
      "phone": "+2348123456789"
    },
    "items": [
      {
        "name": "Classic Burger",
        "quantity": 2,
        "base_price": 1200.00,
        "variants": [
          {
            "name": "Large",
            "price": 300.00
          },
          {
            "name": "Extra Cheese",
            "price": 150.00
          }
        ],
        "special_instructions": "No onions",
        "total_price": 1650.00
      }
    ],
    "total_amount": 2450.00,
    "delivery_address": {
      "street": "123 Main Street",
      "city": "Lagos",
      "state": "Lagos State",
      "postal_code": "100001",
      "landmark": "Near the mall"
    },
    "special_instructions": "Please call when you arrive",
    "order_time": "2025-09-12T16:30:00Z",
    "estimated_delivery": "2025-09-12T17:00:00Z",
    "timestamp": "2025-09-12T16:30:00Z"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "WebSocket notification sent successfully"
}
```

### **3. Email Notifications**

**Service**: `VendorNotificationService._send_email_notification()`

**Subject**: `New Order - Burger Palace`

**Email Body:**
```
Dear Burger Palace,

You have received a new order!

ORDER SUMMARY:
==============
Customer: John Doe
Total Amount: ₦2,450.00
Order Time: 2025-09-12 16:30:00

ORDER CONTENTS:
===============

• Classic Burger x2
  Base Price: ₦1,200.00
  Total: ₦1,650.00
  Customizations:
    - Large (+₦300.00)
    - Extra Cheese (+₦150.00)
  Special Instructions: No onions

• French Fries x1
  Base Price: ₦800.00
  Total: ₦800.00

DELIVERY ADDRESS:
================
123 Main Street
Lagos, Lagos State
100001
Landmark: Near the mall

Delivery Instructions: Please call when you arrive

PAYMENT METHOD: Cash on Delivery

Please prepare this order and confirm when ready for delivery.

Best regards,
Bestyy Team

---
This is an automated notification. Please do not reply to this email.
For support, contact us through the Bestyy platform.
```

**Response:**
```json
{
  "success": true,
  "message": "Email sent to vendor@burgerpalace.com",
  "vendor_email": "vendor@burgerpalace.com"
}
```

## 🔄 Automatic Replies

### **Service**: `AutomaticVendorReplyService.send_automatic_reply()`

**WhatsApp Auto-Reply to Customer:**
```
✅ *Order Confirmed!*

Thank you for your order at Burger Palace!

📋 *Order Details:*
Order ID: #789
Total: ₦2,450.00
Estimated Delivery: 17:00 (30 minutes)

🏪 *Vendor:* Burger Palace
📞 *Contact:* +2348123456789

Your order is being prepared. You'll receive updates on the delivery status.

Thank you for choosing Bestyy! 🍽️
```

## 🎯 Frontend Implementation

### **1. WebSocket Connection (Vendor Dashboard)**

```javascript
// Connect to vendor WebSocket
const vendorSocket = new WebSocket('ws://localhost:8000/ws/vendor/');

vendorSocket.onopen = function(event) {
    console.log('Connected to vendor notifications');
};

vendorSocket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'order.new':
            showNewOrderNotification(data.data);
            break;
        case 'connection.established':
            console.log('WebSocket connection established');
            break;
        default:
            console.log('Unknown message type:', data.type);
    }
};

function showNewOrderNotification(orderData) {
    // Show notification popup
    const notification = document.createElement('div');
    notification.className = 'order-notification';
    notification.innerHTML = `
        <div class="notification-header">
            <h3>🍽️ New Order #${orderData.order_number}</h3>
            <button onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
        <div class="notification-body">
            <p><strong>Customer:</strong> ${orderData.customer.name}</p>
            <p><strong>Total:</strong> ₦${orderData.total_amount.toLocaleString()}</p>
            <p><strong>Items:</strong> ${orderData.items.length} item(s)</p>
            <p><strong>Delivery Time:</strong> ${new Date(orderData.estimated_delivery).toLocaleTimeString()}</p>
        </div>
        <div class="notification-actions">
            <button onclick="viewOrderDetails(${orderData.order_id})">View Details</button>
            <button onclick="acceptOrder(${orderData.order_id})">Accept Order</button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 10 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 10000);
}
```

### **2. Order Status Updates**

```javascript
// Update order status
async function updateOrderStatus(orderId, newStatus) {
    try {
        const response = await fetch(`/api/user/orders/${orderId}/status/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${vendorToken}`
            },
            body: JSON.stringify({
                status: newStatus,
                notes: 'Order is being prepared'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Show success message
            showNotification('Order status updated successfully', 'success');
            
            // Update UI
            updateOrderStatusInUI(orderId, newStatus);
        } else {
            showNotification('Failed to update order status', 'error');
        }
    } catch (error) {
        console.error('Error updating order status:', error);
        showNotification('Network error occurred', 'error');
    }
}
```

## 🔧 Configuration

### **Environment Variables**

```bash
# WhatsApp Configuration
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=noreply@bestyy.com

# WebSocket Configuration
CHANNEL_LAYERS={
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
```

## 📊 Notification Status Tracking

### **Success Response Example:**
```json
{
  "notifications": {
    "whatsapp": {
      "success": true,
      "message": "WhatsApp notification sent to +2348123456789",
      "vendor_phone": "+2348123456789"
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

### **Partial Failure Example:**
```json
{
  "notifications": {
    "whatsapp": {
      "success": true,
      "message": "WhatsApp notification sent successfully"
    },
    "websocket": {
      "success": false,
      "message": "WebSocket notification failed: Channel layer not available"
    },
    "email": {
      "success": false,
      "message": "Email notification failed: SMTP server not configured"
    }
  }
}
```

## 🚀 Frontend Requirements

### **Do You Need to Implement WebSocket in Frontend?**

**YES** - You need to implement WebSocket connections in your frontend for:

1. **Real-time Order Notifications** - Vendors receive instant notifications when orders are placed
2. **Order Status Updates** - Real-time updates when customers change order status
3. **System Notifications** - Account status changes, payment notifications, etc.

### **Implementation Priority:**

1. **High Priority**: WebSocket for vendor order notifications
2. **Medium Priority**: Email notifications (automatic, no frontend needed)
3. **Low Priority**: WhatsApp notifications (automatic, no frontend needed)

### **WebSocket Benefits:**
- ✅ **Instant Notifications** - No polling required
- ✅ **Real-time Updates** - Order status changes immediately
- ✅ **Better UX** - Vendors can respond faster to orders
- ✅ **Reduced Server Load** - No constant API polling

The WebSocket implementation is essential for a smooth vendor experience! 🎉






