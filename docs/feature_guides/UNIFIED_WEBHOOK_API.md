# 🔗 Unified Webhook API Documentation

## 🚀 Overview

The Unified Webhook API provides a single endpoint for handling all types of notifications in the Bestyy platform, including verification status updates, order notifications, payment confirmations, and delivery assignments.

## 📍 Endpoint

**URL**: `POST /api/user/webhook/`  
**Authentication**: None (uses webhook signature verification)  
**Content-Type**: `application/json`

## 🔐 Security

The webhook uses HMAC-SHA256 signature verification for security. Include the signature in the `X-Webhook-Signature` header:

```
X-Webhook-Signature: sha256=<signature>
```

The signature is calculated as:
```
HMAC-SHA256(secret, payload)
```

## 📋 Request Format

### Base Payload Structure

```json
{
  "event_type": "string",
  "user_type": "string", 
  "user_id": "integer",
  "data": "object",
  "timestamp": "string (ISO 8601)"
}
```

### Required Headers

```
Content-Type: application/json
X-Webhook-Signature: sha256=<signature>
```

## 🎯 Supported Events

### 1. Verification Events

#### Vendor Verification Approved
```json
{
  "event_type": "verification.approved",
  "user_type": "vendor",
  "user_id": 123,
  "data": {},
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### Vendor Verification Rejected
```json
{
  "event_type": "verification.rejected",
  "user_type": "vendor", 
  "user_id": 123,
  "data": {
    "reason": "Business registration documents are not clear enough"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### Courier Verification Approved
```json
{
  "event_type": "verification.approved",
  "user_type": "courier",
  "user_id": 456,
  "data": {},
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### Courier Verification Rejected
```json
{
  "event_type": "verification.rejected",
  "user_type": "courier",
  "user_id": 456,
  "data": {
    "reason": "Invalid identification document"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 2. Order Events

#### Order Status Updated
```json
{
  "event_type": "order.updated",
  "user_type": "vendor",
  "user_id": 123,
  "data": {
    "order_id": 789,
    "status": "preparing",
    "message": "Order is being prepared"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### Order Assigned to Courier
```json
{
  "event_type": "order.assigned",
  "user_type": "courier",
  "user_id": 456,
  "data": {
    "order_id": 789,
    "courier_id": 456
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### Order Cancelled
```json
{
  "event_type": "order.cancelled",
  "user_type": "customer",
  "user_id": 789,
  "data": {
    "order_id": 789,
    "reason": "Customer requested cancellation"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### Order Completed
```json
{
  "event_type": "order.completed",
  "user_type": "courier",
  "user_id": 456,
  "data": {
    "order_id": 789,
    "completion_notes": "Delivered successfully"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 3. Payment Events

#### Payment Completed
```json
{
  "event_type": "payment.completed",
  "user_type": "customer",
  "user_id": 789,
  "data": {
    "order_id": 789,
    "amount": 25.99,
    "payment_method": "card",
    "transaction_id": "txn_123456789"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### Payment Failed
```json
{
  "event_type": "payment.failed",
  "user_type": "customer",
  "user_id": 789,
  "data": {
    "order_id": 789,
    "amount": 25.99,
    "payment_method": "card",
    "error": "Insufficient funds"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### Payment Refunded
```json
{
  "event_type": "payment.refunded",
  "user_type": "customer",
  "user_id": 789,
  "data": {
    "order_id": 789,
    "amount": 25.99,
    "refund_reason": "Order cancelled",
    "transaction_id": "ref_123456789"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 4. Delivery Events

#### Delivery Assigned
```json
{
  "event_type": "delivery.assigned",
  "user_type": "courier",
  "user_id": 456,
  "data": {
    "order_id": 789,
    "courier_id": 456,
    "pickup_location": "123 Main St, City",
    "delivery_location": "456 Oak Ave, City"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### Delivery Started
```json
{
  "event_type": "delivery.started",
  "user_type": "courier",
  "user_id": 456,
  "data": {
    "order_id": 789,
    "estimated_delivery_time": "2025-01-15T11:00:00Z"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### Delivery Completed
```json
{
  "event_type": "delivery.completed",
  "user_type": "courier",
  "user_id": 456,
  "data": {
    "order_id": 789,
    "delivery_notes": "Delivered to customer",
    "delivery_photo": "https://example.com/photo.jpg"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### Delivery Failed
```json
{
  "event_type": "delivery.failed",
  "user_type": "courier",
  "user_id": 456,
  "data": {
    "order_id": 789,
    "failure_reason": "Customer not available",
    "retry_attempt": 1
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## 📤 Response Format

### Success Response

```json
{
  "success": true,
  "message": "Event processed successfully",
  "timestamp": "2025-01-15T10:30:00Z",
  "data": {
    // Event-specific data
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": "Error message",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## 🔄 Event Processing

### Verification Events

When verification events are received:

1. **Approval**: Updates user verification status to `approved` and sets verification date
2. **Rejection**: Updates user verification status to `rejected` with reason
3. **Notifications**: Sends real-time notifications via WebSocket, WhatsApp, and email

### Order Events

When order events are received:

1. **Status Update**: Updates order status in database
2. **Notifications**: Sends notifications to relevant parties (vendor, courier, customer)
3. **Assignment**: Assigns courier to order and notifies courier

### Payment Events

When payment events are received:

1. **Status Update**: Updates payment status in database
2. **Notifications**: Notifies vendor of payment completion
3. **Order Processing**: Triggers order processing workflow

### Delivery Events

When delivery events are received:

1. **Status Update**: Updates delivery status in database
2. **Notifications**: Sends notifications to courier and customer
3. **Tracking**: Updates order tracking information

## 🚨 Error Handling

### Common Error Codes

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | Bad Request | Invalid payload or missing required fields |
| 403 | Forbidden | Invalid webhook signature |
| 404 | Not Found | User, order, or courier not found |
| 500 | Internal Server Error | Server processing error |

### Error Response Examples

```json
{
  "error": "Missing event_type",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

```json
{
  "error": "Invalid signature",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

```json
{
  "error": "Vendor not found",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## 🔧 Configuration

### Environment Variables

```bash
# Webhook secret for signature verification
WEBHOOK_SECRET=your_webhook_secret_here

# Enable/disable webhook signature verification
WEBHOOK_VERIFY_SIGNATURE=true
```

### Django Settings

```python
# settings.py
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '')
WEBHOOK_VERIFY_SIGNATURE = os.getenv('WEBHOOK_VERIFY_SIGNATURE', 'true').lower() == 'true'
```

## 📝 Usage Examples

### cURL Examples

#### Verification Approval
```bash
curl -X POST https://your-domain.com/api/user/webhook/ \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: sha256=your_signature" \
  -d '{
    "event_type": "verification.approved",
    "user_type": "vendor",
    "user_id": 123,
    "data": {},
    "timestamp": "2025-01-15T10:30:00Z"
  }'
```

#### Order Status Update
```bash
curl -X POST https://your-domain.com/api/user/webhook/ \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: sha256=your_signature" \
  -d '{
    "event_type": "order.updated",
    "user_type": "vendor",
    "user_id": 123,
    "data": {
      "order_id": 789,
      "status": "preparing",
      "message": "Order is being prepared"
    },
    "timestamp": "2025-01-15T10:30:00Z"
  }'
```

#### Payment Completion
```bash
curl -X POST https://your-domain.com/api/user/webhook/ \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: sha256=your_signature" \
  -d '{
    "event_type": "payment.completed",
    "user_type": "customer",
    "user_id": 789,
    "data": {
      "order_id": 789,
      "amount": 25.99,
      "payment_method": "card",
      "transaction_id": "txn_123456789"
    },
    "timestamp": "2025-01-15T10:30:00Z"
  }'
```

### JavaScript Example

```javascript
const webhookUrl = 'https://your-domain.com/api/user/webhook/';
const secret = 'your_webhook_secret';

function sendWebhook(eventType, userType, userId, data) {
  const payload = {
    event_type: eventType,
    user_type: userType,
    user_id: userId,
    data: data,
    timestamp: new Date().toISOString()
  };
  
  const signature = calculateSignature(JSON.stringify(payload), secret);
  
  fetch(webhookUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Webhook-Signature': `sha256=${signature}`
    },
    body: JSON.stringify(payload)
  })
  .then(response => response.json())
  .then(data => console.log('Webhook sent:', data))
  .catch(error => console.error('Error:', error));
}

function calculateSignature(payload, secret) {
  // Use crypto library to calculate HMAC-SHA256
  const crypto = require('crypto');
  return crypto.createHmac('sha256', secret).update(payload).digest('hex');
}

// Example usage
sendWebhook('verification.approved', 'vendor', 123, {});
sendWebhook('order.updated', 'vendor', 123, {
  order_id: 789,
  status: 'preparing',
  message: 'Order is being prepared'
});
```

## 🔍 Testing

### Test Webhook with cURL

```bash
# Test verification approval
curl -X POST http://localhost:8000/api/user/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "verification.approved",
    "user_type": "vendor",
    "user_id": 1,
    "data": {},
    "timestamp": "2025-01-15T10:30:00Z"
  }'
```

### Test with Postman

1. Set method to `POST`
2. Set URL to `http://localhost:8000/api/user/webhook/`
3. Add header: `Content-Type: application/json`
4. Add header: `X-Webhook-Signature: sha256=your_signature` (if using signature verification)
5. Add JSON body with webhook payload

## 📊 Monitoring

### Logs

The webhook endpoint logs all incoming requests and processing results:

```
[INFO] Processing webhook: verification.approved for vendor 123
[INFO] Vendor verification approved successfully
[INFO] Notifications sent via WebSocket, WhatsApp, and email
```

### Metrics

Track webhook performance:
- Request count by event type
- Success/failure rates
- Processing time
- Error rates by error type

## 🚀 Key Features

### ✅ Unified Interface
- Single endpoint for all notification types
- Consistent request/response format
- Simplified integration

### ✅ Security
- HMAC-SHA256 signature verification
- Configurable security settings
- Request validation

### ✅ Real-time Notifications
- WebSocket notifications
- WhatsApp messages
- Email notifications

### ✅ Error Handling
- Comprehensive error responses
- Detailed logging
- Graceful failure handling

### ✅ Flexibility
- Support for all event types
- Extensible data structure
- Custom event handling

The Unified Webhook API provides a robust, secure, and flexible solution for handling all types of notifications in the Bestyy platform! 🎉
