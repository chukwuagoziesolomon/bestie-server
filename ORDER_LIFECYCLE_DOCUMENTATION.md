# 📋 Complete Order Lifecycle - From Placement to Completion

## Overview
This document outlines the complete order lifecycle in the Bestyy food delivery system, from initial placement through final completion.

---

## 🔄 Order Status Flow

### 1. **AWAITING** (New Status)
- **When**: Order created but user hasn't confirmed
- **Description**: Order is in draft state, waiting for user confirmation and special instructions
- **User Action**: Can add special instructions or confirm order
- **Next Status**: `pending` (when user confirms)

### 2. **PENDING** 
- **When**: Order confirmed by user, waiting for payment
- **Description**: Order is placed but payment not yet confirmed
- **System Action**: Payment link generated, waiting for payment confirmation
- **Next Status**: `payment_confirmed` (when payment verified)

### 3. **PAYMENT_CONFIRMED**
- **When**: Payment successfully processed
- **Description**: Payment verified, order sent to vendor
- **System Action**: Vendor notification sent, order queued for preparation
- **Next Status**: `processing` (when vendor accepts)

### 4. **PROCESSING**
- **When**: Vendor starts preparing the order
- **Description**: Vendor is cooking/preparing the food
- **System Action**: Real-time updates to customer, courier assignment begins
- **Next Status**: `ready` (when vendor marks as ready)

### 5. **READY**
- **When**: Vendor completes food preparation
- **Description**: Order is ready for pickup
- **System Action**: Courier notification sent, pickup assignment
- **Next Status**: `out_for_delivery` (when courier picks up)

### 6. **OUT_FOR_DELIVERY**
- **When**: Courier picks up order and starts delivery
- **Description**: Order is being delivered to customer
- **System Action**: Real-time tracking, customer updates
- **Next Status**: `delivered` (when courier delivers)

### 7. **DELIVERED**
- **When**: Courier delivers order to customer
- **Description**: Order delivered, waiting for customer confirmation
- **System Action**: Customer notification, receipt confirmation request
- **Next Status**: `completed` (when customer confirms receipt)

### 8. **COMPLETED**
- **When**: Customer confirms receipt
- **Description**: Order fully completed
- **System Action**: Final payments processed, ratings collected
- **Next Status**: None (final state)

---

## 🚫 Alternative End States

### **CANCELLED**
- **When**: Order cancelled by customer or system
- **Description**: Order cancelled before completion
- **Triggers**: Customer cancellation, payment failure, vendor rejection

### **REJECTED**
- **When**: Vendor rejects the order
- **Description**: Vendor cannot fulfill the order
- **Triggers**: Out of stock, vendor unavailable, delivery area issues

---

## 🔧 System Components & Responsibilities

### **WhatsApp AI Service**
- Handles initial order creation
- Manages awaiting state and special instructions
- Processes user confirmations

### **Payment System (Paystack)**
- Generates payment links
- Processes payment confirmations
- Handles payment failures

### **Vendor Management**
- Receives order notifications
- Updates order status (processing → ready)
- Manages preparation time

### **Courier Management**
- Assigns couriers to orders
- Tracks delivery progress
- Manages pickup and delivery

### **Status Tracking System**
- Monitors order progress
- Sends real-time updates
- Handles status transitions

### **Delivery Monitoring Service**
- Tracks delivery progress
- Sends customer updates
- Manages delivery timeouts

---

## 📱 Customer Experience Flow

### **Phase 1: Order Placement**
1. Customer: "I want to order egwusi"
2. System: Shows restaurants with menu items
3. Customer: Selects restaurant (types "1")
4. System: Creates awaiting order
5. System: "Is that all? Any special instructions?"
6. Customer: Provides instructions or says "No"
7. System: Finalizes order, requests delivery address

### **Phase 2: Payment & Confirmation**
1. System: Generates payment link
2. Customer: Completes payment
3. System: Confirms payment, notifies vendor
4. System: "Order confirmed! Vendor is preparing your food"

