# Paystack Webhook Integration for Payment Confirmation

## Overview
Integrated Paystack webhooks to automatically verify and confirm payments when customers send money via bank transfer, card, or other payment methods.

## What Was Done

### 1. Enhanced Webhook Handler (`paystack_webhooks.py`)

#### Added `bank.transfer.rejected` Event Handler
- Handles cases where customers send incorrect amounts
- Handles transactions flagged by Paystack's fraud system
- Automatically notifies customers via WhatsApp about the rejection
- Adds rejection notes to the order

#### Improved `charge.success` Event Handler
- Automatically sets `payment_confirmed = True` when payment is received
- Sets `payment_confirmed_at` timestamp
- Updates `payment_status` to `True`
- Stores payment reference
- Logs payment channel (bank_transfer, card, ussd, etc.)
- Prevents duplicate payment confirmations
- Sends WhatsApp notifications to vendor and courier
- Sends payment receipt to customer
- Triggers courier assignment
- Broadcasts payment confirmation via WebSocket

### 2. Payment Confirmation Flow

```python
# When Paystack receives payment:
1. Paystack sends webhook POST to: /api/user/webhooks/paystack/
2. Webhook verifies signature (security)
3. Extracts payment data (amount, reference, channel)
4. Finds order by reference (e.g., "order_123")
5. Sets order.payment_confirmed = True
6. Sets order.payment_confirmed_at = now()
7. Saves order
8. Sends notifications (WhatsApp, WebSocket)
9. Assigns courier
```

## Webhook Events Handled

| Event | Description | Action |
|-------|-------------|--------|
| `charge.success` | Payment received successfully | Confirm payment, notify all parties, assign courier |
| `bank.transfer.rejected` | Transfer rejected (wrong amount/fraud) | Notify customer, add note to order |

## Setup Instructions

### 1. Configure Webhook URL in Paystack Dashboard

