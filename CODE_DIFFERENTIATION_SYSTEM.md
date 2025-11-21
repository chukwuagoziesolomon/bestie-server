# Code Differentiation System - WhatsApp Bot

## 🎯 Problem Solved

Previously, all codes were 6-character/digit format, causing confusion:
- WhatsApp verification codes: `123456`
- Pickup codes: `A1B2C3`
- Delivery OTPs: `789012`

**The bot couldn't differentiate between them!**

---

## ✅ Solution: Prefixed Codes

### Code Types and Formats

| Code Type | Format | Example | Used By | Purpose |
|-----------|--------|---------|---------|---------|
| **WhatsApp Verification** | `XXXXXX` | `123456` | New users | Account verification |
| **Pickup Code** | `PK-XXXXXX` | `PK-A1B2C3` | Vendors | Confirm courier pickup → Pay vendor |
| **Delivery OTP** | `DL-XXXXXX` | `DL-789012` | Couriers | Confirm delivery → Pay courier |

---

## 🔧 Implementation Details

### 1. Pickup Code Generation

```python
# In Order.generate_pickup_code()
code_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
code = f"PK-{code_part}"  # e.g., PK-A1B2C3

# Stored in database: order.pickup_code = "PK-A1B2C3"
```

**Example generated codes:**
- `PK-A1B2C3`
- `PK-XY7890`
- `PK-4K9M2N`

### 2. Delivery OTP Generation

```python
# In Order.generate_delivery_otp()
otp_part = ''.join(random.choices('0123456789', k=6))
otp = f"DL-{otp_part}"  # e.g., DL-123456

# Stored in database: order.delivery_otp = "DL-123456"
```

**Example generated OTPs:**
- `DL-123456`
- `DL-789012`
- `DL-456789`

### 3. WhatsApp Verification Code (Unchanged)

```python
# Remains as plain 6-digit code
verification_code = '123456'  # No prefix
```

---

## 🤖 WhatsApp Bot Detection Logic

### How the Bot Identifies Each Code Type

```python
# 1. PICKUP CODE Detection (for Vendors)
if user_role == 'vendor':
    if content.startswith('PK-'):
        # Definitely a pickup code
        → Process pickup verification
        → Trigger vendor payout
    elif len(content) == 6 and is_alphanumeric:
        # Could be pickup code without prefix (backward compatible)
        → Search for matching order
        → If found, process as pickup code

# 2. DELIVERY OTP Detection (for Couriers)
if user_role == 'courier':
    if content.startswith('DL-'):
        # Definitely a delivery OTP
        → Process delivery verification
        → Trigger courier payout
    elif len(content) == 6 and is_digits:
        # Could be delivery OTP without prefix (backward compatible)
        → Search for matching order
        → If found, process as delivery OTP

# 3. WHATSAPP VERIFICATION Code (for New Users)
if user_role is None or not verified:
    if len(content) == 6 and is_digits and not prefixed:
        # Likely WhatsApp verification code
        → Call verification endpoint
        → Create user account
```

---

## 💬 User Experience Examples

### Scenario 1: Vendor Receiving Pickup Code

**System sends to vendor:**
```
📦 Order Ready for Pickup!

Order: ORD-20251121-00123
Pickup Code: PK-A1B2C3

Show this code to the courier.
When they pick up, enter the code here to confirm.
```

**Vendor enters in WhatsApp:**
```
Vendor → PK-A1B2C3
Bot → ✅ Pickup Code Verified!
      💰 Your Payout: ₦9,000
      💸 Payment initiated!
```

**Backward compatible (without prefix):**
```
Vendor → A1B2C3
Bot → ✅ Pickup Code Verified!
      (Bot automatically adds PK- prefix)
```

### Scenario 2: Courier Receiving Delivery OTP

**System sends to courier:**
```
📦 Order Out for Delivery!

Order: ORD-20251121-00123
Delivery OTP: DL-789012

Customer will provide this code upon delivery.
Enter it here to confirm delivery.
```