### **Phase 3: Preparation**
1. Vendor: Receives order notification
2. Vendor: Starts preparing food
3. System: Updates status to "processing"
4. System: "Your order is being prepared by [Vendor Name]"

### **Phase 4: Ready & Pickup**
1. Vendor: Marks order as ready
2. System: Assigns courier
3. System: "Your order is ready! Courier [Name] is on the way to pick it up"

### **Phase 5: Delivery**
1. Courier: Picks up order
2. System: Updates to "out for delivery"
3. System: "Your order is out for delivery! ETA: [time]"
4. Courier: Delivers to customer
5. System: "Your order has been delivered! Please confirm receipt"

### **Phase 6: Completion**
1. Customer: Confirms receipt
2. System: Marks as completed
3. System: "Order completed! Thank you for using Bestyy"

---

## ⏱️ Timing & Monitoring

### **Target Times**
- **Payment Confirmation**: < 5 minutes
- **Vendor Response**: < 10 minutes
- **Food Preparation**: 15-30 minutes
- **Delivery Time**: 20-45 minutes
- **Total Order Time**: 45-90 minutes

### **Monitoring Thresholds**
- **Warning**: 15 minutes over target
- **Critical**: 25 minutes over target
- **Timeout**: 30 minutes over target

### **Real-time Updates**
- Status changes every 5 minutes
- Customer notifications at each major milestone
- Automatic escalation for delays

---

## 🔔 Notification System

### **Customer Notifications**
- Order confirmation
- Payment confirmation
- Vendor acceptance
- Preparation start
- Ready for pickup
- Out for delivery
- Delivered
- Completion confirmation

### **Vendor Notifications**
- New order received
- Payment confirmation
- Customer special instructions
- Courier assignment
- Pickup confirmation

### **Courier Notifications**
- New delivery assignment
- Pickup location details
- Customer delivery address
- Special instructions
- Delivery completion

---

## 🛠️ Technical Implementation

### **Database Fields**
```python
# Order Model Key Fields
status = CharField(choices=STATUS_CHOICES)
payment_confirmed = BooleanField()
payment_confirmed_at = DateTimeField()
user_receipt_confirmed = BooleanField()
user_receipt_confirmed_at = DateTimeField()
special_instructions = TextField()
order_placed_at = DateTimeField()
order_ready_at = DateTimeField()
out_for_delivery_at = DateTimeField()
delivered_at = DateTimeField()
```

### **Status Transition Methods**
```python
# Order Model Methods
confirm_payment()      # pending → payment_confirmed
mark_as_ready()        # processing → ready
mark_out_for_delivery() # ready → out_for_delivery
mark_as_delivered()    # out_for_delivery → delivered
confirm_user_receipt() # delivered → completed
```

### **Monitoring Services**
- `StatusTrackingSystem`: Overall order monitoring
- `DeliveryMonitoringService`: Delivery-specific tracking
- `WhatsAppCourierNotificationService`: Courier communications
- `WhatsAppVendorNotificationService`: Vendor communications

---

## 📊 Analytics & Reporting

### **Order Metrics**
- Average preparation time
- Average delivery time
- Success rate by status
- Customer satisfaction scores
- Vendor performance metrics
- Courier performance metrics

### **Real-time Dashboard**
- Active orders by status
- Delivery progress tracking
- Performance alerts
- System health monitoring

---

## 🚨 Error Handling & Recovery

### **Payment Failures**
- Automatic retry mechanisms
- Alternative payment methods
- Customer notification and support

### **Vendor Issues**
- Automatic vendor reassignment
- Customer notification of delays
- Compensation offers

### **Delivery Issues**
- Courier reassignment
- Real-time tracking updates
- Customer communication

### **System Failures**
- Automatic status recovery
- Manual intervention capabilities
- Customer support escalation

---

## 📈 Performance Optimization

### **Efficiency Measures**
- Automated status transitions
- Real-time monitoring
- Proactive issue detection
- Customer communication automation

### **Quality Assurance**
- Status validation
- Timeout handling
- Customer feedback integration
- Continuous improvement

---

This comprehensive order lifecycle ensures a smooth, transparent, and efficient food delivery experience from placement to completion.
