# WebSocket Quick Reference

## WebSocket Endpoints

| Endpoint | Purpose | Auth Required |
|----------|---------|---------------|
| `ws://localhost:8000/ws/admin/activity/` | Admin activity feed | Superuser |
| `ws://localhost:8000/admin/activity/` | Admin activity feed (compatibility) | Superuser |
| `ws://localhost:8000/ws/vendor/notifications/` | Vendor notifications | Vendor user |
| `ws://localhost:8000/vendor/notifications/` | Vendor notifications (compatibility) | Vendor user |
| `ws://localhost:8000/ws/courier/notifications/` | Courier notifications | Courier user |
| `ws://localhost:8000/courier/notifications/` | Courier notifications (compatibility) | Courier user |

## Connection Example

```javascript
const token = localStorage.getItem('access_token');
const socket = new WebSocket(`ws://localhost:8000/ws/admin/activity/?token=${token}`);
```

## Message Types

### Admin Activity Feed

| Message Type | Description | Data Structure |
|--------------|-------------|----------------|
| `connection.established` | Connection confirmed | `{ message, timestamp, user_id }` |
| `activity_update` | New activity | `{ id, title, description, icon, color, timestamp }` |
| `vendor.registered` | New vendor signup | `{ vendor_id, business_name, email, timestamp }` |
| `vendor.approved` | Vendor approved | `{ vendor_id, business_name, approved_by, timestamp }` |
| `vendor.rejected` | Vendor rejected | `{ vendor_id, business_name, rejected_by, reason, timestamp }` |
| `courier.registered` | New courier signup | `{ courier_id, full_name, email, timestamp }` |
| `courier.approved` | Courier approved | `{ courier_id, full_name, approved_by, timestamp }` |
| `courier.rejected` | Courier rejected | `{ courier_id, full_name, rejected_by, reason, timestamp }` |

### Vendor Notifications

| Message Type | Description | Data Structure |
|--------------|-------------|----------------|
| `connection.established` | Connection confirmed | `{ message, vendor_id, business_name, timestamp }` |
| `account.approved` | Account approved | `{ message, status, verification_date, next_steps }` |
| `account.rejected` | Account rejected | `{ message, status, reason, verification_date, next_steps }` |
| `order.updated` | Order status change | `{ order_id, status, message }` |

### Courier Notifications

| Message Type | Description | Data Structure |
|--------------|-------------|----------------|
| `connection.established` | Connection confirmed | `{ message, courier_id, timestamp }` |
| `account.approved` | Account approved | `{ message, status, verification_date, next_steps }` |
| `account.rejected` | Account rejected | `{ message, status, reason, verification_date, next_steps }` |
| `delivery.assigned` | New delivery | `{ order_id, pickup_location, delivery_location }` |

## Activity Icons

| Icon | Usage | Color |
|------|-------|-------|
| `shopping-cart` | New orders | `#10B981` |
| `truck` | Courier activities | `#3B82F6` |
| `check-circle` | Approvals/completions | `#10B981` |
| `times-circle` | Rejections | `#EF4444` |
| `user-plus` | New registrations | `#8B5CF6` |
| `store` | Vendor activities | `#F59E0B` |

## API Endpoints for Activity Data

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/admin/activities/recent/` | GET | Get recent activities | `{ activities: [...] }` |
| `/admin/verification/all-pending/` | GET | Get pending verifications | `{ vendors: [...], couriers: [...] }` |
| `/admin/verification/{type}/{id}/` | GET | Get specific user details | User details with documents |
| `/admin/verification/{type}/{id}/approve/` | POST | Approve user | `{ success: true, message: "..." }` |
| `/admin/verification/{type}/{id}/reject/` | POST | Reject user | `{ success: true, message: "..." }` |

## Error Codes

| Code | Description | Action |
|------|-------------|--------|
| `1000` | Normal closure | Connection closed normally |
| `1001` | Going away | Server is shutting down |
| `1002` | Protocol error | Refresh page |
| `1003` | Unsupported data | Check message format |
| `1006` | Connection lost | Attempt reconnection |
| `1011` | Server error | Contact support |

## JavaScript Integration Examples

### Basic Connection

```javascript
const socket = new WebSocket('ws://localhost:8000/ws/admin/activity/?token=YOUR_TOKEN');

socket.onopen = () => console.log('Connected');
socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
socket.onclose = () => console.log('Disconnected');
socket.onerror = (error) => console.error('Error:', error);
```

### Activity Feed Handler

```javascript
function handleActivityUpdate(data) {
    const activity = data.data;
    const feed = document.getElementById('activity-feed');
    
    const item = document.createElement('div');
    item.className = 'activity-item';
    item.innerHTML = `
        <div class="icon" style="color: ${activity.color}">
            <i class="fas fa-${activity.icon}"></i>
        </div>
        <div class="content">
            <h4>${activity.title}</h4>
            <p>${activity.description}</p>
            <small>${new Date(activity.timestamp).toLocaleString()}</small>
        </div>
    `;
    
    feed.insertBefore(item, feed.firstChild);
}
```

### Notification Handler

```javascript
function handleNotification(data) {
    const notification = data.data;
    
    // Show toast notification
    showToast({
        title: notification.message,
        type: notification.status === 'approved' ? 'success' : 'error',
        duration: 10000
    });
    
    // Update UI
    updateAccountStatus(notification.status);
}
```

## CSS Classes for Styling

```css
/* Connection Status */
.connection-status.connected { background: #10B981; color: white; }
.connection-status.disconnected { background: #EF4444; color: white; }
.connection-status.error { background: #F59E0B; color: white; }

/* Activity Items */
.activity-item { display: flex; padding: 12px; border-bottom: 1px solid #eee; }
.activity-icon { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 12px; }
.activity-content { flex: 1; }
.activity-title { font-weight: 600; margin-bottom: 4px; }
.activity-description { color: #666; font-size: 14px; }
.activity-time { color: #999; font-size: 12px; }

/* Notifications */
.toast { position: fixed; top: 20px; right: 20px; padding: 16px; border-radius: 8px; color: white; z-index: 1000; }
.toast-success { background: #10B981; }
.toast-error { background: #EF4444; }
.toast-info { background: #3B82F6; }
.toast-warning { background: #F59E0B; }
```

## Testing Commands

```bash
# Test WebSocket connection
curl -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Upgrade: websocket" \
     -H "Connection: Upgrade" \
     http://localhost:8000/ws/admin/activity/

# Test activity endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/admin/activities/recent/?limit=10
```

## Troubleshooting

### Common Issues

**"No route found for path 'admin/activity/'"**
- ✅ **Fixed**: Added compatibility routes
- Use either `/ws/admin/activity/` or `/admin/activity/`
- Both routes now work

**"Authentication failed"**
- Check JWT token is valid and not expired
- Ensure user has correct permissions (superuser for admin, vendor for vendor routes, etc.)

**"Connection refused"**
- Verify Django server is running with Daphne
- Check WebSocket URL is correct
- Ensure no firewall blocking WebSocket connections

## Production Checklist

- [ ] Use WSS (secure WebSocket) in production
- [ ] Implement proper error handling
- [ ] Add reconnection logic
- [ ] Test with different network conditions
- [ ] Implement rate limiting
- [ ] Add proper logging
- [ ] Test authentication flow
- [ ] Validate all incoming messages
- [ ] Handle connection drops gracefully
- [ ] Implement proper cleanup on page unload
