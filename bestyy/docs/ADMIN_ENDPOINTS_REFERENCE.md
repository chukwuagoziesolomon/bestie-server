# Admin API Endpoints Reference

This document provides a comprehensive list of all admin API endpoints with their parameters and responses.

## Table of Contents

1. [Authentication Endpoints](#authentication-endpoints)
2. [Dashboard & Analytics Endpoints](#dashboard--analytics-endpoints)
3. [User Management Endpoints](#user-management-endpoints)
4. [Vendor Management Endpoints](#vendor-management-endpoints)
5. [Courier Management Endpoints](#courier-management-endpoints)
6. [Verification Endpoints](#verification-endpoints)
7. [Order Management Endpoints](#order-management-endpoints)
8. [Revenue Analytics Endpoints](#revenue-analytics-endpoints)
9. [Activity & Notifications Endpoints](#activity--notifications-endpoints)

## Authentication Endpoints

### 1. Admin Login
**POST** `/api/admin/login/`

**Parameters:**
```json
{
    "email": "admin@example.com",
    "password": "password123"
}
```

**Response (200 OK):**
```json
{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
        "id": 1,
        "email": "admin@example.com",
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin",
        "is_superuser": true
    }
}
```

### 2. Admin Logout
**POST** `/api/admin/logout/`

**Parameters:**
```json
{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
    "message": "Successfully logged out"
}
```

## Dashboard & Analytics Endpoints

### 3. Dashboard KPI Stats
**GET** `/api/admin/dashboard/stats/`

**Parameters:**
- `period` (optional): `today`, `week`, `month` (default: `week`)

**Response (200 OK):**
```json
{
    "total_orders": {
        "value": 90,
        "trend": "up",
        "change_percentage": 1.3,
        "comparison_text": "Up from past week",
        "icon": "package"
    },
    "total_revenue": {
        "value": 200000.00,
        "formatted_value": "N200,000",
        "trend": "down",
        "change_percentage": 4.3,
        "comparison_text": "Down from yesterday",
        "icon": "trending-up"
    },
    "pending_verification": {
        "value": 10,
        "trend": "up",
        "change_percentage": 1.8,
        "comparison_text": "Up from yesterday",
        "icon": "check-circle"
    },
    "active_couriers": {
        "value": 8,
        "trend": "up",
        "change_percentage": 1.8,
        "comparison_text": "Up from yesterday",
        "icon": "truck"
    }
}
```

### 4. Dashboard Metrics
**GET** `/api/admin/dashboard-metrics/`

**Response (200 OK):**
```json
{
    "totals": {
        "users": 150,
        "vendors": 25,
        "couriers": 30,
        "active_users": 120
    },
    "new_users": {
        "week": 15,
        "month": 45
    },
    "pending_verifications": {
        "vendors": 5,
        "couriers": 3
    },
    "user_growth": [
        {
            "date": "2025-09-01",
            "count": 100
        }
    ]
}
```

## User Management Endpoints

### 5. Regular Users List
**GET** `/api/admin/users/`

**Parameters:**
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)
- `search` (optional): Search in names, emails

**Response (200 OK):**
```json
{
    "count": 150,
    "next": "http://localhost:8000/api/admin/users/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "user",
            "date_joined": "2025-09-01T10:00:00Z",
            "last_login": "2025-09-08T15:30:00Z",
            "is_active": true
        }
    ]
}
```

### 6. Regular Users Count
**GET** `/api/admin/users/count/`

**Response (200 OK):**
```json
{
    "total_users": 150,
    "active_users": 120,
    "new_users_this_week": 15,
    "new_users_this_month": 45
}
```

### 7. Suspend User
**POST** `/api/admin/users/{type}/{id}/suspend/`

**Path Parameters:**
- `type`: `vendor` or `courier`
- `id`: User profile ID

**Parameters:**
```json
{
    "reason": "Violation of terms of service",
    "duration_days": 30,
    "notify_user": true
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Vendor account suspended successfully",
    "user": {
        "id": 1,
        "email": "vendor@example.com",
        "business_name": "Tasty Bites",
        "status": "suspended",
        "suspension_reason": "Violation of terms of service",
        "suspension_date": "2025-09-08T10:30:00Z",
        "suspension_duration_days": 30
    }
}
```

### 8. Activate User
**POST** `/api/admin/users/{type}/{id}/activate/`

**Path Parameters:**
- `type`: `vendor` or `courier`
- `id`: User profile ID

**Parameters:**
```json
{
    "reason": "Issue resolved, account reactivated",
    "notify_user": true
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Vendor account activated successfully",
    "user": {
        "id": 1,
        "email": "vendor@example.com",
        "business_name": "Tasty Bites",
        "status": "active",
        "activation_date": "2025-09-08T10:30:00Z"
    }
}
```

### 9. Get User Status
**GET** `/api/admin/users/{type}/{id}/status/`

**Path Parameters:**
- `type`: `vendor` or `courier`
- `id`: User profile ID

**Response (200 OK):**
```json
{
    "user": {
        "id": 1,
        "email": "vendor@example.com",
        "business_name": "Tasty Bites",
        "status": "active",
        "suspension_reason": null,
        "suspension_date": null,
        "suspension_duration_days": null,
        "activation_date": "2025-09-01T10:30:00Z"
    }
}
```

### 10. List Suspended Users
**GET** `/api/admin/users/suspended/`

**Parameters:**
- `type` (optional): `vendor`, `courier`, or omit for both
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 10, max: 100)
- `search` (optional): Search in names, emails, business names

**Response (200 OK):**
```json
{
    "suspended_vendors": {
        "count": 2,
        "results": [
            {
                "id": 1,
                "email": "vendor@example.com",
                "business_name": "Tasty Bites",
                "suspension_reason": "Violation of terms",
                "suspension_date": "2025-09-08T10:30:00Z",
                "suspension_duration_days": 30
            }
        ],
        "page": 1,
        "page_size": 10,
        "total_pages": 1
    },
    "suspended_couriers": {
        "count": 1,
        "results": [
            {
                "id": 1,
                "email": "courier@example.com",
                "full_name": "John Doe",
                "suspension_reason": "Poor service quality",
                "suspension_date": "2025-09-08T10:30:00Z",
                "suspension_duration_days": 14
            }
        ],
        "page": 1,
        "page_size": 10,
        "total_pages": 1
    },
    "summary": {
        "total_suspended": 3,
        "vendors_suspended": 2,
        "couriers_suspended": 1
    }
}
```

## Vendor Management Endpoints

### 11. Pending Vendors List
**GET** `/api/admin/vendors/pending/`

**Parameters:**
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 10, max: 100)
- `search` (optional): Search in names, emails, business names

**Response (200 OK):**
```json
{
    "count": 5,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "user": {
                "id": 1,
                "email": "vendor@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "full_name": "John Doe",
                "date_joined": "2025-09-01T10:00:00Z"
            },
            "business_name": "Tasty Bites",
            "phone": "+1234567890",
            "verification_status": "pending",
            "created_at": "2025-09-01T10:00:00Z",
            "logo": "https://res.cloudinary.com/.../logo.jpg",
            "cac_document": "https://res.cloudinary.com/.../cac.pdf"
        }
    ]
}
```

### 12. Vendor Details
**GET** `/api/admin/vendors/{vendor_id}/`

**Path Parameters:**
- `vendor_id`: Vendor profile ID

**Response (200 OK):**
```json
{
    "type": "vendor",
    "id": 1,
    "user": {
        "id": 1,
        "email": "vendor@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "full_name": "John Doe",
        "date_joined": "2025-09-01T10:00:00Z"
    },
    "business_name": "Tasty Bites",
    "phone": "+1234567890",
    "business_address": "123 Main St",
    "cac_number": "123456",
    "verification_status": "pending",
    "verification_notes": null,
    "created_at": "2025-09-01T10:00:00Z",
    "updated_at": "2025-09-01T10:00:00Z",
    "logo": "https://res.cloudinary.com/.../logo.jpg",
    "cac_document": "https://res.cloudinary.com/.../cac.pdf",
    "valid_id": "https://res.cloudinary.com/.../id.jpg"
}
```

### 13. Approve Vendor
**POST** `/api/admin/vendors/{vendor_id}/approve/`

**Path Parameters:**
- `vendor_id`: Vendor profile ID

**Parameters:**
```json
{
    "notes": "All documents verified successfully"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Vendor approved successfully",
    "vendor": {
        "id": 1,
        "verification_status": "approved",
        "verification_date": "2025-09-08T10:30:00Z",
        "verification_notes": "All documents verified successfully"
    }
}
```

### 14. Reject Vendor
**POST** `/api/admin/vendors/{vendor_id}/reject/`

**Path Parameters:**
- `vendor_id`: Vendor profile ID

**Parameters:**
```json
{
    "reason": "Invalid CAC document",
    "notes": "Please provide a valid CAC document"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Vendor rejected successfully",
    "vendor": {
        "id": 1,
        "verification_status": "rejected",
        "verification_date": "2025-09-08T10:30:00Z",
        "verification_notes": "Please provide a valid CAC document"
    }
}
```

### 15. Vendor Stats
**GET** `/api/admin/vendors/stats/`

**Response (200 OK):**
```json
{
    "total_vendors": 25,
    "approved_vendors": 20,
    "pending_vendors": 3,
    "rejected_vendors": 2,
    "new_vendors_this_week": 5,
    "new_vendors_this_month": 15
}
```

## Courier Management Endpoints

### 16. Pending Couriers List
**GET** `/api/admin/couriers/pending/`

**Parameters:**
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 10, max: 100)
- `search` (optional): Search in names, emails

**Response (200 OK):**
```json
{
    "count": 3,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "user": {
                "id": 2,
                "email": "courier@example.com",
                "first_name": "Jane",
                "last_name": "Smith",
                "full_name": "Jane Smith",
                "date_joined": "2025-09-01T10:00:00Z"
            },
            "phone": "+1234567890",
            "vehicle_type": "bike",
            "verification_status": "pending",
            "created_at": "2025-09-01T10:00:00Z",
            "profile_photo": "https://res.cloudinary.com/.../photo.jpg",
            "id_upload": "https://res.cloudinary.com/.../id.jpg"
        }
    ]
}
```

### 17. Courier Details
**GET** `/api/admin/couriers/{courier_id}/`

**Path Parameters:**
- `courier_id`: Courier profile ID

**Response (200 OK):**
```json
{
    "type": "courier",
    "id": 1,
    "user": {
        "id": 2,
        "email": "courier@example.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "full_name": "Jane Smith",
        "date_joined": "2025-09-01T10:00:00Z"
    },
    "phone": "+1234567890",
    "vehicle_type": "bike",
    "verification_status": "pending",
    "created_at": "2025-09-01T10:00:00Z",
    "updated_at": "2025-09-01T10:00:00Z",
    "profile_photo": "https://res.cloudinary.com/.../photo.jpg",
    "id_upload": "https://res.cloudinary.com/.../id.jpg"
}
```

### 18. Approve Courier
**POST** `/api/admin/couriers/{courier_id}/approve/`

**Path Parameters:**
- `courier_id`: Courier profile ID

**Parameters:**
```json
{
    "notes": "All documents verified successfully"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Courier approved successfully",
    "courier": {
        "id": 1,
        "verification_status": "approved",
        "verification_date": "2025-09-08T10:30:00Z",
        "verification_notes": "All documents verified successfully"
    }
}
```

### 19. Reject Courier
**POST** `/api/admin/couriers/{courier_id}/reject/`

**Path Parameters:**
- `courier_id`: Courier profile ID

**Parameters:**
```json
{
    "reason": "Invalid ID document",
    "notes": "Please provide a valid government-issued ID"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Courier rejected successfully",
    "courier": {
        "id": 1,
        "verification_status": "rejected",
        "verification_date": "2025-09-08T10:30:00Z",
        "verification_notes": "Please provide a valid government-issued ID"
    }
}
```

## Verification Endpoints

### 20. All Pending Verifications
**GET** `/api/admin/verification/all-pending/`

**Parameters:**
- `type` (optional): `vendor`, `courier`, or omit for both
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 10, max: 100)
- `search` (optional): Search in names, emails, business names

**Response (200 OK):**
```json
{
    "vendors": {
        "count": 5,
        "results": [
            {
                "type": "vendor",
                "id": 1,
                "user": {
                    "id": 1,
                    "email": "vendor@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "full_name": "John Doe",
                    "date_joined": "2025-09-01T10:00:00Z"
                },
                "business_name": "Tasty Bites",
                "phone": "+1234567890",
                "verification_status": "pending",
                "created_at": "2025-09-01T10:00:00Z",
                "logo": "https://res.cloudinary.com/.../logo.jpg",
                "cac_document": "https://res.cloudinary.com/.../cac.pdf"
            }
        ]
    },
    "couriers": {
        "count": 3,
        "results": [
            {
                "type": "courier",
                "id": 1,
                "user": {
                    "id": 2,
                    "email": "courier@example.com",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "full_name": "Jane Smith",
                    "date_joined": "2025-09-01T10:00:00Z"
                },
                "phone": "+1234567890",
                "vehicle_type": "bike",
                "verification_status": "pending",
                "created_at": "2025-09-01T10:00:00Z",
                "profile_photo": "https://res.cloudinary.com/.../photo.jpg",
                "id_upload": "https://res.cloudinary.com/.../id.jpg"
            }
        ]
    },
    "summary": {
        "total_pending": 8,
        "vendors_pending": 5,
        "couriers_pending": 3
    }
}
```

### 21. Unified Verification Details
**GET** `/api/admin/verification/{type}/{id}/`

**Path Parameters:**
- `type`: `vendor` or `courier`
- `id`: Profile ID

**Response (200 OK):**
```json
{
    "type": "vendor",
    "id": 1,
    "user": {
        "id": 1,
        "email": "vendor@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "full_name": "John Doe",
        "date_joined": "2025-09-01T10:00:00Z"
    },
    "business_name": "Tasty Bites",
    "phone": "+1234567890",
    "business_address": "123 Main St",
    "cac_number": "123456",
    "verification_status": "pending",
    "verification_notes": null,
    "created_at": "2025-09-01T10:00:00Z",
    "updated_at": "2025-09-01T10:00:00Z",
    "logo": "https://res.cloudinary.com/.../logo.jpg",
    "cac_document": "https://res.cloudinary.com/.../cac.pdf",
    "valid_id": "https://res.cloudinary.com/.../id.jpg"
}
```

### 22. Unified Approve
**POST** `/api/admin/verification/{type}/{id}/approve/`

**Path Parameters:**
- `type`: `vendor` or `courier`
- `id`: Profile ID

**Parameters:**
```json
{
    "notes": "All documents verified successfully"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Vendor approved successfully",
    "verification": {
        "type": "vendor",
        "id": 1,
        "verification_status": "approved",
        "verification_date": "2025-09-08T10:30:00Z",
        "verification_notes": "All documents verified successfully"
    }
}
```

### 23. Unified Reject
**POST** `/api/admin/verification/{type}/{id}/reject/`

**Path Parameters:**
- `type`: `vendor` or `courier`
- `id`: Profile ID

**Parameters:**
```json
{
    "reason": "Invalid documents",
    "notes": "Please provide valid documents"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Vendor rejected successfully",
    "verification": {
        "type": "vendor",
        "id": 1,
        "verification_status": "rejected",
        "verification_date": "2025-09-08T10:30:00Z",
        "verification_notes": "Please provide valid documents"
    }
}
```

## Order Management Endpoints

### 24. Orders List
**GET** `/api/admin/orders/`

**Parameters:**
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)
- `status` (optional): Filter by order status
- `vendor_id` (optional): Filter by vendor
- `courier_id` (optional): Filter by courier
- `date_from` (optional): Filter orders from date (YYYY-MM-DD)
- `date_to` (optional): Filter orders to date (YYYY-MM-DD)

**Response (200 OK):**
```json
{
    "count": 150,
    "next": "http://localhost:8000/api/admin/orders/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "order_number": "ORD-001",
            "customer": {
                "id": 1,
                "email": "customer@example.com",
                "full_name": "John Customer"
            },
            "vendor": {
                "id": 1,
                "business_name": "Tasty Bites"
            },
            "courier": {
                "id": 1,
                "full_name": "Jane Courier"
            },
            "status": "delivered",
            "total_price": 2500.00,
            "created_at": "2025-09-08T10:00:00Z",
            "delivered_at": "2025-09-08T12:30:00Z"
        }
    ]
}
```

### 25. Order Stats
**GET** `/api/admin/orders/stats/`

**Parameters:**
- `period` (optional): `today`, `week`, `month`, `year` (default: `month`)

**Response (200 OK):**
```json
{
    "total_orders": 150,
    "completed_orders": 120,
    "pending_orders": 20,
    "cancelled_orders": 10,
    "total_revenue": 375000.00,
    "average_order_value": 2500.00,
    "orders_by_status": {
        "pending": 20,
        "confirmed": 15,
        "preparing": 10,
        "ready": 5,
        "picked_up": 8,
        "delivered": 120,
        "cancelled": 10
    }
}
```

## Revenue Analytics Endpoints

### 26. Revenue Analytics
**GET** `/api/admin/revenue/analytics/`

**Parameters:**
- `period` (optional): `today`, `week`, `month`, `quarter`, `year`, `custom` (default: `month`)
- `start_date` (optional): Start date for custom period (YYYY-MM-DD)
- `end_date` (optional): End date for custom period (YYYY-MM-DD)
- `granularity` (optional): `hour`, `day`, `week`, `month` (default: `day`)
- `currency` (optional): Currency code (default: `NGN`)

**Response (200 OK):**
```json
{
    "summary": {
        "total_revenue": 128700.00,
        "total_orders": 1250,
        "average_order_value": 102.96,
        "growth_percentage": 3.4,
        "previous_period_revenue": 124500.00
    },
    "time_series": [
        {
            "date": "2025-07-29T00:00:00Z",
            "revenue": 220342.76,
            "orders": 45,
            "average_order_value": 4896.51
        }
    ],
    "breakdown": {
        "by_status": {
            "completed": 125000.00,
            "pending": 2500.00,
            "cancelled": 1200.00
        },
        "by_payment_method": {
            "card": 85000.00,
            "bank_transfer": 43700.00
        },
        "top_vendors": [
            {
                "id": 1,
                "business_name": "Tasty Bites",
                "revenue": 25000.00,
                "orders": 150,
                "percentage": 19.4
            }
        ]
    },
    "period": {
        "start_date": "2025-07-01T00:00:00Z",
        "end_date": "2025-07-31T23:59:59Z",
        "granularity": "day"
    }
}
```

### 27. Revenue Chart Data
**GET** `/api/admin/revenue/chart/`

**Parameters:**
- `chart_type` (optional): `line`, `bar`, `pie` (default: `line`)
- `period` (optional): `today`, `week`, `month`, `quarter`, `year` (default: `month`)
- `granularity` (optional): `hour`, `day`, `week`, `month` (default: `day`)

**Response (200 OK):**
```json
{
    "chart_data": {
        "labels": ["2025-09-01", "2025-09-02", "2025-09-03"],
        "datasets": [
            {
                "label": "Revenue",
                "data": [25000, 30000, 28000],
                "borderColor": "rgb(75, 192, 192)",
                "backgroundColor": "rgba(75, 192, 192, 0.2)"
            }
        ]
    },
    "summary": {
        "total_revenue": 83000,
        "total_orders": 45,
        "average_order_value": 1844.44
    }
}
```

### 28. Revenue Breakdown
**GET** `/api/admin/revenue/breakdown/`

**Parameters:**
- `date` (optional): Specific date (YYYY-MM-DD, default: today)
- `period` (optional): `day`, `week`, `month` (default: `day`)
- `breakdown_type` (optional): `hourly`, `daily`, `by_vendor`, `by_status`, `by_payment_method` (default: `hourly`)

**Response (200 OK):**
```json
{
    "period": {
        "date": "2025-09-08",
        "period_type": "day",
        "breakdown_type": "hourly"
    },
    "summary": {
        "total_revenue": 25000.00,
        "total_orders": 45,
        "average_order_value": 555.56
    },
    "breakdown": [
        {
            "time": "09:00",
            "revenue": 2500.00,
            "orders": 5,
            "percentage": 10.0
        },
        {
            "time": "10:00",
            "revenue": 3200.00,
            "orders": 7,
            "percentage": 12.8
        }
    ],
    "top_performers": [
        {
            "vendor_id": 1,
            "vendor_name": "Tasty Bites",
            "revenue": 5000.00,
            "orders": 10,
            "percentage": 20.0
        }
    ]
}
```

## Activity & Notifications Endpoints

### 29. Recent Activities
**GET** `/api/admin/activities/recent/`

**Parameters:**
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)
- `activity_type` (optional): Filter by activity type
- `date_from` (optional): Filter activities from date (YYYY-MM-DD)
- `date_to` (optional): Filter activities to date (YYYY-MM-DD)

**Response (200 OK):**
```json
{
    "count": 50,
    "next": "http://localhost:8000/api/admin/activities/recent/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "activity_type": "user_signup",
            "description": "New user registered: john@example.com",
            "user": {
                "id": 1,
                "email": "admin@example.com",
                "full_name": "Admin User"
            },
            "metadata": {
                "new_user_id": 15,
                "new_user_email": "john@example.com"
            },
            "timestamp": "2025-09-08T10:30:00Z"
        }
    ]
}
```

## Error Responses

### Common Error Formats

**401 Unauthorized:**
```json
{
    "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden:**
```json
{
    "error": "Only superusers can access the admin panel"
}
```

**404 Not Found:**
```json
{
    "error": "Vendor not found"
}
```

**400 Bad Request:**
```json
{
    "error": "Invalid request data",
    "details": {
        "field_name": ["This field is required."]
    }
}
```

**500 Internal Server Error:**
```json
{
    "error": "Internal server error occurred"
}
```

## URL Compatibility

All endpoints support multiple URL patterns for frontend compatibility:

- **Primary**: `/api/admin/endpoint/`
- **Double API**: `/api/api/admin/endpoint/`
- **No API prefix**: `/admin/endpoint/`
- **User admin**: `/api/user/admin/endpoint/`

## Authentication

All endpoints require:
- Valid JWT token in Authorization header: `Bearer <token>`
- User must be a superuser (`is_superuser=True`)

## Rate Limiting

- No specific rate limiting implemented
- Recommended: 100 requests per minute per user for production

## WebSocket Endpoints

Real-time notifications are available via WebSocket:

- **Admin Activity**: `ws://localhost:8000/ws/admin/activity/`
- **Vendor Notifications**: `ws://localhost:8000/ws/vendor/notifications/`
- **Courier Notifications**: `ws://localhost:8000/ws/courier/notifications/`

All WebSocket connections require JWT authentication via query parameter: `?token=<jwt_token>`
