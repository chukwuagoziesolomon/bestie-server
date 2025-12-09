# API Endpoints Documentation

## 1. Vendor Autocomplete Search

**Endpoint:** `GET /api/user/vendors/autocomplete/`

**Purpose:** Fast search for restaurants/vendors with advanced filtering by name, location, food items, and price.

**Authentication:** None (public endpoint)

**Query Parameters:**
- `q` (string, optional): Search query (restaurant name, category, description, service areas)
- `location` (string, optional): Filter by city/state/area
- `category` (string, optional): Filter by business category
- `food` (string, optional): Search by food item name
- `min_price` (number, optional): Minimum price filter for food items
- `max_price` (number, optional): Maximum price filter for food items
- `limit` (integer, optional): Maximum results (default: 10, max: 50)

**Example Request:**
```bash
GET /api/user/vendors/autocomplete/?q=rice&location=Lagos&food=jollof&min_price=500&max_price=1500&limit=5
```

**Response:**
```json
{
  "success": true,
  "query": "rice",
  "count": 3,
  "results": [
    {
      "id": 1,
      "business_name": "Mama's Kitchen",
      "category": "Nigerian Restaurant",
      "address": "123 Lagos Street, Lagos",
      "service_areas": "Lagos, Ikeja",
      "description": "Authentic Nigerian cuisine",
      "logo": "https://cloudinary.com/...",
      "cover_image": "https://cloudinary.com/...",
      "offers_delivery": true,
      "opening_hours": "08:00:00",
      "closing_hours": "22:00:00",
      "product_count": 25,
      "phone": "+2348012345678",
      "matching_products": [
        {
          "id": 101,
          "name": "Jollof Rice",
          "price": 1200.00,
          "description": "Spicy Nigerian jollof rice"
        }
      ]
    }
  ]
}
```

**Features:**
- Smart ranking (exact matches, starts with, contains)
- Location-based filtering
- Food item search with price filtering
- Returns matching food items when food/price filters are used

---

## 2. Phone Verification with JWT Tokens

**Endpoint:** `POST /api/auth/verify-whatsapp-signup/`

**Purpose:** Verify phone number during user onboarding and return JWT tokens for subsequent authenticated requests.

**Authentication:** None (public endpoint)

**Request Body:**
```json
{
  "phone": "+2348012345678",
  "code": "123456"
}
```