1. Go to [Paystack Dashboard](https://dashboard.paystack.com/)
2. Navigate to: **Settings** → **Webhooks**
3. Set webhook URL to: `https://your-domain.com/api/user/webhooks/paystack/`
4. Copy your **Secret Key** from Paystack

### 2. Set Environment Variable

Add to your `.env` file:
```bash
PAYSTACK_SECRET_KEY=sk_live_your_secret_key_here
```

### 3. Test the Webhook

#### Using Paystack Test Mode:
1. Use test secret key: `sk_test_...`
2. Make a test payment
3. Check your logs for: `✅ Payment confirmed for Order #...`

#### Using Local Testing (ngrok):
```bash
# Start ngrok
ngrok http 8000

# Update Paystack webhook URL to ngrok URL
https://your-ngrok-url.ngrok.io/api/user/webhooks/paystack/

# Make a test payment
# Check terminal logs
```

## Example Webhook Payloads

### charge.success (Bank Transfer)
```json
{
  "event": "charge.success",
  "data": {
    "id": 3104021987,
    "status": "success",
    "reference": "order_123",
    "amount": 2500000,
    "channel": "bank_transfer",
    "currency": "NGN",
    "paid_at": "2023-09-12T13:29:09.000Z",
    "authorization": {
      "channel": "bank_transfer",
      "sender_name": "John Doe",
      "sender_bank_account_number": "0123456789"
    },
    "customer": {
      "email": "customer@example.com"
    }
  }
}
```

### bank.transfer.rejected
```json
{
  "event": "bank.transfer.rejected",
  "data": {
    "reference": "order_123",
    "amount": 2400000,
    "gateway_response": "Incorrect amount sent",
    "customer": {
      "email": "customer@example.com"
    }
  }
}
```

## Order Payment Confirmation Process

### Before Payment:
```python
order.payment_confirmed = False
order.payment_confirmed_at = None
order.payment_status = False
order.payment_reference = None
```

### After Webhook Receives `charge.success`:
```python
order.payment_confirmed = True
order.payment_confirmed_at = datetime.now()
order.payment_status = True
order.payment_reference = "order_123_xyz"
order.payment_method = "Paystack bank_transfer"
```

## Revenue Calculation Impact

Now that payments are automatically confirmed:

```python
# Revenue calculations will include this order:
confirmed_orders = Order.objects.filter(payment_confirmed=True)

# Total revenue from confirmed payments only
total_revenue = confirmed_orders.aggregate(
    total=Sum('total_amount')
)['total']
```

## Notifications Sent

### 1. Customer (via WhatsApp)
- ✅ Payment receipt with order details
- ⚠️  Rejection notification (if payment rejected)

### 2. Vendor (via WhatsApp)
- 🍽️ New order notification with pickup code
- Order details and customer info

### 3. Courier (via WhatsApp)
- 🚴 Delivery assignment with OTP
- Pickup and delivery addresses

### 4. Real-time (via WebSocket)
- Payment confirmation broadcast
- Order status updates

## Security

### Webhook Signature Verification
The webhook verifies Paystack signatures to prevent fraud:

```python
def verify_paystack_signature(request):
    paystack_signature = request.headers.get('x-paystack-signature')
    secret = settings.PAYSTACK_SECRET_KEY
    
    computed_signature = hmac.new(
        secret.encode('utf-8'),
        request.body,
        hashlib.sha512
    ).hexdigest()
    
    return hmac.compare_digest(paystack_signature, computed_signature)
```

**In production:** Always verify signatures (DEBUG=False)  
**In development:** Signature check is skipped (DEBUG=True)

## Testing

### Test Webhook Locally:
```bash
# 1. Start Django server
python manage.py runserver

# 2. Use curl to simulate webhook
curl -X POST http://localhost:8000/api/user/webhooks/paystack/ \
  -H "Content-Type: application/json" \
  -d '{
    "event": "charge.success",
    "data": {
      "reference": "order_5",
      "amount": 2500000,
      "channel": "bank_transfer",
      "status": "success",
      "paid_at": "2025-11-20T12:00:00Z"
    }
  }'

# 3. Check order payment_confirmed status
python manage.py shell
>>> from bestyy.restaurant_features.order.models import Order
>>> order = Order.objects.get(id=5)
>>> print(f"Payment confirmed: {order.payment_confirmed}")
>>> print(f"Confirmed at: {order.payment_confirmed_at}")
```

## Monitoring

### Check Webhook Logs:
```python
import logging
logger = logging.getLogger(__name__)

# Logs to watch for:
# ✅ "Payment confirmed for Order #123"
# ⚠️  "Bank transfer rejected for reference order_123"
# 💰 "Payment received via bank_transfer"
# 🚴 "Assigned courier to order 123"
```

### Verify in Dashboard:
```bash
# Check Paystack dashboard
https://dashboard.paystack.com/transactions

# Check your admin dashboard
http://your-domain.com/api/admin/dashboard/stats/
# Revenue should now show only confirmed payments
```

## Troubleshooting

### Webhook not receiving events?
1. Check Paystack Dashboard → Webhooks → Event logs
2. Verify webhook URL is correct
3. Ensure server is publicly accessible (use ngrok for local testing)

### Payment confirmed but no notifications?
1. Check WhatsApp service is configured
2. Verify phone numbers are valid
3. Check application logs for errors

### Duplicate payment confirmations?
- Webhook handler checks `if not order.payment_confirmed:` to prevent duplicates
- Safe to receive same webhook multiple times

## Next Steps

1. **Test in Production:**
   - Switch to live Paystack keys
   - Update webhook URL to production domain
   - Monitor first few real payments

2. **Monitor Revenue:**
   - Check admin dashboard shows correct revenue
   - Verify only confirmed payments count
   - Test vendor/courier earnings calculations

3. **Customer Experience:**
   - Ensure customers receive payment receipts
   - Verify rejection notifications work
   - Test courier assignment after payment
