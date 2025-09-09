# WebSocket Integration Guide

This guide provides comprehensive documentation for integrating the real-time WebSocket system in your frontend applications and admin dashboard.

## Table of Contents

1. [Overview](#overview)
2. [WebSocket Endpoints](#websocket-endpoints)
3. [Authentication](#authentication)
4. [Admin Dashboard Integration](#admin-dashboard-integration)
5. [Vendor Dashboard Integration](#vendor-dashboard-integration)
6. [Courier Dashboard Integration](#courier-dashboard-integration)
7. [Message Formats](#message-formats)
8. [Error Handling](#error-handling)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

## Overview

The WebSocket system provides real-time notifications for:
- **Admin Dashboard**: Activity feed, user registrations, order updates, verification status changes
- **Vendor Dashboard**: Account verification status, order notifications
- **Courier Dashboard**: Account verification status, delivery notifications

## WebSocket Endpoints

### Base URL
```
ws://localhost:8000/ws/
```

### Available Endpoints

| Endpoint | Purpose | Authentication Required |
|----------|---------|------------------------|
| `/ws/admin/activity/` | Admin activity feed | Superuser only |
| `/admin/activity/` | Admin activity feed (compatibility) | Superuser only |
| `/ws/vendor/notifications/` | Vendor notifications | Vendor users only |
| `/vendor/notifications/` | Vendor notifications (compatibility) | Vendor users only |
| `/ws/courier/notifications/` | Courier notifications | Courier users only |
| `/courier/notifications/` | Courier notifications (compatibility) | Courier users only |

**Note:** Both `/ws/` prefixed and non-prefixed routes are available for compatibility. Use the `/ws/` prefixed routes for new implementations.

## Authentication

All WebSocket connections require JWT authentication. Include the JWT token in the connection URL:

```javascript
const token = localStorage.getItem('access_token');
const wsUrl = `ws://localhost:8000/ws/admin/activity/?token=${token}`;
const socket = new WebSocket(wsUrl);
```

## Admin Dashboard Integration

### 1. Connect to Admin Activity Feed

```javascript
class AdminWebSocketManager {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
    }

    connect() {
        const token = localStorage.getItem('access_token');
        const wsUrl = `ws://localhost:8000/ws/admin/activity/?token=${token}`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = (event) => {
            console.log('Connected to admin activity feed');
            this.reconnectAttempts = 0;
            this.showConnectionStatus('connected');
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.socket.onclose = (event) => {
            console.log('Disconnected from admin activity feed');
            this.showConnectionStatus('disconnected');
            this.attemptReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showConnectionStatus('error');
        };
    }

    handleMessage(data) {
        switch (data.type) {
            case 'connection.established':
                console.log('WebSocket connection established');
                break;
                
            case 'activity_update':
                this.addActivityToFeed(data.data);
                break;
                
            case 'vendor.registered':
                this.showNotification('New vendor registered', 'info');
                break;
                
            case 'vendor.approved':
                this.showNotification('Vendor approved', 'success');
                break;
                
            case 'vendor.rejected':
                this.showNotification('Vendor rejected', 'warning');
                break;
                
            case 'courier.registered':
                this.showNotification('New courier registered', 'info');
                break;
                
            case 'courier.approved':
                this.showNotification('Courier approved', 'success');
                break;
                
            case 'courier.rejected':
                this.showNotification('Courier rejected', 'warning');
                break;
                
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    addActivityToFeed(activity) {
        const activityFeed = document.getElementById('activity-feed');
        const activityElement = this.createActivityElement(activity);
        activityFeed.insertBefore(activityElement, activityFeed.firstChild);
        
        // Keep only last 50 activities
        const activities = activityFeed.children;
        if (activities.length > 50) {
            activityFeed.removeChild(activities[activities.length - 1]);
        }
    }

    createActivityElement(activity) {
        const div = document.createElement('div');
        div.className = 'activity-item';
        div.innerHTML = `
            <div class="activity-icon" style="color: ${activity.color}">
                <i class="fas fa-${this.getIconClass(activity.icon)}"></i>
            </div>
            <div class="activity-content">
                <div class="activity-title">${activity.title}</div>
                <div class="activity-description">${activity.description}</div>
                <div class="activity-time">${this.formatTime(activity.timestamp)}</div>
            </div>
        `;
        return div;
    }

    getIconClass(icon) {
        const iconMap = {
            'shopping-cart': 'shopping-cart',
            'truck': 'truck',
            'check-circle': 'check-circle',
            'user-plus': 'user-plus',
            'store': 'store',
            'times-circle': 'times-circle'
        };
        return iconMap[icon] || 'info-circle';
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)} mins ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
        return date.toLocaleDateString();
    }

    showNotification(message, type) {
        // Implement your notification system here
        console.log(`${type.toUpperCase()}: ${message}`);
    }

    showConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.className = `connection-status ${status}`;
            statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                this.connect();
            }, this.reconnectDelay * this.reconnectAttempts);
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }
}

// Initialize WebSocket connection
const adminWS = new AdminWebSocketManager();
adminWS.connect();
```

### 2. HTML Structure for Activity Feed

```html
<div class="admin-dashboard">
    <div class="dashboard-header">
        <h1>Admin Dashboard</h1>
        <div id="connection-status" class="connection-status disconnected">Disconnected</div>
    </div>
    
    <div class="activity-section">
        <h2>Recent Activities</h2>
        <div id="activity-feed" class="activity-feed">
            <!-- Activities will be added here dynamically -->
        </div>
    </div>
</div>
```

### 3. CSS Styling

```css
.connection-status {
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: bold;
}

.connection-status.connected {
    background-color: #10B981;
    color: white;
}

.connection-status.disconnected {
    background-color: #EF4444;
    color: white;
}

.connection-status.error {
    background-color: #F59E0B;
    color: white;
}

.activity-feed {
    max-height: 600px;
    overflow-y: auto;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 16px;
}

.activity-item {
    display: flex;
    align-items: flex-start;
    padding: 12px 0;
    border-bottom: 1px solid #F3F4F6;
}

.activity-item:last-child {
    border-bottom: none;
}

.activity-icon {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background-color: #F3F4F6;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 12px;
    font-size: 18px;
}

.activity-content {
    flex: 1;
}

.activity-title {
    font-weight: 600;
    color: #111827;
    margin-bottom: 4px;
}

.activity-description {
    color: #6B7280;
    font-size: 14px;
    margin-bottom: 4px;
}

.activity-time {
    color: #9CA3AF;
    font-size: 12px;
}
```

## Vendor Dashboard Integration

### 1. Connect to Vendor Notifications

```javascript
class VendorWebSocketManager {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    connect() {
        const token = localStorage.getItem('access_token');
        const wsUrl = `ws://localhost:8000/ws/vendor/notifications/?token=${token}`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = (event) => {
            console.log('Connected to vendor notifications');
            this.reconnectAttempts = 0;
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.socket.onclose = (event) => {
            console.log('Disconnected from vendor notifications');
            this.attemptReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('Vendor WebSocket error:', error);
        };
    }

    handleMessage(data) {
        switch (data.type) {
            case 'connection.established':
                console.log('Vendor WebSocket connection established');
                break;
                
            case 'account.approved':
                this.showApprovalNotification(data.data);
                break;
                
            case 'account.rejected':
                this.showRejectionNotification(data.data);
                break;
                
            case 'order.updated':
                this.showOrderUpdate(data.data);
                break;
                
            default:
                console.log('Unknown vendor message type:', data.type);
        }
    }

    showApprovalNotification(data) {
        const notification = {
            title: 'Account Approved!',
            message: data.message,
            type: 'success',
            duration: 10000
        };
        this.showNotification(notification);
        
        // Update UI to show approved status
        this.updateAccountStatus('approved');
    }

    showRejectionNotification(data) {
        const notification = {
            title: 'Account Rejected',
            message: data.message,
            type: 'error',
            duration: 15000,
            details: data.reason
        };
        this.showNotification(notification);
        
        // Update UI to show rejected status
        this.updateAccountStatus('rejected', data.reason);
    }

    showOrderUpdate(data) {
        const notification = {
            title: 'Order Update',
            message: `Order #${data.order_id} status: ${data.status}`,
            type: 'info',
            duration: 5000
        };
        this.showNotification(notification);
    }

    updateAccountStatus(status, reason = null) {
        const statusElement = document.getElementById('account-status');
        if (statusElement) {
            statusElement.className = `account-status ${status}`;
            statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            
            if (reason) {
                const reasonElement = document.getElementById('rejection-reason');
                if (reasonElement) {
                    reasonElement.textContent = reason;
                    reasonElement.style.display = 'block';
                }
            }
        }
    }

    showNotification(notification) {
        // Implement your notification system here
        console.log('Notification:', notification);
        
        // Example: Show toast notification
        this.showToast(notification);
    }

    showToast(notification) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${notification.type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <h4>${notification.title}</h4>
                <p>${notification.message}</p>
                ${notification.details ? `<p class="toast-details">${notification.details}</p>` : ''}
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        document.body.appendChild(toast);
        
        // Auto remove after duration
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, notification.duration || 5000);
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                this.connect();
            }, 1000 * this.reconnectAttempts);
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }
}

// Initialize vendor WebSocket
const vendorWS = new VendorWebSocketManager();
vendorWS.connect();
```

## Courier Dashboard Integration

### 1. Connect to Courier Notifications

```javascript
class CourierWebSocketManager {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    connect() {
        const token = localStorage.getItem('access_token');
        const wsUrl = `ws://localhost:8000/ws/courier/notifications/?token=${token}`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = (event) => {
            console.log('Connected to courier notifications');
            this.reconnectAttempts = 0;
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.socket.onclose = (event) => {
            console.log('Disconnected from courier notifications');
            this.attemptReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('Courier WebSocket error:', error);
        };
    }

    handleMessage(data) {
        switch (data.type) {
            case 'connection.established':
                console.log('Courier WebSocket connection established');
                break;
                
            case 'account.approved':
                this.showApprovalNotification(data.data);
                break;
                
            case 'account.rejected':
                this.showRejectionNotification(data.data);
                break;
                
            case 'delivery.assigned':
                this.showDeliveryAssignment(data.data);
                break;
                
            default:
                console.log('Unknown courier message type:', data.type);
        }
    }

    showApprovalNotification(data) {
        const notification = {
            title: 'Account Approved!',
            message: data.message,
            type: 'success',
            duration: 10000
        };
        this.showNotification(notification);
        this.updateAccountStatus('approved');
    }

    showRejectionNotification(data) {
        const notification = {
            title: 'Account Rejected',
            message: data.message,
            type: 'error',
            duration: 15000,
            details: data.reason
        };
        this.showNotification(notification);
        this.updateAccountStatus('rejected', data.reason);
    }

    showDeliveryAssignment(data) {
        const notification = {
            title: 'New Delivery Assignment',
            message: `You have been assigned to deliver order #${data.order_id}`,
            type: 'info',
            duration: 8000
        };
        this.showNotification(notification);
    }

    updateAccountStatus(status, reason = null) {
        const statusElement = document.getElementById('account-status');
        if (statusElement) {
            statusElement.className = `account-status ${status}`;
            statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            
            if (reason) {
                const reasonElement = document.getElementById('rejection-reason');
                if (reasonElement) {
                    reasonElement.textContent = reason;
                    reasonElement.style.display = 'block';
                }
            }
        }
    }

    showNotification(notification) {
        // Implement your notification system here
        console.log('Courier Notification:', notification);
        this.showToast(notification);
    }

    showToast(notification) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${notification.type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <h4>${notification.title}</h4>
                <p>${notification.message}</p>
                ${notification.details ? `<p class="toast-details">${notification.details}</p>` : ''}
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, notification.duration || 5000);
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                this.connect();
            }, 1000 * this.reconnectAttempts);
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }
}

// Initialize courier WebSocket
const courierWS = new CourierWebSocketManager();
courierWS.connect();
```

## Message Formats

### 1. Admin Activity Messages

```javascript
// Activity Update
{
    "type": "activity_update",
    "data": {
        "id": 123,
        "title": "New Order #1001",
        "description": "User 'John Doe' ordered from 'Tasty Bites'",
        "icon": "shopping-cart",
        "color": "#10B981",
        "amount": 25.50,
        "timestamp": "2025-09-08T10:30:00Z",
        "user": {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com"
        },
        "vendor": {
            "id": 2,
            "name": "Tasty Bites"
        }
    }
}

// Vendor Registration
{
    "type": "vendor.registered",
    "data": {
        "vendor_id": 3,
        "business_name": "New Restaurant",
        "email": "owner@newrestaurant.com",
        "timestamp": "2025-09-08T10:30:00Z",
        "message": "New vendor registered: New Restaurant"
    }
}

// Vendor Approval
{
    "type": "vendor.approved",
    "data": {
        "vendor_id": 3,
        "business_name": "New Restaurant",
        "approved_by": "Admin User",
        "timestamp": "2025-09-08T10:30:00Z",
        "message": "Vendor approved: New Restaurant"
    }
}
```

### 2. Vendor Notification Messages

```javascript
// Account Approved
{
    "type": "account.approved",
    "data": {
        "message": "Your vendor account has been approved!",
        "status": "approved",
        "verification_date": "2025-09-08T10:30:00Z",
        "next_steps": "You can now access all vendor features.",
        "timestamp": "2025-09-08T10:30:00Z"
    }
}

// Account Rejected
{
    "type": "account.rejected",
    "data": {
        "message": "Your vendor account has been rejected.",
        "status": "rejected",
        "reason": "Documents are unclear. Please resubmit with better quality images.",
        "verification_date": "2025-09-08T10:30:00Z",
        "next_steps": "Please update your information and reapply.",
        "timestamp": "2025-09-08T10:30:00Z"
    }
}
```

### 3. Courier Notification Messages

```javascript
// Account Approved
{
    "type": "account.approved",
    "data": {
        "message": "Your courier account has been approved!",
        "status": "approved",
        "verification_date": "2025-09-08T10:30:00Z",
        "next_steps": "You can now start accepting delivery requests.",
        "timestamp": "2025-09-08T10:30:00Z"
    }
}

// Account Rejected
{
    "type": "account.rejected",
    "data": {
        "message": "Your courier account has been rejected.",
        "status": "rejected",
        "reason": "Invalid ID document provided.",
        "verification_date": "2025-09-08T10:30:00Z",
        "next_steps": "Please update your information and reapply.",
        "timestamp": "2025-09-08T10:30:00Z"
    }
}
```

## Error Handling

### 1. Connection Errors

```javascript
socket.onerror = (error) => {
    console.error('WebSocket error:', error);
    
    // Handle different error types
    if (error.code === 1006) {
        // Connection lost
        showError('Connection lost. Attempting to reconnect...');
    } else if (error.code === 1002) {
        // Protocol error
        showError('Protocol error. Please refresh the page.');
    } else if (error.code === 1003) {
        // Unsupported data
        showError('Unsupported data received.');
    }
};
```

### 2. Authentication Errors

```javascript
socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'auth.error') {
        console.error('Authentication error:', data.message);
        // Redirect to login or refresh token
        handleAuthError(data.message);
    }
};

