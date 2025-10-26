# Paystack Conditional Payment Integration API Documentation

## Overview

This document outlines the API endpoints for Bestyy's conditional Paystack payment system. The system enables customers to pay for food orders with automatic payouts to vendors and couriers upon code verification.

## Authentication

All endpoints require authentication via Bearer token:
```
Authorization: Bearer <user_token>
```

## Payment Flow

1. Customer places order
2. Customer initializes payment (full amount charged)
3. Paystack processes payment
4. Webhook confirms payment and generates codes
5. Vendor verifies pickup code → gets paid
6. Courier verifies delivery code → gets paid
7. Platform retains commission

## Endpoints

### 1. Initialize Order Payment

**Endpoint:** `POST /api/user/orders/{order_id}/initialize-payment/`

**Description:** Initializes payment for an existing order with conditional payouts to vendor and courier.

**Authentication:** Required (Customer/User)

**Request Body:** None required

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Payment initialized successfully",
  "payment": {
    "reference": "order_123_1698765432",
    "authorization_url": "https://checkout.paystack.com/xyz123",
    "total_amount": 7500.00,
    "breakdown": {
      "vendor_amount": 5000.00,
      "courier_amount": 1500.00,
      "platform_commission": 1000.00
    }
  },
  "order": {
    "id": 123,
    "status": "pending"
  }
}
```

**Response (Error - 400/500):**
```json
{
  "success": false,
  "error": "Payment already confirmed for this order"
}
```

**Frontend Integration:**
```javascript
const initializePayment = async (orderId) => {
  try {
    const response = await fetch(`/api/user/orders/${orderId}/initialize-payment/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'application/json'
      }
    });

    const data = await response.json();

    if (data.success) {
      // Initialize Paystack checkout
      const handler = PaystackPop.setup({
        key: process.env.REACT_APP_PAYSTACK_PUBLIC_KEY,
        email: user.email,
        amount: data.payment.total_amount * 100, // Convert to kobo
        ref: data.payment.reference,
        onClose: () => {
          setPaymentStatus('cancelled');
        },
        callback: (response) => {
          setPaymentStatus('processing');
          navigate(`/orders/${orderId}/track`);
        }
      });

      handler.openIframe();
    }
  } catch (error) {
    setError('Payment initialization failed');
  }
};
```

---

### 2. Verify Pickup Code (Vendor)

**Endpoint:** `POST /api/user/orders/{order_id}/verify-pickup/`

**Description:** Vendor verifies pickup code after courier collects the order, triggering vendor payout.

**Authentication:** Required (Vendor)

**Request Body:**
```json
{
  "code": "A1B2C3"
}
```

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Pickup code verified successfully",
  "payout_triggered": true,
  "order": {
    "id": 123,
    "status": "out_for_delivery",
    "vendor_paid": true
  }
}
```

**Response (Error - 400):**
```json
{
  "success": false,
  "error": "Invalid pickup code"
}
```

**Frontend Integration (Vendor App):**
```jsx
const VendorPickupVerification = ({ orderId }) => {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);

  const verifyPickup = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/user/orders/${orderId}/verify-pickup/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${vendorToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code })
      });

      const data = await response.json();
      if (data.success) {
        setPaymentStatus('vendor_paid');
        showSuccess('Pickup confirmed - payment processed');
      }
    } catch (error) {
      setError('Invalid pickup code');
    }
    setLoading(false);
  };

  return (
    <div className="pickup-verification">
      <h3>Confirm Courier Pickup</h3>
      <input
        type="text"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="Enter pickup code"
      />
      <button onClick={verifyPickup} disabled={loading}>
        {loading ? 'Verifying...' : 'Confirm Pickup'}
      </button>
    </div>
  );
};
```

---

### 3. Verify Delivery Code (Courier)

**Endpoint:** `POST /api/user/orders/{order_id}/verify-delivery/`

**Description:** Courier verifies delivery code provided by customer, triggering courier payout and order completion.

**Authentication:** Required (Courier)

**Request Body:**
```json
{
  "code": "X9Y8Z7"
}
```

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Delivery code verified successfully",
  "payout_triggered": true,
  "order": {
    "id": 123,
    "status": "completed",
    "courier_paid": true
  }
}
```

**Response (Error - 400):**
```json
{
  "success": false,
  "error": "Invalid delivery code"
}
```

