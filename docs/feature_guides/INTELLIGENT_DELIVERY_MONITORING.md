# 🤖 Intelligent Delivery Monitoring System

## 🚀 Overview

The Intelligent Delivery Monitoring System uses OpenRouter LLM to provide real-time delivery tracking, automatic status updates, and intelligent customer support. The system monitors deliveries every 5 minutes, understands vendor and courier intents, and provides proactive customer updates.

## 🎯 Key Features

### ✅ **Real-Time Monitoring**
- **5-minute status checks** for all active deliveries
- **Automatic vendor/courier queries** via WhatsApp
- **Intelligent intent analysis** using OpenRouter LLM
- **Proactive customer updates** based on delivery progress

### ✅ **AI-Powered Intent Analysis**
- **Vendor Intent Detection**: ready, preparing, delay, problem, etc.
- **Courier Intent Detection**: picked_up, on_the_way, arrived, delivered, etc.
- **Customer Support**: order_status, delivery_time, complaint, etc.
- **Urgency Level Assessment**: low, medium, high, critical

### ✅ **Intelligent Customer Support**
- **Automatic response generation** using LLM
- **Context-aware responses** based on order status
- **Real-time status information** for customers
- **Escalation handling** for urgent issues

## 🔄 Complete Flow

### 1. **Order Placement & Tracking Start**
```
Customer places order → System starts delivery tracking → Initial status check
```

### 2. **5-Minute Monitoring Cycle**
```
Every 5 minutes:
├── Query vendor about order status
├── Query courier about delivery progress
├── Analyze responses using LLM
├── Update order status if needed
├── Send customer updates if required
└── Handle urgent situations
```

### 3. **Intent Analysis & Response**
```
Vendor/Courier responds → LLM analyzes intent → System takes action → Customer updated
```

### 4. **Customer Support**
```
Customer asks question → LLM generates response → Real-time status provided → Follow-up actions
```

## 📋 API Endpoints

### **Unified Webhook** - `POST /api/user/webhook/`