function handleAuthError(message) {
    if (message.includes('token')) {
        // Token expired or invalid
        localStorage.removeItem('access_token');
        window.location.href = '/login';
    }
}
```

### 3. Reconnection Strategy

```javascript
class WebSocketManager {
    constructor() {
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.isReconnecting = false;
    }

    attemptReconnect() {
        if (this.isReconnecting || this.reconnectAttempts >= this.maxReconnectAttempts) {
            return;
        }

        this.isReconnecting = true;
        this.reconnectAttempts++;

        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        setTimeout(() => {
            console.log(`Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
            this.connect();
            this.isReconnecting = false;
        }, delay);
    }
}
```

## Testing

### 1. Test WebSocket Connection

```javascript
// Test admin WebSocket
function testAdminWebSocket() {
    const token = 'your-test-token';
    const ws = new WebSocket(`ws://localhost:8000/ws/admin/activity/?token=${token}`);
    
    ws.onopen = () => console.log('Admin WebSocket connected');
    ws.onmessage = (event) => console.log('Admin message:', JSON.parse(event.data));
    ws.onerror = (error) => console.error('Admin WebSocket error:', error);
}

// Test vendor WebSocket
function testVendorWebSocket() {
    const token = 'your-vendor-token';
    const ws = new WebSocket(`ws://localhost:8000/ws/vendor/notifications/?token=${token}`);
    
    ws.onopen = () => console.log('Vendor WebSocket connected');
    ws.onmessage = (event) => console.log('Vendor message:', JSON.parse(event.data));
    ws.onerror = (error) => console.error('Vendor WebSocket error:', error);
}
```

### 2. Test Message Handling

```javascript
// Test activity feed
function testActivityFeed() {
    const mockActivity = {
        type: 'activity_update',
        data: {
            id: 1,
            title: 'Test Activity',
            description: 'This is a test activity',
            icon: 'info-circle',
            color: '#3B82F6',
            timestamp: new Date().toISOString()
        }
    };
    
    // Simulate receiving message
    adminWS.handleMessage(mockActivity);
}
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check if Django server is running
   - Verify WebSocket URL is correct
   - Check firewall settings

2. **Authentication Failed**
   - Verify JWT token is valid
   - Check token expiration
   - Ensure user has correct permissions

3. **Messages Not Received**
   - Check WebSocket connection status
   - Verify message handlers are registered
   - Check browser console for errors

4. **Reconnection Issues**
   - Check network connectivity
   - Verify reconnection logic
   - Check for rate limiting

### Debug Mode

```javascript
// Enable debug logging
const DEBUG = true;

function debugLog(message, data = null) {
    if (DEBUG) {
        console.log(`[WebSocket Debug] ${message}`, data);
    }
}

// Use in WebSocket handlers
socket.onopen = (event) => {
    debugLog('WebSocket opened', event);
};

socket.onmessage = (event) => {
    debugLog('Message received', JSON.parse(event.data));
};
```

### Browser Compatibility

| Browser | WebSocket Support | Notes |
|---------|------------------|-------|
| Chrome | ✅ Full | Recommended |
| Firefox | ✅ Full | Recommended |
| Safari | ✅ Full | iOS 4.2+ |
| Edge | ✅ Full | Recommended |
| IE | ⚠️ Limited | IE 10+ only |

## Best Practices

1. **Always handle connection errors gracefully**
2. **Implement proper reconnection logic**
3. **Use exponential backoff for reconnection**
4. **Validate all incoming messages**
5. **Clean up WebSocket connections on page unload**
6. **Use TypeScript for better type safety**
7. **Implement proper error boundaries**
8. **Test with different network conditions**

## Security Considerations

1. **Always use WSS in production**
2. **Validate JWT tokens on the server**
3. **Implement rate limiting**
4. **Sanitize all incoming data**
5. **Use CORS properly**
6. **Implement proper authentication checks**

This guide provides everything you need to integrate the WebSocket system into your frontend applications. The system is designed to be robust, scalable, and easy to use.