**Frontend Integration (Courier App):**
```jsx
const CourierDeliveryVerification = ({ orderId }) => {
  const [code, setCode] = useState('');

  const verifyDelivery = async () => {
    try {
      const response = await fetch(`/api/user/orders/${orderId}/verify-delivery/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${courierToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code })
      });

      const data = await response.json();
      if (data.success) {
        setOrderStatus('completed');
        showSuccess('Delivery confirmed - payment received');
      }
    } catch (error) {
      setError('Invalid delivery code');
    }
  };

  return (
    <div className="delivery-verification">
      <h3>Confirm Delivery</h3>
      <p>Ask customer for delivery code:</p>
      <input
        type="text"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="Enter delivery code"
      />
      <button onClick={verifyDelivery}>Confirm Delivery</button>
    </div>
  );
};
```

---

### 4. Get Order Status

**Endpoint:** `GET /api/user/orders/{order_id}/`

**Description:** Get current order status including payment stages.

**Authentication:** Required (Order owner)

**Response (Success - 200):**
```json
{
  "id": 123,
  "status": "completed",
  "payment_confirmed": true,
  "vendor_paid": true,
  "courier_paid": true,
  "pickup_code": "A1B2C3",
  "pickup_code_verified": true,
  "vendor_payout_amount": 5000.00,
  "courier_payout_amount": 1500.00,
  "platform_commission": 1000.00,
  "total_price": 7500.00
}
```

**Frontend Integration (Order Tracking):**
```jsx
const OrderTracker = ({ orderId }) => {
  const [order, setOrder] = useState(null);

  useEffect(() => {
    const fetchOrder = async () => {
      const response = await fetch(`/api/user/orders/${orderId}/`, {
        headers: { 'Authorization': `Bearer ${userToken}` }
      });
      const data = await response.json();
      setOrder(data);
    };

    fetchOrder();
    const interval = setInterval(fetchOrder, 5000);
    return () => clearInterval(interval);
  }, [orderId]);

  const getStatusDisplay = (status) => {
    const statusMap = {
      'pending': '⏳ Order Placed',
      'payment_confirmed': '💰 Payment Confirmed',
      'ready': '🍽️ Order Ready',
      'out_for_delivery': '🚚 Out for Delivery',
      'delivered': '📦 Delivered',
      'completed': '✅ Completed'
    };
    return statusMap[status] || status;
  };

  return (
    <div className="order-tracker">
      <h3>Order Status: {getStatusDisplay(order?.status)}</h3>

      <div className="payment-status">
        <div className={`status-item ${order?.payment_confirmed ? 'completed' : 'pending'}`}>
          💳 Payment: {order?.payment_confirmed ? 'Confirmed' : 'Pending'}
        </div>
        <div className={`status-item ${order?.vendor_paid ? 'completed' : 'pending'}`}>
          👨‍🍳 Vendor: {order?.vendor_paid ? 'Paid' : 'Pending Pickup'}
        </div>
        <div className={`status-item ${order?.courier_paid ? 'completed' : 'pending'}`}>
          🚚 Courier: {order?.courier_paid ? 'Paid' : 'Pending Delivery'}
        </div>
      </div>
    </div>
  );
};
```

## Webhook Events

### Charge Success (Payment Confirmation)

**Event:** `charge.success`

**Description:** Triggered when customer payment is successful. Automatically generates verification codes.

**Payload:**
```json
{
  "event": "charge.success",
  "data": {
    "reference": "order_123_1698765432",
    "amount": 750000, // in kobo
    "metadata": {
      "order_id": 123,
      "vendor_amount": 500000,
      "courier_amount": 150000,
      "platform_commission": 100000
    }
  }
}
```

### Transfer Success (Payout Confirmation)

**Event:** `transfer.success`

**Description:** Triggered when vendor or courier payout is completed.

**Payload:**
```json
{
  "event": "transfer.success",
  "data": {
    "reference": "vendor_payout_123_1698765432",
    "amount": 500000, // in kobo
    "recipient": {
      "name": "Vendor Name"
    }
  }
}
```

## Payment Methods Supported

- 💳 **Debit/Credit Cards** (Visa, Mastercard, Verve)
- 📱 **Mobile Money** (MTN Mobile Money, Airtel Money, Glo, 9Mobile)
- 🏦 **Bank Transfers** (Direct bank transfers via Paystack)

## Error Handling

### Common Error Codes

- `400 Bad Request`: Invalid request data or order not found
- `401 Unauthorized`: Invalid or missing authentication
- `403 Forbidden`: User doesn't have permission for this action
- `404 Not Found`: Order or resource not found
- `500 Internal Server Error`: Server-side processing error

### Error Response Format

```json
{
  "success": false,
  "error": "Descriptive error message",
  "code": "ERROR_CODE" // Optional
}
```

## Frontend Components Needed

### 1. Payment Method Selector
```jsx
const PaymentMethods = ({ onMethodSelect }) => (
  <div className="payment-methods">
    <button onClick={() => onMethodSelect('card')}>💳 Card</button>
    <button onClick={() => onMethodSelect('mobile_money')}>📱 Mobile Money</button>
    <button onClick={() => onMethodSelect('bank_transfer')}>🏦 Bank Transfer</button>
  </div>
);
```

### 2. Payment Summary Display
```jsx
const PaymentSummary = ({ breakdown }) => (
  <div className="payment-summary">
    <div>Food Amount: ₦{breakdown.vendor_amount}</div>
    <div>Delivery Fee: ₦{breakdown.courier_amount}</div>
    <div>Platform Fee: ₦{breakdown.platform_commission}</div>
    <hr />
    <div>Total: ₦{breakdown.total_amount}</div>
  </div>
);
```

### 3. Code Input Components
```jsx
const CodeInput = ({ label, onVerify }) => {
  const [code, setCode] = useState('');

  return (
    <div className="code-input">
      <label>{label}</label>
      <input
        type="text"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="Enter code"
      />
      <button onClick={() => onVerify(code)}>Verify</button>
    </div>
  );
};
```

## Security Considerations

- All endpoints require authentication
- Paystack webhook signatures are verified
- Codes expire after verification
- User permissions are enforced for each action
- Payment amounts are validated server-side

## Testing

Use Paystack test keys for development:
- Public Key: `pk_test_xxx`
- Secret Key: `sk_test_xxx`

Test payment methods:
- Cards: Use test card numbers from Paystack docs
- Mobile Money: Use test phone numbers
- Bank Transfer: Use demo bank details

## Production Deployment

1. Replace test keys with live Paystack keys
2. Configure webhook URL in Paystack dashboard
3. Set up proper error monitoring
4. Enable webhook signature verification
5. Test with small amounts first

## Support

For issues with payment integration:
- Check Paystack dashboard for transaction logs
- Verify webhook delivery in application logs
- Test with Paystack's API documentation
- Contact Paystack support for payment-specific issues