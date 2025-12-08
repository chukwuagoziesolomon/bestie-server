# JWT Token Configuration & Usage Guide

## Token Lifetimes (Updated December 7, 2025)

### Access Token
- **Lifetime**: 24 hours (1 day)
- **Purpose**: Used for API authentication
- **Usage**: Include in Authorization header for all protected API requests

### Refresh Token
- **Lifetime**: 30 days
- **Purpose**: Used to obtain new access tokens without re-login
- **Auto-rotation**: Enabled - Each refresh generates a new refresh token
- **Blacklisting**: Old refresh tokens are automatically blacklisted after use

## API Endpoints

### Login
```
POST /api/user/login/
```

**Request:**
```json
{
    "email": "user@example.com",
    "password": "password123"
}
```

**Response:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": {
        "id": 1,
        "email": "user@example.com",
        "username": "user123"
    }
}
```

### Refresh Token
```
POST /api/token/refresh/
```

**Request:**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."  // New refresh token
}
```

### Token Verification
```
POST /api/token/verify/
```

**Request:**
```json
{
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response:**
```json
{}  // Empty response means token is valid
```

## Frontend Implementation

### Token Storage
Store both tokens securely in the browser:

```javascript
// After successful login
const handleLogin = async (email, password) => {
    const response = await fetch('http://127.0.0.1:8000/api/user/login/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    
    // Store tokens
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
    localStorage.setItem('user', JSON.stringify(data.user));
};
```

### Automatic Token Refresh

Implement automatic token refresh before the access token expires:

```javascript
// Token refresh function
const refreshAccessToken = async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (!refreshToken) {
        // No refresh token, redirect to login
        window.location.href = '/login';
        return null;
    }
    
    try {
        const response = await fetch('http://127.0.0.1:8000/api/token/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh: refreshToken })
        });
        
        if (response.ok) {
            const data = await response.json();
            // Update stored tokens
            localStorage.setItem('access_token', data.access);
            localStorage.setItem('refresh_token', data.refresh);
            return data.access;
        } else {
            // Refresh token is invalid or expired
            localStorage.clear();
            window.location.href = '/login';
            return null;
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
        return null;
    }
};

// Axios interceptor for automatic token refresh
import axios from 'axios';

const api = axios.create({
    baseURL: 'http://127.0.0.1:8000/api'
});

// Request interceptor - Add token to all requests
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor - Handle 401 errors
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        
        // If 401 error and we haven't already tried to refresh
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;
            
            const newAccessToken = await refreshAccessToken();
            
            if (newAccessToken) {
                // Retry original request with new token
                originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
                return api(originalRequest);
            }
        }
        
        return Promise.reject(error);
    }
);

export default api;
```

### Using the API Client

```javascript
// Example: Fetch user recommendations
import api from './api';

const getRecommendations = async (city) => {
    try {
        const response = await api.get('/user/recommendations/', {
            params: { city, limit: 20 }
        });
        return response.data;
    } catch (error) {
        console.error('Failed to fetch recommendations:', error);
        throw error;
    }
};
```

### Proactive Token Refresh

Refresh token before it expires (recommended):

```javascript
// Check and refresh token every 23 hours (1 hour before expiry)
const TOKEN_REFRESH_INTERVAL = 23 * 60 * 60 * 1000; // 23 hours in milliseconds

const startTokenRefreshTimer = () => {
    setInterval(async () => {
        const token = localStorage.getItem('access_token');
        if (token) {
            await refreshAccessToken();
        }
    }, TOKEN_REFRESH_INTERVAL);
};

// Start timer when app loads
startTokenRefreshTimer();
```

## Error Handling

### Common Error Scenarios

#### 1. Access Token Expired (401)
```json
{
    "detail": "Given token not valid for any token type",
    "code": "token_not_valid",
    "messages": [
        {
            "token_class": "AccessToken",
            "token_type": "access",
            "message": "Token is invalid or expired"
        }
    ]
}
```
**Solution**: Automatically refresh using refresh token

#### 2. Refresh Token Expired (401)
```json
{
    "detail": "Token is invalid or expired",
    "code": "token_not_valid"
}
```
**Solution**: Redirect user to login page

#### 3. Blacklisted Token (401)
```json
{
    "detail": "Token is blacklisted",
    "code": "token_not_valid"
}
```
**Solution**: Token was already used/rotated, redirect to login

## Security Best Practices

1. **Store Tokens Securely**
   - Use `localStorage` for web apps (or `httpOnly` cookies for better security)
   - Never expose tokens in URLs
   - Clear tokens on logout

2. **Handle Token Rotation**
   - Always update both access and refresh tokens after refresh
   - Old refresh tokens are automatically blacklisted

3. **Implement Logout**
```javascript
const logout = async () => {
    // Optional: Call backend logout endpoint if you implement one
    // await api.post('/user/logout/');
    
    // Clear all stored tokens
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    
    // Redirect to login
    window.location.href = '/login';
};
```

4. **Validate Token on App Load**
```javascript
const validateToken = async () => {
    const token = localStorage.getItem('access_token');
    
    if (!token) {
        return false;
    }
    
    try {
        const response = await fetch('http://127.0.0.1:8000/api/token/verify/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ token })
        });
        
        if (response.ok) {
            return true;
        } else {
            // Token invalid, try to refresh
            const newToken = await refreshAccessToken();
            return newToken !== null;
        }
    } catch (error) {
        console.error('Token validation failed:', error);
        return false;
    }
};
```

## Migration Guide

If users are experiencing 401 errors after this update:

1. **Existing tokens will remain valid until their original expiry**
2. **New logins will use the updated 24-hour access token lifetime**
3. **Users should log out and log back in to get new tokens with updated settings**

## Testing Token Functionality

### Test Token Expiry
```bash
# Get token
curl -X POST http://127.0.0.1:8000/api/user/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Use access token
curl http://127.0.0.1:8000/api/user/recommendations/?city=Lagos \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Refresh token
curl -X POST http://127.0.0.1:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "YOUR_REFRESH_TOKEN"}'
```

## Summary

- **Access Token**: 24 hours (increased from 1 hour)
- **Refresh Token**: 30 days (increased from 7 days)
- **Auto-rotation**: Enabled for refresh tokens
- **Blacklisting**: Enabled to prevent token reuse
- **Frontend**: Must implement automatic token refresh on 401 errors
- **User Experience**: Users stay logged in for up to 30 days without re-entering credentials
