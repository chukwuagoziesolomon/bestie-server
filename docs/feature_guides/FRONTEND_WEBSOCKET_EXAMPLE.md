# Frontend WebSocket Implementation Guide

This guide explains how to implement WebSocket connections in your React frontend to receive real-time notifications.

## WebSocket Service

Create a new file `src/services/websocket.js`:

```javascript
/**
 * WebSocket service for handling real-time notifications
 */

class WebSocketService {
  constructor() {
    this.socket = null;
    this.callbacks = {
      onOpen: [],
      onClose: [],
      onError: [],
      onMessage: []
    };
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000; // 3 seconds
  }

  /**
   * Connect to WebSocket server
   * @param {string} path - WebSocket endpoint path (e.g., '/ws/vendor/notifications/')
   * @param {string} token - JWT token for authentication
   */
  connect(path, token) {
    // Close existing connection if any
    if (this.socket) {
      this.disconnect();
    }

    // Build WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.REACT_APP_WS_HOST || window.location.host;
    const url = `${protocol}//${host}${path}?token=${encodeURIComponent(token)}`;

    // Create new WebSocket connection
    this.socket = new WebSocket(url);

    // Set up event handlers
    this.socket.onopen = (event) => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0; // Reset reconnect attempts on successful connection
      this.callbacks.onOpen.forEach(callback => callback(event));
    };

    this.socket.onclose = (event) => {
      console.log('WebSocket disconnected');
      this.callbacks.onClose.forEach(callback => callback(event));
      
      // Attempt to reconnect
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
        setTimeout(() => this.connect(path, token), this.reconnectDelay);
      }
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.callbacks.onError.forEach(callback => callback(error));
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.callbacks.onMessage.forEach(callback => callback(data));
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  /**
   * Register a callback for WebSocket events
   * @param {string} event - Event name ('onOpen', 'onClose', 'onError', 'onMessage')
   * @param {Function} callback - Callback function
   */
  on(event, callback) {
    if (this.callbacks[event]) {
      this.callbacks[event].push(callback);
    }
    return this; // For method chaining
  }

  /**
   * Remove a callback
   * @param {string} event - Event name
   * @param {Function} callback - Callback function to remove
   */
  off(event, callback) {
    if (this.callbacks[event]) {
      this.callbacks[event] = this.callbacks[event].filter(cb => cb !== callback);
    }
    return this;
  }
}

// Create a singleton instance
export const webSocketService = new WebSocketService();
```

## Authentication Hook

Create a custom hook to handle WebSocket connections in your React components:

```javascript
// src/hooks/useWebSocket.js
import { useEffect, useCallback } from 'react';
import { webSocketService } from '../services/websocket';

export function useWebSocket(token, path, callbacks = {}) {
  const { onOpen, onClose, onError, onMessage } = callbacks;

  // Connect to WebSocket when component mounts
  useEffect(() => {
    if (!token || !path) return;

    // Connect to WebSocket
    webSocketService.connect(path, token);

    // Register callbacks
    if (onOpen) webSocketService.on('onOpen', onOpen);
    if (onClose) webSocketService.on('onClose', onClose);
    if (onError) webSocketService.on('onError', onError);
    if (onMessage) webSocketService.on('onMessage', onMessage);

    // Cleanup on unmount
    return () => {
      if (onOpen) webSocketService.off('onOpen', onOpen);
      if (onClose) webSocketService.off('onClose', onClose);
      if (onError) webSocketService.off('onError', onError);
      if (onMessage) webSocketService.off('onMessage', onMessage);
      
      // Only disconnect if no other components are using the WebSocket
      // You might want to implement reference counting if needed
      // webSocketService.disconnect();
    };
  }, [token, path, onOpen, onClose, onError, onMessage]);

  // Return the WebSocket service for manual control if needed
  return webSocketService;
}
```

## Example Component

Here's how to use the WebSocket service in a React component:

```jsx
// src/components/VendorNotifications.js
import React, { useState, useCallback } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAuth } from '../contexts/AuthContext'; // Your auth context