**Response (Success):**
```json
{
  "ok": true,
  "user_id": 123,
  "role": "user",
  "first_name": "John",
  "last_name": "Doe",
  "verification_complete": true,
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

**Response (Error):**
```json
{
  "ok": false,
  "error": "Invalid verification code"
}
```

**GET Endpoint for Verification Status:**
`GET /api/auth/verification-status/?phone=+2348012345678`

**Purpose:** Check verification status without submitting verification code

**Response (Verification Pending):**
```json
{
  "ok": true,
  "verified": false,
  "verification_complete": false,
  "expires_at": "2025-12-09T15:30:00Z",
  "time_remaining_seconds": 1800
}
```

**Response (Already Verified):**
```json
{
  "ok": true,
  "verified": true,
  "verification_complete": true,
  "message": "Phone number has already been verified successfully",
  "user_id": "123",
  "role": "user",
  "first_name": "John",
  "last_name": "Doe",
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

**Important Note:** For verified users, the GET endpoint now returns JWT tokens to enable seamless continuation of the onboarding flow after WhatsApp verification.

**Features:**
- Creates user account upon successful verification
- Returns JWT access and refresh tokens
- Tokens can be used for bank verification and other protected endpoints
- Frontend should store tokens for subsequent requests
- GET endpoint allows checking verification status without resubmitting code
- **GET endpoint returns JWT tokens for already verified users (enables WhatsApp verification flow)**

---

## 3. Bank Account Verification

**Endpoint:** `POST /api/user/verification/verify-bank/`

**Purpose:** Verify and save bank account details for vendors and couriers.

**Authentication:** Required (`Authorization: Bearer <access_token>`)

**Request Body:**
```json
{
  "account_number": "1234567890",
  "account_name": "John Doe",
  "bank_name": "Access Bank"
}
```

**Note:** `bank_code` is optional - automatically resolved from `bank_name`

**Response (Success):**
```json
{
  "success": true,
  "message": "Bank account verified successfully"
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Invalid key"
}
```

**Note:** The "Invalid key" error typically indicates that the Paystack secret key is not configured correctly on the server. This is an environment variable issue, not a problem with your request data.

**Troubleshooting "Invalid key" Error:**
1. **Check Environment Variables:** Ensure `PAYSTACK_SECRET_KEY` is set correctly in your deployment environment (Render.com dashboard)
2. **Verify Key Format:** Paystack secret keys start with `sk_` 
3. **Test Locally First:** The API works correctly locally, so the issue is server-side configuration
4. **Account Name Matching:** Paystack returns account names in ALL CAPS and different order. The API handles case-insensitive matching, but ensure the name is reasonably similar.

**Bank Code Resolution:**
- OPay Digital Services Limited (OPay) → Code: `999992`
- The system automatically resolves bank names to codes
- If resolution fails, you can manually provide the `bank_code` field

---

## 4. Bank Details Editing

**For Vendors:** `PATCH /api/user/vendor/profile/`

**For Couriers:** Use profile update endpoints (see below)

**For Regular Users:** `PATCH /api/user/profile-info/`

**Purpose:** Update bank account details after initial verification.

**Authentication:** Required (`Authorization: Bearer <access_token>`)

**Request Body (Vendor Example):**
```json
{
  "bank_account_number": "0987654321",
  "bank_name": "GTBank",
  "bank_code": "058"
}
```

**Response:**
```json
{
  "id": 1,
  "business_name": "Mama's Kitchen",
  "bank_account_number": "0987654321",
  "bank_name": "GTBank",
  "bank_code": "058",
  "bank_account_verified": false,
  // ... other profile fields
}
```

**Note:** Changing bank details may require re-verification. The `bank_account_verified` flag will be reset to `false`.

---

## 5. Paystack Supported Banks

**Endpoint:** `GET /api/user/verification/supported-banks/`

**Purpose:** Get list of supported banks for account verification.

**Authentication:** None (public endpoint)

**Query Parameters:**
- `country` (string, optional): Country code (default: "nigeria")

**Example Request:**
```bash
GET /api/user/verification/supported-banks/?country=nigeria
```

**Response:**
```json
{
  "success": true,
  "country": "nigeria",
  "count": 25,
  "banks": [
    {
      "name": "Access Bank",
      "slug": "access-bank",
      "code": "044",
      "longcode": "044150149",
      "gateway": "emandate",
      "pay_with_bank": true,
      "active": true,
      "country": "Nigeria",
      "currency": "NGN",
      "type": "nuban",
      "id": 1,
      "createdAt": "2016-07-14T10:04:29.000Z",
      "updatedAt": "2023-10-12T10:30:00.000Z"
    }
  ]
}
```

**Features:**
- Returns all Paystack-supported Nigerian banks
- Includes bank codes needed for verification
- Used by frontend to populate bank selection dropdowns

---

## Summary

### Authentication Flow:
1. **Phone Verification** → Returns JWT tokens
2. **Bank Verification** → Uses JWT tokens from step 1
3. **Profile Updates** → Uses JWT tokens for ongoing access

### Key Endpoints:
- Search: `GET /api/user/vendors/autocomplete/`
- Phone Verify: `POST /api/auth/verify-whatsapp-signup/`
- Phone Verify Status: `GET /api/auth/verification-status/`
- Bank Verify: `POST /api/user/verification/verify-bank/`
- Bank Update: `PATCH /api/user/vendor/profile/` (vendors)
- Supported Banks: `GET /api/user/verification/supported-banks/`

### Frontend Integration:
- Store JWT tokens after phone verification
- Include `Authorization: Bearer <access_token>` header in authenticated requests
- Handle token refresh using the refresh token when access token expires