#### **1. Start Delivery Tracking**
```json
{
  "event_type": "delivery.monitor",
  "data": {
    "order_id": 789,
    "action": "start_tracking"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### **2. Status Check**
```json
{
  "event_type": "delivery.monitor",
  "data": {
    "order_id": 789,
    "action": "status_check"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### **3. Vendor Response Processing**
```json
{
  "event_type": "vendor.response",
  "data": {
    "order_id": 789,
    "vendor_phone": "+2348123456789",
    "response_message": "Order is ready for pickup"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### **4. Courier Response Processing**
```json
{
  "event_type": "courier.response",
  "data": {
    "order_id": 789,
    "courier_phone": "+2348123456789",
    "response_message": "Picked up order, on the way to customer"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### **5. Customer Inquiry**
```json
{
  "event_type": "customer.inquiry",
  "data": {
    "customer_message": "Where is my order?",
    "customer_id": 123,
    "order_id": 789
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## 🤖 LLM Integration

### **OpenRouter Configuration**
```python
# Settings
OPENROUTER_API_KEY = "your_openrouter_api_key"
OPENROUTER_APP_URL = "https://bestyy.com"
OPENROUTER_APP_NAME = "Bestyy Delivery Monitor"

# Model Used
MODEL = "meta-llama/llama-3.2-3b-instruct:free"
```

### **Intent Analysis Prompts**

#### **Vendor Intent Analysis**
```
Analyze this vendor message for intent and urgency:

VENDOR MESSAGE: "Order is ready for pickup"
ORDER CONTEXT: Order #789, Customer: John Doe, Elapsed Time: 12 minutes

VENDOR INTENT CATEGORIES:
- ready: Order is ready for pickup
- preparing: Still preparing the order
- delay: Need more time (specify reason)
- problem: Having issues (specify problem)

Respond with JSON:
{
    "primary_intent": "ready",
    "confidence": 0.95,
    "urgency_level": "low",
    "extracted_info": {
        "status": "ready",
        "estimated_time": "5-10 min",
        "issues": [],
        "reason": "Order preparation completed"
    },
    "action_required": "none",
    "customer_message": "Your order is ready for pickup!",
    "internal_notes": "Order ready, courier can be notified"
}
```

#### **Courier Intent Analysis**
```
Analyze this courier message for intent and urgency:

COURIER MESSAGE: "Picked up order, on the way to customer"
ORDER CONTEXT: Order #789, Customer: John Doe, Elapsed Time: 18 minutes

COURIER INTENT CATEGORIES:
- picked_up: Order has been picked up from vendor
- on_the_way: Heading to customer location
- arrived: Arrived at customer location
- delivered: Successfully delivered to customer

Respond with JSON:
{
    "primary_intent": "on_the_way",
    "confidence": 0.90,
    "urgency_level": "low",
    "extracted_info": {
        "status": "on_the_way",
        "estimated_delivery": "5-10 min",
        "issues": [],
        "reason": "Order picked up and en route"
    },
    "action_required": "none",
    "customer_message": "Your order is on its way to you!",
    "internal_notes": "Courier en route, delivery imminent"
}
```

## 📱 WhatsApp Messages

### **Vendor Status Query**
```
📋 ORDER STATUS CHECK

Order #789 - Customer: John Doe

🕐 Order Time: 10:30
⏰ Elapsed Time: 12 minutes

Please reply with your current status:
• "READY" - Order is ready for pickup
• "PREPARING" - Still preparing the order
• "DELAY" - Need more time (specify reason)
• "PROBLEM" - Having issues (specify problem)

This helps us keep customers informed. Thank you! 🙏

---
Bestyy Delivery Monitor
```

### **Courier Status Query**
```
🚚 DELIVERY STATUS CHECK

Order #789 - Customer: John Doe

🕐 Assigned Time: 10:30
⏰ Elapsed Time: 18 minutes
📍 Delivery Address: 456 Oak Avenue, Enugu

Please reply with your current status:
• "PICKED_UP" - Order picked up from vendor
• "ON_THE_WAY" - Heading to customer
• "ARRIVED" - Arrived at customer location
• "DELIVERED" - Successfully delivered
• "DELAY" - Running late (specify reason)
• "PROBLEM" - Having issues (specify problem)

This helps us keep customers informed. Thank you! 🙏

---
Bestyy Delivery Monitor
```

### **Customer Updates**

#### **Order Ready**
```
✅ Order Update - Order #789

Great news! Your order from Burger Palace is ready for pickup.

🚚 Next Step: Our courier will pick it up shortly and deliver it to you.

Thank you for your patience! 🙏

---
Bestyy Delivery Team
```

#### **On the Way**
```
🚚 Order Update - Order #789

Your order has been picked up from Burger Palace and is on its way to you!

📍 Delivery Address: 456 Oak Avenue, Enugu

We'll notify you when our courier arrives. Thank you for your patience!

---
Bestyy Delivery Team
```

#### **Delay Notification**
```
⏰ Order Update - Order #789

We apologize for the delay with your order from Burger Palace.

🕐 Current Status: Preparing
⏰ Elapsed Time: 22 minutes

We're working to get your order to you as soon as possible. Thank you for your patience.

---
Bestyy Delivery Team
```

## 🔧 Services Architecture

### **1. DeliveryMonitoringService**
- **Purpose**: Core monitoring logic
- **Key Methods**:
  - `monitor_active_deliveries()`
  - `_check_delivery_status()`
  - `_query_vendor_status()`
  - `_query_courier_status()`
  - `_analyze_status_responses()`

### **2. IntentAnalysisService**
- **Purpose**: LLM-based intent analysis
- **Key Methods**:
  - `analyze_vendor_intent()`
  - `analyze_courier_intent()`
  - `analyze_customer_support_intent()`
  - `_call_llm_for_intent_analysis()`

### **3. CustomerSupportAIService**
- **Purpose**: AI-powered customer support
- **Key Methods**:
  - `handle_customer_inquiry()`
  - `_generate_support_response()`
  - `generate_status_update_message()`
  - `handle_urgent_customer_issue()`

### **4. StatusTrackingSystem**
- **Purpose**: Comprehensive status tracking
- **Key Methods**:
  - `start_delivery_tracking()`
  - `process_status_check()`
  - `process_vendor_response()`
  - `process_courier_response()`
  - `handle_customer_inquiry()`

## ⏰ Monitoring Schedule

### **5-Minute Status Checks**
```
Order placed → Start tracking
├── 5 min: First status check
├── 10 min: Second status check
├── 15 min: Warning threshold reached
├── 20 min: Target delivery time
├── 25 min: Critical threshold
└── Continue until delivered
```

### **Urgency Levels**
- **Low (0-15 min)**: Normal monitoring
- **Medium (15-20 min)**: Increased monitoring
- **High (20-25 min)**: Warning notifications
- **Critical (25+ min)**: Immediate intervention

## 🧪 Testing

### **Test Delivery Monitoring**
```bash
curl -X POST http://localhost:8000/api/user/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "delivery.monitor",
    "data": {
      "order_id": 789,
      "action": "start_tracking"
    }
  }'
```

### **Test Vendor Response**
```bash
curl -X POST http://localhost:8000/api/user/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "vendor.response",
    "data": {
      "order_id": 789,
      "vendor_phone": "+2348123456789",
      "response_message": "Order is ready for pickup"
    }
  }'
```

### **Test Customer Inquiry**
```bash
curl -X POST http://localhost:8000/api/user/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "customer.inquiry",
    "data": {
      "customer_message": "Where is my order?",
      "customer_id": 123,
      "order_id": 789
    }
  }'
```

## 📊 Monitoring Dashboard

### **Key Metrics**
- **Active Deliveries**: Orders being tracked
- **Average Delivery Time**: Performance metric
- **Status Check Success Rate**: System reliability
- **Customer Satisfaction**: Response quality
- **LLM Response Time**: AI performance

### **Real-Time Alerts**
- **Overdue Orders**: 25+ minutes
- **Failed Status Checks**: System issues
- **High Urgency Responses**: Customer complaints
- **LLM Errors**: AI service issues

## 🚨 Error Handling

### **Common Issues**
1. **LLM API Errors**: Fallback to rule-based responses
2. **WhatsApp Delivery Failures**: Retry with email
3. **Status Check Timeouts**: Escalate to human
4. **Intent Analysis Failures**: Use default responses

### **Fallback Strategies**
- **LLM Unavailable**: Rule-based intent detection
- **WhatsApp Down**: Email notifications
- **Database Issues**: In-memory tracking
- **Service Overload**: Queue management

## 🔄 Integration Points

### **Existing Systems**
- **WhatsApp AI**: Reuses existing OpenRouter integration
- **Courier Notifications**: Extends existing courier system
- **Vendor Notifications**: Extends existing vendor system
- **WebSocket**: Real-time updates to dashboards

### **New Integrations**
- **Customer Support**: AI-powered responses
- **Status Tracking**: Real-time monitoring
- **Intent Analysis**: LLM-based understanding
- **Proactive Updates**: Automatic customer notifications

## 🚀 Key Benefits

### ✅ **For Customers**
- **Real-time updates** every 5 minutes
- **Intelligent responses** to inquiries
- **Proactive notifications** about delays
- **Transparent delivery tracking**

### ✅ **For Vendors**
- **Automated status queries** reduce manual work
- **Clear communication** with delivery team
- **Issue detection** and resolution
- **Performance monitoring**

### ✅ **For Couriers**
- **Regular status check-ins** keep them informed
- **Issue reporting** for delays or problems
- **Performance tracking** and feedback
- **Support for delivery challenges**

### ✅ **For Business**
- **15-20 minute delivery target** monitoring
- **Customer satisfaction** improvement
- **Operational efficiency** gains
- **Data-driven insights** for optimization

The Intelligent Delivery Monitoring System provides a comprehensive solution for real-time delivery tracking, intelligent customer support, and proactive issue resolution using OpenRouter LLM! 🤖✨