**Courier enters in WhatsApp:**
```
Courier → DL-789012
Bot → ✅ Delivery Confirmed!
      💰 Your Payout: ₦1,500
      💸 Payment initiated!
```

**Backward compatible (without prefix):**
```
Courier → 789012
Bot → ✅ Delivery Confirmed!
      (Bot automatically adds DL- prefix)
```

### Scenario 3: New User Verification

**System sends to new user:**
```
Welcome to Bestyy!
Your verification code is: 123456

Reply with this code to verify your account.
```

**User enters in WhatsApp:**
```
User → 123456
Bot → ✅ Account verified!
      Welcome to Bestyy!
```

---

## 🔍 Code Verification Methods

### Method 1: `verify_pickup_code(code)`

```python
def verify_pickup_code(self, code):
    """
    Accepts:
    - PK-A1B2C3 (with prefix)
    - A1B2C3 (without prefix - auto-adds PK-)
    
    Returns: True if code matches, False otherwise
    """
    if not self.pickup_code:
        return False
    
    # Normalize input - add prefix if not present
    if not code.upper().startswith('PK-'):
        code = f"PK-{code.upper()}"
    
    return self.pickup_code.upper() == code.upper()
```

**Examples:**
```python
# Database has: pickup_code = "PK-A1B2C3"

order.verify_pickup_code("PK-A1B2C3")  # ✅ True
order.verify_pickup_code("pk-a1b2c3")  # ✅ True (case insensitive)
order.verify_pickup_code("A1B2C3")     # ✅ True (auto-adds prefix)
order.verify_pickup_code("a1b2c3")     # ✅ True (case insensitive)
order.verify_pickup_code("PK-WRONG")   # ❌ False
order.verify_pickup_code("WRONG")      # ❌ False
```

### Method 2: `verify_delivery_otp(otp)`

```python
def verify_delivery_otp(self, otp):
    """
    Accepts:
    - DL-123456 (with prefix)
    - 123456 (without prefix - auto-adds DL-)
    
    Returns: True if OTP matches, False otherwise
    """
    if not self.delivery_otp:
        return False
    
    # Normalize input - add prefix if not present
    if not otp.upper().startswith('DL-'):
        otp = f"DL-{otp.upper()}"
    
    return self.delivery_otp.upper() == otp.upper()
```

**Examples:**
```python
# Database has: delivery_otp = "DL-123456"

order.verify_delivery_otp("DL-123456")  # ✅ True
order.verify_delivery_otp("dl-123456")  # ✅ True (case insensitive)
order.verify_delivery_otp("123456")     # ✅ True (auto-adds prefix)
order.verify_delivery_otp("DL-WRONG")   # ❌ False
order.verify_delivery_otp("WRONG")      # ❌ False
```

---

## 🔄 WhatsApp Bot Flow Diagram

```
User sends message to WhatsApp
        ↓
Is user verified?
    ↓                    ↓
   YES                   NO
    ↓                    ↓
Check user role    Is 6-digit code?
    ↓                    ↓
┌───────────┐           YES → WhatsApp Verification
│  VENDOR   │            ↓
└───────────┘       Call /verify-whatsapp-signup/
     ↓                   ↓
Starts with PK-?    Create user account
     ↓
    YES → PICKUP CODE
     ↓
Search for order with pickup_code
     ↓
Found? → Verify code
     ↓
✅ Success → Trigger vendor payout
     ↓
Send ₦X,XXX to vendor's bank


┌───────────┐
│  COURIER  │
└───────────┘
     ↓
Starts with DL-?
     ↓
    YES → DELIVERY OTP
     ↓
Search for order with delivery_otp
     ↓
Found? → Verify OTP
     ↓
✅ Success → Trigger courier payout
     ↓
Send ₦X,XXX to courier's bank
```

