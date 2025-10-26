# 🚚 Courier Notification System

## 🚀 Overview

The Courier Notification System automatically assigns and notifies couriers when vendors are ready for pickup. The system uses location-based matching to find nearby couriers and sends notifications via WhatsApp, email, and WebSocket.

## 🔄 Complete Flow

### 1. **Order Placement**
- Customer places order
- Order is sent to vendor
- Vendor receives WhatsApp notification

### 2. **Vendor Ready Notification**
- Vendor types "I am ready" or similar message to WhatsApp
- System detects ready message
- Finds nearby available couriers
- Assigns best courier to order
- Sends notifications to courier

### 3. **Courier Assignment**
- Courier receives WhatsApp notification
- Courier receives email notification
- Courier receives WebSocket notification
- Order status updated to "assigned"

## 📋 API Endpoints

### **1. Unified Webhook Endpoint**

**POST** `/api/user/webhook/`

#### **Vendor Ready Event**
```json
{
  "event_type": "vendor.ready",
  "data": {
    "vendor_phone": "+2348123456789",
    "message": "I am ready for pickup"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### **WhatsApp Message Event**
```json
{
  "event_type": "whatsapp.message",
  "data": {
    "entry": [
      {
        "changes": [
          {
            "value": {
              "messages": [
                {
                  "from": "2348123456789",
                  "text": {
                    "body": "I am ready"
                  },
                  "id": "wamid.xxx",
                  "timestamp": "1642248000"
                }
              ]
            }
          }
        ]
      }
    ]
  }
}
```

### **2. Courier Assignment Response**

```json
{
  "success": true,
  "message": "Vendor ready processed successfully",
  "vendor_id": 123,
  "orders_processed": 1,
  "results": [
    {
      "success": true,
      "order_id": 789,
      "courier_id": 456,
      "courier_name": "John Doe",
      "courier_phone": "+2348123456789",
      "notifications": {
        "whatsapp": {
          "success": true,
          "message": "WhatsApp message sent to +2348123456789"
        },
        "websocket": {
          "success": true,
          "message": "WebSocket notification sent to courier 456"
        },
        "email": {
          "success": true,
          "message": "Email sent to courier@example.com"
        }
      },
      "assignment_details": {
        "distance_km": 2.5,
        "estimated_earnings": 325,
        "estimated_delivery_time": "30-45 min",
        "vehicle_type": "bike"
      }
    }
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## 🔧 Services

### **1. CourierLocationService**

Finds nearby couriers based on vendor location and service areas.

#### **Key Methods:**
- `find_nearby_couriers(vendor, max_distance_km, limit)`
- `find_couriers_by_service_area(vendor_address, limit)`
- `assign_courier_to_order(order, vendor, customer_data)`

#### **Location Matching:**
- Uses geocoding to get coordinates
- Calculates distance between vendor and courier
- Matches service areas
- Considers working hours and availability

### **2. CourierNotificationService**

Sends notifications to couriers via multiple channels.

#### **Key Methods:**
- `send_delivery_assignment(courier, order_data)`
- `send_delivery_update(courier, order_data, update_type)`

#### **Notification Channels:**
- **WhatsApp**: Delivery assignment details
- **Email**: Detailed order information
- **WebSocket**: Real-time updates

### **3. VendorReadyService**

Processes vendor ready messages and triggers courier assignment.

#### **Key Methods:**
- `process_vendor_ready_message(vendor_phone, message)`
- `handle_whatsapp_webhook(webhook_data)`

#### **Ready Message Detection:**
Keywords that trigger courier assignment:
- "ready", "done", "finished", "prepared"
- "pickup", "delivery ready", "order ready"
- "am ready", "i am ready", "we are ready"

## 📱 WhatsApp Messages

### **Courier Assignment Message**

```
🚚 NEW DELIVERY ASSIGNMENT

📋 Order Details:
Order ID: #789
Customer: John Doe
Phone: +234-123-456-7890

🏪 Pickup Location:
Burger Palace
123 Independence Layout, Enugu

📍 Delivery Location:
456 Oak Avenue, Enugu

💰 Earnings: ₦325
📏 Distance: 2.5 km
🕐 Order Time: 2025-01-15 10:30

📦 Order Items:
• Classic Beef Burger x1
  - Regular (Free)
  - Extra Cheese (+₦1500)
  📝 Note: No onions, extra spicy

🚀 Next Steps:
1. Head to pickup location
2. Confirm pickup with vendor
3. Deliver to customer
4. Confirm delivery completion

💡 Reply with:
• "ACCEPT" to accept this delivery
• "DECLINE" to decline this delivery
• "MORE INFO" for additional details

---
Bestyy Delivery System
```

### **Delivery Update Messages**

#### **Delivery Started**
```
🚚 DELIVERY STARTED

Order #789 is now out for delivery.

👤 Customer: John Doe
📍 Delivery Address: 456 Oak Avenue, Enugu

🕐 Started at: Now

Please deliver the order safely and confirm completion.

---
Bestyy Delivery System
```

#### **Delivery Completed**
```
✅ DELIVERY COMPLETED

Order #789 has been successfully delivered!

👤 Customer: John Doe
🕐 Completed at: Now
💰 Earnings: ₦325

Thank you for completing this delivery!

---
Bestyy Delivery System
```

## 📧 Email Notifications

### **Delivery Assignment Email**

**Subject**: `🚚 New Delivery Assignment - Order #789`

**Body**:
```
Hello John,

You have been assigned a new delivery!

📋 Order Details:
• Order ID: #789
• Customer: John Doe
• Phone: +234-123-456-7890

🏪 Pickup Location:
• Vendor: Burger Palace
• Address: 123 Independence Layout, Enugu

📍 Delivery Location:
• Address: 456 Oak Avenue, Enugu

💰 Estimated Earnings: ₦325
📏 Distance: 2.5 km

🚀 Next Steps:
1. Head to the pickup location
2. Confirm pickup with the vendor
3. Deliver to the customer
4. Confirm delivery completion

Please check your courier dashboard for more details.

Best regards,
Bestyy Delivery Team
```

## 🔍 Courier Selection Algorithm

### **1. Location-Based Matching**
- Calculate distance between vendor and courier
- Use geocoding to get accurate coordinates
- Consider maximum delivery radius

### **2. Service Area Matching**
- Check if courier serves vendor's area
- Match city/area names
- Fallback method if geocoding fails

### **3. Availability Check**
- Verify courier is active and not suspended
- Check working hours
- Ensure verification status is approved

### **4. Selection Criteria**
- **Primary**: Distance (closest first)
- **Secondary**: Vehicle type preference
- **Tertiary**: Historical performance

## 🛠 Configuration

### **Environment Variables**

```bash
# WhatsApp Configuration
WHATSAPP_ACCESS_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token

# Google Maps (Optional)
GOOGLE_MAPS_API_KEY=your_google_maps_key

# Email Configuration
DEFAULT_FROM_EMAIL=noreply@bestyy.com
```

### **Courier Profile Requirements**

```python
# Required fields for courier assignment
courier.is_active = True
courier.is_suspended = False
courier.verification_status = 'approved'
courier.service_areas = "Lagos, Ikeja, Victoria Island"
courier.phone = "+2348123456789"
```

## 📊 Monitoring and Analytics

### **Key Metrics**
- Courier assignment success rate
- Average assignment time
- Distance-based matching accuracy
- Notification delivery rates

### **Logging**
```python
# Log courier assignments
logger.info(f"Courier {courier.id} assigned to order {order.id}")

# Log notification results
logger.info(f"Notifications sent: {notification_result}")

# Log errors
logger.error(f"Courier assignment failed: {error}")
```

## 🧪 Testing

### **Test Vendor Ready Message**

```bash
curl -X POST http://localhost:8000/api/user/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "vendor.ready",
    "data": {
      "vendor_phone": "+2348123456789",
      "message": "I am ready for pickup"
    },
    "timestamp": "2025-01-15T10:30:00Z"
  }'
```

### **Test WhatsApp Webhook**

```bash
curl -X POST http://localhost:8000/api/user/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "whatsapp.message",
    "data": {
      "entry": [
        {
          "changes": [
            {
              "value": {
                "messages": [
                  {
                    "from": "2348123456789",
                    "text": {
                      "body": "I am ready"
                    },
                    "id": "wamid.test123",
                    "timestamp": "1642248000"
                  }
                ]
              }
            }
          ]
        }
      ]
    }
  }'
```

## 🚨 Error Handling

### **Common Errors**

| Error | Description | Solution |
|-------|-------------|----------|
| `Vendor not found` | Phone number not in database | Check vendor phone number |
| `No available courier found` | No couriers in area | Expand search radius or add couriers |
| `Message does not indicate vendor is ready` | Invalid ready message | Use proper keywords |
| `No pending orders found` | No orders to assign | Check order status |

### **Fallback Strategies**

1. **Geocoding fails**: Use service area matching
2. **No nearby couriers**: Expand search radius
3. **WhatsApp fails**: Send email notification
4. **All notifications fail**: Log error and retry

## 🔄 Integration with Existing Systems

### **Order Management**
- Updates order status to "assigned"
- Links courier to order
- Tracks assignment timestamp

### **Vendor Notifications**
- Integrates with existing vendor WhatsApp system
- Uses same webhook infrastructure
- Maintains consistent message format

### **WebSocket System**
- Sends real-time updates to courier dashboard
- Integrates with existing WebSocket consumers
- Maintains connection state

## 🚀 Key Features

### ✅ **Intelligent Matching**
- Location-based courier selection
- Service area verification
- Availability checking

### ✅ **Multi-Channel Notifications**
- WhatsApp messages with rich formatting
- Email notifications with detailed information
- WebSocket real-time updates

### ✅ **Automatic Processing**
- Vendor ready message detection
- Automatic courier assignment
- Status updates and tracking

### ✅ **Robust Error Handling**
- Fallback strategies
- Comprehensive logging
- Graceful failure handling

### ✅ **Scalable Architecture**
- Service-based design
- Configurable parameters
- Easy to extend and modify

The Courier Notification System provides a complete solution for automatic courier assignment and notification, ensuring efficient delivery operations! 🚚✨
