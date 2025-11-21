# Paystack Automated Payments - Quick Reference

## 🎯 What Was Implemented

Automatic payment system that:
- ✅ Pays vendors when pickup code is verified by courier
- ✅ Pays couriers when delivery OTP is verified by customer  
- ✅ Uses unique references to prevent duplicate payments
- ✅ Tracks payment status via Paystack webhooks
- ✅ Calculates platform fee (10%) automatically

## 📝 Key Files

| File | Purpose |
|------|---------|
| `paystack_transfer_service.py` | Core payment automation logic |
| `order/models.py` | Transfer tracking fields & methods |
| `user/models.py` | Vendor/Courier bank account fields |
| `webhook_views.py` | Paystack webhook handler |
| `test_paystack_transfers.py` | Test script |

## 💰 Payment Formula

```
Total Order: ₦10,000
Delivery Fee: ₦1,500
Platform Fee: ₦1,000 (10% of total)

Vendor Gets:  ₦7,500 (Total - Platform Fee - Delivery Fee)
Courier Gets: ₦1,500 (Delivery Fee)
Platform Gets: ₦1,000 (10% Platform Fee)
```

## 🔄 Payment Triggers

### Vendor Payment
```python
# Triggered when courier enters pickup code
POST /api/user/orders/{id}/verify-pickup/
{"code": "ABC123"}

→ order.trigger_vendor_payout()
→ Paystack transfer initiated
→ Webhook confirms success
```

### Courier Payment
```python
# Triggered when customer enters delivery OTP
POST /api/user/orders/{id}/verify-delivery/
{"code": "123456"}

→ order.trigger_courier_payout()
→ Paystack transfer initiated
→ Webhook confirms success
```

## 🔑 Transfer References

**Format**: `{type}_{order_number}_{uuid16}`

Examples:
- `vendor_ORD123456_65be4c381bed453b`
- `courier_ORD123456_789fb2e171704fd8`

**Why unique?** Prevents double-crediting if transfer retried.

## 🏦 Bank Setup (One-Time per Vendor/Courier)

```python
from bestyy.core_features.user.services.paystack_transfer_service import PaystackTransferService

service = PaystackTransferService()

# 1. Get banks
banks = service.get_banks()

# 2. Create recipient
recipient = service.create_transfer_recipient(
    account_number='0123456789',
    bank_code='044',  # Access Bank
    name='Vendor Name'
)

# 3. Save to profile
vendor.paystack_recipient_code = recipient['recipient_code']
vendor.bank_account_number = '0123456789'
vendor.bank_code = '044'
vendor.bank_name = 'Access Bank'
vendor.save()
```

## 📊 Check Payment Status

```python
from bestyy.restaurant_features.order.models import Order

order = Order.objects.get(order_number='ORD-123')

# Vendor
print(order.vendor_paid)              # True/False
print(order.vendor_transfer_status)   # pending/processing/success/failed
print(order.vendor_transfer_code)     # TRF_xxx from Paystack
print(order.vendor_paid_at)          # Timestamp

# Courier  
print(order.courier_paid)             # True/False
print(order.courier_transfer_status)  # pending/processing/success/failed
print(order.courier_transfer_code)    # TRF_xxx from Paystack
print(order.courier_paid_at)         # Timestamp
```

## 🧪 Testing

```bash
# Run test script
python test_paystack_transfers.py

# Output shows:
# - Bank list retrieval
# - Reference generation
# - Payout calculations
# - Order payment status
```

## ⚙️ Paystack Dashboard Setup

1. Go to **Settings → API Keys & Webhooks**
2. Copy your Secret Key → Add to `.env`
3. Go to **Settings → Preferences**  
4. **Disable Transfer OTP** (required for automation)
5. Add webhook: `https://yourdomain.com/api/webhooks/paystack/transfer/`

## 🚨 Common Issues

| Issue | Solution |
|-------|----------|
| "No recipient code" | Run bank setup first |
| "Insufficient balance" | Fund Paystack account |
| "Invalid account" | Verify account number & bank code |
| "Transfer failed" | Check Paystack dashboard for details |

## 📈 Database Fields Added

### Order Model
- `vendor_transfer_reference` (unique)
- `vendor_transfer_code`
- `vendor_transfer_status`
- `vendor_paid_at`
- `courier_transfer_reference` (unique)
- `courier_transfer_code`
- `courier_transfer_status`  
- `courier_paid_at`

### VendorProfile / CourierProfile Models
- `paystack_recipient_code`
- `bank_account_number`
- `bank_code`
- `bank_name`

## 🎯 Next Implementation Tasks

1. [ ] UI for bank account registration
2. [ ] Recipient auto-creation on profile completion
3. [ ] Payment retry mechanism for failures
4. [ ] Earnings dashboard for vendors/couriers
5. [ ] Low balance alerts
6. [ ] Export payment reports

## 📞 Paystack Resources

- **Transfers API**: https://paystack.com/docs/transfers/single-transfers
- **Banks List**: https://paystack.com/docs/miscellaneous/bank-list  
- **Webhooks**: https://paystack.com/docs/payments/webhooks
- **Dashboard**: https://dashboard.paystack.com

## ✅ Verification Checklist

- [x] PaystackTransferService created
- [x] Order model updated with transfer fields
- [x] Vendor/Courier models updated with bank fields
- [x] Database migrations applied
- [x] Pickup verification triggers vendor payment
- [x] Delivery verification triggers courier payment
- [x] Webhook handler for transfer status
- [x] Unique references prevent duplicates
- [x] Test script validates functionality

---

**Status**: ✅ Implementation Complete - Ready for Testing
**Date**: November 21, 2025