const VendorNotifications = () => {
  const { token } = useAuth(); // Get JWT token from your auth context
  const [notifications, setNotifications] = useState([]);

  // Handle incoming WebSocket messages
  const handleMessage = useCallback((message) => {
    console.log('Received notification:', message);
    
    setNotifications(prev => [message, ...prev].slice(0, 50)); // Keep last 50 messages
    
    // Handle different message types
    switch (message.type) {
      case 'verification.approved':
        // Handle vendor approval
        console.log('Vendor approved:', message.data);
        break;
        
      case 'verification.rejected':
        // Handle vendor rejection
        console.log('Vendor rejected:', message.data);
        break;
        
      case 'order.updated':
        // Handle order update
        console.log('Order updated:', message.data);
        break;
        
      default:
        console.log('Unhandled message type:', message.type);
    }
  }, []);

  // Connect to WebSocket
  useWebSocket(token, '/ws/vendor/notifications/', {
    onOpen: () => console.log('Connected to vendor notifications'),
    onClose: () => console.log('Disconnected from vendor notifications'),
    onError: (error) => console.error('WebSocket error:', error),
    onMessage: handleMessage,
  });

  return (
    <div className="notifications-panel">
      <h3>Notifications</h3>
      {notifications.length === 0 ? (
        <p>No notifications</p>
      ) : (
        <ul>
          {notifications.map((notification, index) => (
            <li key={index} className={`notification ${notification.type}`}>
              <strong>{notification.type}</strong>: 
              {notification.data?.message || JSON.stringify(notification.data)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default VendorNotifications;
```

## Admin Dashboard Example

For the admin dashboard, you can listen to admin-specific events:

```jsx
// src/components/AdminDashboard.js
import React, { useState, useCallback } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAuth } from '../contexts/AuthContext';

const AdminDashboard = () => {
  const { token } = useAuth();
  const [activities, setActivities] = useState([]);
  const [pendingVendors, setPendingVendors] = useState(0);

  // Handle incoming admin activities
  const handleMessage = useCallback((message) => {
    console.log('Admin activity:', message);
    
    // Update activities list
    setActivities(prev => [message, ...prev].slice(0, 50));
    
    // Handle specific message types
    switch (message.type) {
      case 'vendor.registered':
        setPendingVendors(prev => prev + 1);
        break;
        
      case 'vendor.approved':
      case 'vendor.rejected':
        setPendingVendors(prev => Math.max(0, prev - 1));
        break;
        
      default:
        break;
    }
  }, []);

  // Connect to admin WebSocket
  useWebSocket(token, '/ws/admin/activity/', {
    onMessage: handleMessage,
  });

  return (
    <div className="admin-dashboard">
      <div className="dashboard-header">
        <h2>Admin Dashboard</h2>
        <div className="stats">
          <div className="stat">
            <h3>Pending Vendors</h3>
            <p>{pendingVendors}</p>
          </div>
          {/* Add more stats as needed */}
        </div>
      </div>
      
      <div className="activity-feed">
        <h3>Recent Activities</h3>
        {activities.length === 0 ? (
          <p>No recent activities</p>
        ) : (
          <ul>
            {activities.map((activity, index) => (
              <li key={index} className={`activity ${activity.type}`}>
                <span className="activity-type">{activity.type}</span>
                <span className="activity-message">
                  {activity.data?.message || JSON.stringify(activity.data)}
                </span>
                <span className="activity-time">
                  {new Date(activity.timestamp).toLocaleTimeString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;
```

## Environment Variables

Add these to your `.env` file in the frontend:

```env
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_WS_HOST=localhost:8000  # WebSocket server host
```

## Styling

Add some basic styling for notifications and activities:

```css
/* src/styles/notifications.css */
.notifications-panel {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.notifications-panel h3 {
  margin-top: 0;
  color: #333;
  border-bottom: 1px solid #ddd;
  padding-bottom: 10px;
}

.notifications-panel ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.notifications-panel li {
  padding: 10px;
  margin: 5px 0;
  background: white;
  border-left: 4px solid #4CAF50;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.notifications-panel li.verification.rejected {
  border-left-color: #f44336;
}

/* Activity feed styles */
.activity-feed {
  margin-top: 20px;
}

.activity {
  display: flex;
  justify-content: space-between;
  padding: 10px;
  margin: 5px 0;
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.activity-type {
  font-weight: bold;
  color: #2196F3;
  margin-right: 10px;
}

.activity-time {
  color: #666;
  font-size: 0.9em;
}
```

## Connecting to the Backend

Make sure your backend is running and the WebSocket server is accessible. The frontend will automatically connect to the WebSocket server when a component using the `useWebSocket` hook mounts.

## Testing

1. Start your React development server:
   ```bash
   npm start
   ```

2. Open the application in your browser and log in as a vendor or admin.

3. Open the browser's developer tools and check the console for WebSocket connection messages.

4. Test the WebSocket connection by performing actions that trigger notifications (e.g., vendor registration, approval, etc.).

## Production Deployment

For production, make sure to:

1. Configure proper WebSocket proxy settings in your web server (Nginx/Apache).
2. Use secure WebSocket (WSS) when using HTTPS.
3. Handle reconnection logic appropriately.
4. Implement proper error handling and user feedback.
5. Consider rate limiting and other security measures.

## Troubleshooting

- **Connection refused**: Make sure the WebSocket server is running and accessible.
- **Authentication failed**: Verify that the JWT token is valid and included in the WebSocket connection URL.
- **CORS issues**: Check that the backend allows WebSocket connections from your frontend's origin.
- **SSL/TLS issues**: When using WSS, ensure your SSL certificate is valid and properly configured.