---

## 🧪 Testing Different Code Types

### Test 1: WhatsApp Verification (New User)

```python
# User not in database
POST /whatsapp/webhook
{
    "from": "+2348012345678",
    "message": "123456"
}

# Bot Response:
✅ Account verified!
Welcome to Bestyy!
```

### Test 2: Pickup Code Verification (Vendor)

```python
# Vendor with pending order
POST /whatsapp/webhook
{
    "from": "+2348098765432",  # Verified vendor
    "message": "PK-A1B2C3"
}

# Bot Response:
✅ Pickup Code Verified!
📦 Order: ORD-20251121-00123
💰 Your Payout: ₦9,000
💸 Payment initiated!
```

### Test 3: Delivery OTP Verification (Courier)

```python
# Courier with assigned delivery
POST /whatsapp/webhook
{
    "from": "+2348055555555",  # Verified courier
    "message": "DL-789012"
}

# Bot Response:
✅ Delivery Confirmed!
📦 Order: ORD-20251121-00123
💰 Your Payout: ₦1,500
💸 Payment initiated!
```

---

## ✅ Advantages of Prefix System

1. **Clear Identification**
   - Bot instantly knows what type of code it is
   - No confusion between different verification types

2. **User Friendly**
   - Codes are self-explanatory (PK = Pickup, DL = Delivery)
   - Easy to communicate over phone: "P-K dash A-1-B-2-C-3"

3. **Backward Compatible**
   - Users can enter with or without prefix
   - System automatically normalizes the input

4. **Error Prevention**
   - Prevents accidental verification with wrong code type
   - Clear error messages guide users

5. **Scalable**
   - Easy to add new code types in future (e.g., RT- for Return, CN- for Cancellation)

---

## 📝 Database Structure

### Order Model Fields

```python
class Order(models.Model):
    # Pickup verification (Vendor → Payment)
    pickup_code = models.CharField(max_length=20)  # Stores "PK-A1B2C3"
    pickup_code_verified = models.BooleanField(default=False)
    vendor_transfer_reference = models.CharField(max_length=50, unique=True)
    vendor_paid = models.BooleanField(default=False)
    
    # Delivery verification (Courier → Payment)
    delivery_otp = models.CharField(max_length=20)  # Stores "DL-123456"
    delivery_otp_verified = models.BooleanField(default=False)
    courier_transfer_reference = models.CharField(max_length=50, unique=True)
    courier_paid = models.BooleanField(default=False)
```

### PendingUser Model (WhatsApp Verification)

```python
class PendingUser(models.Model):
    phone = models.CharField(max_length=20)
    verification_code = models.CharField(max_length=6)  # Stores "123456" (no prefix)
    verified = models.BooleanField(default=False)
```

---

## 🚨 Error Messages

### Invalid Pickup Code
```
❌ No order found with code: PK-WRONG

Please ensure:
• The code is correct (format: PK-XXXXXX)
• The order hasn't been verified already
• The order belongs to your vendor account
```

### Invalid Delivery OTP
```
❌ No order found with OTP: DL-WRONG

Please ensure:
• The OTP is correct (format: DL-XXXXXX)
• The order hasn't been delivered already
• The order is assigned to you
```

### Invalid WhatsApp Verification
```
❌ Invalid verification code

Please check your code and try again, or visit 
the website to request a new code.
```

---

## 🎯 Summary

| Question | Answer |
|----------|--------|
| How does the bot know which endpoint to call? | By checking the **prefix** (PK- or DL-) and **user role** |
| Can users enter codes without prefix? | **Yes!** The system auto-adds the prefix |
| Are old codes still valid? | **Yes!** Backward compatible with unprefixed codes |
| What if code has wrong prefix? | System shows clear error with correct format |
| Is WhatsApp verification affected? | **No!** It remains unprefixed and works as before |

**The prefix system makes everything crystal clear! 🎉**
