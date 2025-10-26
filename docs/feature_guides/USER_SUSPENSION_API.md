# User Suspension/Activation API Documentation

This document provides comprehensive documentation for the admin user management endpoints that allow suspending and activating vendor and courier accounts.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Suspend User Endpoint](#suspend-user-endpoint)
4. [Activate User Endpoint](#activate-user-endpoint)
5. [User Status Endpoint](#user-status-endpoint)
6. [Suspended Users List Endpoint](#suspended-users-list-endpoint)
7. [Response Examples](#response-examples)
8. [Error Handling](#error-handling)
9. [WebSocket Notifications](#websocket-notifications)
10. [Frontend Integration](#frontend-integration)

## Overview

The User Suspension/Activation API provides comprehensive account management capabilities for admins to:

- **Suspend Accounts**: Temporarily or permanently disable vendor/courier accounts
- **Activate Accounts**: Reactivate previously suspended accounts
- **Check Status**: Get current account status and suspension details
- **List Suspended Users**: View all suspended accounts with filtering and pagination
- **Real-time Notifications**: Send WebSocket notifications to affected users and admins

## Authentication

All endpoints require:
- Valid JWT authentication token
- User must be a superuser (`is_superuser=True`)

```javascript
// Example authentication header
Authorization: Bearer <your_jwt_token>
```

## Suspend User Endpoint

### POST /api/admin/users/{type}/{id}/suspend/

Suspends a vendor or courier account, preventing them from using the platform.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | Yes | User type. Options: `vendor`, `courier` |
| `id` | integer | Yes | ID of the vendor or courier profile |

#### Request Body

```json
{
    "reason": "Violation of terms of service",
    "duration_days": 30,
    "notify_user": true
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `reason` | string | No | "Account suspended by admin" | Reason for suspension |
| `duration_days` | integer | No | null | Duration in days (null for indefinite) |
| `notify_user` | boolean | No | true | Whether to send notification to user |

#### Response (200 OK)

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

## Activate User Endpoint

### POST /api/admin/users/{type}/{id}/activate/

Reactivates a previously suspended vendor or courier account.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | Yes | User type. Options: `vendor`, `courier` |
| `id` | integer | Yes | ID of the vendor or courier profile |

#### Request Body

```json
{
    "reason": "Issue resolved, account reactivated",
    "notify_user": true
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `reason` | string | No | "Account reactivated by admin" | Reason for reactivation |
| `notify_user` | boolean | No | true | Whether to send notification to user |

#### Response (200 OK)

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

## User Status Endpoint

### GET /api/admin/users/{type}/{id}/status/

Gets the current status of a vendor or courier account.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | Yes | User type. Options: `vendor`, `courier` |
| `id` | integer | Yes | ID of the vendor or courier profile |

#### Response (200 OK)

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

## 


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

## Response Examples

### Suspend Vendor

```bash
POST /api/admin/users/vendor/1/suspend/
Content-Type: application/json
Authorization: Bearer <token>

{
    "reason": "Multiple customer complaints about food quality",
    "duration_days": 14,
    "notify_user": true
}
```

```json
{
    "success": true,
    "message": "Vendor account suspended successfully",
    "user": {
        "id": 1,
        "email": "tastybites@example.com",
        "business_name": "Tasty Bites Restaurant",
        "status": "suspended",
        "suspension_reason": "Multiple customer complaints about food quality",
        "suspension_date": "2025-09-08T14:30:00Z",
        "suspension_duration_days": 14
    }
}
```

### Activate Courier

```bash
POST /api/admin/users/courier/5/activate/
Content-Type: application/json
Authorization: Bearer <token>

{
    "reason": "Training completed, performance improved",
    "notify_user": true
}
```

```json
{
    "success": true,
    "message": "Courier account activated successfully",
    "user": {
        "id": 5,
        "email": "john.doe@example.com",
        "full_name": "John Doe",
        "status": "active",
        "activation_date": "2025-09-08T16:45:00Z"
    }
}
```

### Get User Status

```bash
GET /api/admin/users/vendor/1/status/
Authorization: Bearer <token>
```

```json
{
    "user": {
        "id": 1,
        "email": "tastybites@example.com",
        "business_name": "Tasty Bites Restaurant",
        "status": "suspended",
        "suspension_reason": "Multiple customer complaints about food quality",
        "suspension_date": "2025-09-08T14:30:00Z",
        "suspension_duration_days": 14,
        "activation_date": null
    }
}
```

### List Suspended Users

```bash
GET /api/admin/users/suspended/?type=vendor&page=1&page_size=5&search=tasty
Authorization: Bearer <token>
```

```json
{
    "suspended_vendors": {
        "count": 1,
        "results": [
            {
                "id": 1,
                "email": "tastybites@example.com",
                "business_name": "Tasty Bites Restaurant",
                "suspension_reason": "Multiple customer complaints about food quality",
                "suspension_date": "2025-09-08T14:30:00Z",
                "suspension_duration_days": 14
            }
        ],
        "page": 1,
        "page_size": 5,
        "total_pages": 1
    },
    "summary": {
        "total_suspended": 1,
        "vendors_suspended": 1,
        "couriers_suspended": 0
    }
}
```

## Error Handling

### Common Error Responses

**401 Unauthorized**
```json
{
    "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden**
```json
{
    "error": "Only superusers can access the admin panel"
}
```

**404 Not Found**
```json
{
    "error": "Vendor not found"
}
```

**400 Bad Request**
```json
{
    "error": "Vendor is already suspended"
}
```

**500 Internal Server Error**
```json
{
    "error": "Failed to suspend user account"
}
```

## WebSocket Notifications

When users are suspended or activated, real-time notifications are sent via WebSocket:

### Admin Notifications

**Vendor Suspended**
```json
{
    "type": "vendor.suspended",
    "data": {
        "vendor_id": 1,
        "business_name": "Tasty Bites",
        "suspended_by": "admin@example.com",
        "timestamp": "2025-09-08T14:30:00Z",
        "reason": "Multiple customer complaints",
        "duration_days": 14,
        "message": "Vendor suspended: Tasty Bites"
    }
}
```

**Courier Activated**
```json
{
    "type": "courier.activated",
    "data": {
        "courier_id": 5,
        "full_name": "John Doe",
        "activated_by": "admin@example.com",
        "timestamp": "2025-09-08T16:45:00Z",
        "reason": "Training completed",
        "message": "Courier activated: John Doe"
    }
}
```

### User Notifications

**Account Suspended**
```json
{
    "type": "account.suspended",
    "data": {
        "status": "suspended",
        "reason": "Multiple customer complaints about food quality",
        "duration_days": 14,
        "suspension_date": "2025-09-08T14:30:00Z",
        "message": "Your vendor account has been suspended.",
        "contact_support": "Please contact support for more information."
    }
}
```

**Account Activated**
```json
{
    "type": "account.activated",
    "data": {
        "status": "active",
        "reason": "Training completed, performance improved",
        "activation_date": "2025-09-08T16:45:00Z",
        "message": "Your courier account has been reactivated!",
        "next_steps": "You can now start accepting delivery requests again."
    }
}
```

## Frontend Integration

### React/JavaScript Example

```javascript
// User Management Component
const UserManagement = () => {
  const [suspendedUsers, setSuspendedUsers] = useState(null);
  const [loading, setLoading] = useState(false);

  // Suspend user
  const suspendUser = async (userType, userId, reason, durationDays) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/admin/users/${userType}/${userId}/suspend/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          reason: reason,
          duration_days: durationDays,
          notify_user: true
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('User suspended:', data);
        // Refresh suspended users list
        fetchSuspendedUsers();
      } else {
        const error = await response.json();
        console.error('Error suspending user:', error);
      }
    } catch (error) {
      console.error('Error suspending user:', error);
    } finally {
      setLoading(false);
    }
  };

  // Activate user
  const activateUser = async (userType, userId, reason) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/admin/users/${userType}/${userId}/activate/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          reason: reason,
          notify_user: true
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('User activated:', data);
        // Refresh suspended users list
        fetchSuspendedUsers();
      } else {
        const error = await response.json();
        console.error('Error activating user:', error);
      }
    } catch (error) {
      console.error('Error activating user:', error);
    } finally {
      setLoading(false);
    }
  };

  // Get user status
  const getUserStatus = async (userType, userId) => {
    try {
      const response = await fetch(`/api/admin/users/${userType}/${userId}/status/`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        return data.user;
      }
    } catch (error) {
      console.error('Error getting user status:', error);
    }
  };

  // Fetch suspended users
  const fetchSuspendedUsers = async () => {
    try {
      const response = await fetch('/api/admin/users/suspended/', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setSuspendedUsers(data);
      }
    } catch (error) {
      console.error('Error fetching suspended users:', error);
    }
  };

  useEffect(() => {
    fetchSuspendedUsers();
  }, []);

  return (
    <div className="user-management">
      <h2>Suspended Users</h2>
      
      {suspendedUsers?.suspended_vendors?.results.map(vendor => (
        <div key={vendor.id} className="suspended-user-card">
          <h3>{vendor.business_name}</h3>
          <p>Email: {vendor.email}</p>
          <p>Reason: {vendor.suspension_reason}</p>
          <p>Suspended: {new Date(vendor.suspension_date).toLocaleDateString()}</p>
          
          <button 
            onClick={() => activateUser('vendor', vendor.id, 'Issue resolved')}
            disabled={loading}
          >
            Activate
          </button>
        </div>
      ))}
      
      {suspendedUsers?.suspended_couriers?.results.map(courier => (
        <div key={courier.id} className="suspended-user-card">
          <h3>{courier.full_name}</h3>
          <p>Email: {courier.email}</p>
          <p>Reason: {courier.suspension_reason}</p>
          <p>Suspended: {new Date(courier.suspension_date).toLocaleDateString()}</p>
          
          <button 
            onClick={() => activateUser('courier', courier.id, 'Issue resolved')}
            disabled={loading}
          >
            Activate
          </button>
        </div>
      ))}
    </div>
  );
};
```

### WebSocket Integration

```javascript
// WebSocket connection for real-time notifications
const useUserNotifications = () => {
  const [socket, setSocket] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const ws = new WebSocket(`ws://localhost:8000/ws/admin/activity/?token=${token}`);
    
    ws.onopen = () => {
      console.log('Connected to admin notifications');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'vendor.suspended' || data.type === 'courier.suspended') {
        // Show notification
        showNotification(`${data.data.message}`, 'warning');
        // Refresh suspended users list
        fetchSuspendedUsers();
      } else if (data.type === 'vendor.activated' || data.type === 'courier.activated') {
        // Show notification
        showNotification(`${data.data.message}`, 'success');
        // Refresh suspended users list
        fetchSuspendedUsers();
      }
    };
    
    ws.onclose = () => {
      console.log('Disconnected from admin notifications');
    };
    
    setSocket(ws);
    
    return () => {
      ws.close();
    };
  }, []);

  return socket;
};
```

## URL Compatibility

The following URL patterns are supported for frontend compatibility:

- `/api/admin/users/{type}/{id}/suspend/` - Primary endpoint
- `/api/api/admin/users/{type}/{id}/suspend/` - Double API prefix compatibility
- `/admin/users/{type}/{id}/suspend/` - No API prefix compatibility
- `/api/user/admin/users/{type}/{id}/suspend/` - User admin prefix compatibility

- `/api/admin/users/{type}/{id}/activate/` - Primary endpoint
- `/api/api/admin/users/{type}/{id}/activate/` - Double API prefix compatibility
- `/admin/users/{type}/{id}/activate/` - No API prefix compatibility
- `/api/user/admin/users/{type}/{id}/activate/` - User admin prefix compatibility

- `/api/admin/users/suspended/` - Primary endpoint
- `/api/api/admin/users/suspended/` - Double API prefix compatibility
- `/admin/users/suspended/` - No API prefix compatibility
- `/api/user/admin/users/suspended/` - User admin prefix compatibility

## Database Changes

The following fields have been added to the models:

### VendorProfile
- `is_suspended`: Boolean field indicating if account is suspended
- `suspension_reason`: Text field for suspension reason
- `suspension_date`: DateTime field for when account was suspended
- `suspension_duration_days`: Integer field for suspension duration
- `activation_date`: DateTime field for when account was last activated

### CourierProfile
- `is_suspended`: Boolean field indicating if account is suspended
- `suspension_reason`: Text field for suspension reason
- `suspension_date`: DateTime field for when account was suspended
- `suspension_duration_days`: Integer field for suspension duration
- `activation_date`: DateTime field for when account was last activated

## Security Considerations

- All endpoints require superuser authentication
- Suspension affects both the profile and the underlying user account
- Real-time notifications are sent to both admins and affected users
- All suspension/activation actions are logged for audit purposes
- Consider implementing rate limiting for production use
- Suspended users cannot log in or perform any platform actions

## Performance Notes

- Suspension/activation operations are immediate
- WebSocket notifications are sent asynchronously
- Suspended users list supports pagination for large datasets
- Search functionality is optimized with database indexes
- Consider implementing caching for frequently accessed suspension data
