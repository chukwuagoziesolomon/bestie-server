# 🔐 Multi-Role Authentication - Frontend Integration Guide

**System:** Bestyy Multi-Role Authentication System  
**Date:** November 21, 2025  
**Status:** ✅ Production Ready

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [API Endpoints](#api-endpoints)
3. [Authentication Flow](#authentication-flow)
4. [Registration Flow](#registration-flow)
5. [Login Flow](#login-flow)
6. [Code Examples](#code-examples)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)

---

## 🎯 Overview

The Bestyy authentication system supports **multiple roles with the same email/phone**:
- **User** (Customer) - Orders food
- **Vendor** (Restaurant/Shop) - Sells food
- **Courier** (Delivery) - Delivers orders

### Key Features:
- ✅ Same email/phone can have multiple roles
- ✅ User role has **instant registration** (no verification)
- ✅ Vendor/Courier roles require **WhatsApp verification**
- ✅ Multiple profiles require **profile selection** at login
- ✅ JWT-based authentication with refresh tokens

---

## 🔌 API Endpoints

### Base URL
```
https://your-api-domain.com/api/user/
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register/multi-role/` | Register for one or multiple roles (same email can have User, Vendor, Courier) |
| POST | `/login/` | Login with email/password - Returns tokens OR list of profiles if multiple roles exist |
| POST | `/login/select-profile/` | Select specific profile when user has multiple roles (User + Vendor + Courier) |

### 🔍 Understanding the Two Login Flows:

**Simple Login Flow (Single Role):**
- User has only registered as one role (e.g., only "User")
- `/login/` endpoint returns JWT tokens immediately
- No profile selection needed

**Multi-Role Login Flow (Multiple Profiles):**
- User has registered for multiple roles (e.g., "User" + "Vendor")
- `/login/` endpoint returns a list of available profiles
- User must call `/login/select-profile/` to choose which role to use
- Then receives JWT tokens for the selected role

---

## 🔄 Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    REGISTRATION FLOW                         │
└─────────────────────────────────────────────────────────────┘

User Role (Instant - No Verification):
├── POST /register/multi-role/ with role: ["user"]
├── Immediate account creation ✅
├── Receive JWT tokens automatically
└── Can login and use app immediately

Vendor/Courier Role (Requires WhatsApp Verification):
├── POST /register/multi-role/ with role: ["vendor"] or ["courier"]
├── Pending user created (not activated yet)
├── Receive 6-digit verification code
├── Send "VERIFY 123456" to WhatsApp
├── Account activated ✅
└── Can now login with email/password

Multi-Role Registration (Same Email, Multiple Roles):
├── User registers as "user" → Instant ✅
├── Same user registers as "vendor" → Needs verification
├── Same user registers as "courier" → Needs verification
└── Now has 3 profiles under one email address

┌─────────────────────────────────────────────────────────────┐
│                      LOGIN FLOW                              │
└─────────────────────────────────────────────────────────────┘

Scenario 1: Single Role (e.g., only "User")
├── POST /login/ with email + password
├── Backend finds only ONE role for this email
├── Response: JWT tokens + user profile ✅
└── Frontend: Store tokens, redirect to dashboard

Scenario 2: Multiple Roles (e.g., "User" + "Vendor" + "Courier")
├── POST /login/ with email + password
├── Backend finds MULTIPLE roles for this email
├── Response: List of all profiles (no tokens yet) 📋
├── Frontend: Show profile selector UI
├── User clicks on desired role (e.g., "Vendor")
├── POST /login/select-profile/ with profile_id
├── Response: JWT tokens for selected role ✅
└── Frontend: Store tokens, redirect to role-specific dashboard
```

---

## 🎭 Understanding Multi-Role vs Profile Selection

### What's the Difference?

**Multi-Role Registration** = Same person can register for multiple roles using the **same email and password**

Example:
- John registers as **User** (customer) with `john@example.com`
- Later, John opens a restaurant and registers as **Vendor** with `john@example.com` (same email!)
- John can also register as **Courier** with `john@example.com` (same email!)
- Result: John has **3 separate profiles** under one email

### Why Two Login Endpoints?

1. **`POST /login/`** - Initial login attempt
   - Checks how many roles/profiles exist for the email
   - If **one role** → Returns tokens immediately
   - If **multiple roles** → Returns list of profiles (no tokens yet)

2. **`POST /login/select-profile/`** - Profile selection (only needed for multi-role users)
   - User picks which role they want to use (User, Vendor, or Courier)
   - Backend generates tokens for that specific role
   - User accesses the app with that role's permissions

### Real-World Example:

```
John's Email: john@example.com
Password: SecurePass123!

Registered Roles:
✅ User (Profile ID: 100)
✅ Vendor (Profile ID: 101) - "John's Kitchen"
✅ Courier (Profile ID: 102) - Motorcycle delivery

Login Flow:
1. John enters: john@example.com + SecurePass123!
2. POST /login/ → Backend finds 3 profiles
3. Frontend shows: "Which profile do you want to use?"
   - 🛒 Customer (User)
   - 🍳 John's Kitchen (Vendor)
   - 🏍️ Delivery (Courier)
4. John clicks "John's Kitchen (Vendor)"
5. POST /login/select-profile/ with profile_id: 101
6. Receives tokens for Vendor role
7. Redirected to /vendor/dashboard
```

---

## 📝 Registration Flow

### 1. Simple User Registration (Instant)

**Endpoint:** `POST /api/user/register/multi-role/`

**Request Body (Minimal):**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!"
}
```

**Request Body (Complete):**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!",
  "phone": "+2348012345678",
  "first_name": "John",
  "last_name": "Doe",
  "roles": ["user"]
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "message": "User account created successfully.",
  "user": {
    "id": 123,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "user",
    "phone": "+2348012345678"
  },
  "tokens": {
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

### 2. Vendor Registration (Requires Verification)

**Endpoint:** `POST /api/user/register/multi-role/`

**Request Body:**
```json
{
  "email": "vendor@example.com",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!",
  "phone": "+2348012345678",
  "first_name": "Restaurant",
  "last_name": "Owner",
  "roles": ["vendor"],
  "business_name": "John's Kitchen",
  "business_category": "Nigerian Cuisine",
  "business_address": "123 Main Street, Lagos",
  "delivery_radius": 10,
  "service_areas": "Lagos Island, Victoria Island",
  "opening_hours": "09:00:00",
  "closing_hours": "22:00:00",
  "cac_number": "RC123456",
  "tin_number": "TIN123456"
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "pending_user_id": 456,
  "verification_code": "543210",
  "phone": "+2348012345678",
  "roles": ["vendor"],
  "message": "Send 'VERIFY 543210' to WhatsApp number +2348012345678"
}
```

**Frontend Action:** Display verification instructions to user.

### 3. Courier Registration (Requires Verification)

**Endpoint:** `POST /api/user/register/multi-role/`

**Request Body:**
```json
{
  "email": "courier@example.com",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!",
  "phone": "+2348012345678",
  "first_name": "Delivery",
  "last_name": "Person",
  "roles": ["courier"],
  "vehicle_type": "motorcycle",
  "license_number": "LIC123456",
  "vehicle_registration": "ABC123XY",
  "availability_status": "available"
}
```

**Success Response (201 Created):**
```json
{
  "success": true,
  "pending_user_id": 789,
  "verification_code": "678901",
  "phone": "+2348012345678",
  "roles": ["courier"],
  "message": "Send 'VERIFY 678901' to WhatsApp number +2348012345678"
}
```

### 4. Multi-Role Registration (User + Vendor)

**Request Body:**
```json
{
  "email": "multi@example.com",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!",
  "phone": "+2348012345678",
  "first_name": "Multi",
  "last_name": "Role",
  "roles": ["user", "vendor"],
  "business_name": "Multi's Kitchen",
  "business_category": "Fast Food",
  "business_address": "456 Market Street, Abuja",
  "opening_hours": "08:00:00",
  "closing_hours": "20:00:00"
}
```

**Success Response:** Same as vendor registration (requires verification).

---

## 🔑 Login Flow

### 1. Login with Single Profile

**Endpoint:** `POST /api/user/login/`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Success Response (200 OK):**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 123,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "user",
    "phone": "+2348012345678"
  },
  "multiple_profiles": false
}
```

**Frontend Action:** Store tokens and redirect to dashboard.

### 2. Login with Multiple Profiles

**Endpoint:** `POST /api/user/login/`

**Request Body:**
```json
{
  "email": "multi@example.com",
  "password": "SecurePass123!"
}
```

**Success Response (200 OK):**
```json
{
  "multiple_profiles": true,
  "message": "Multiple profiles found. Please select one to continue.",
  "profiles": [
    {
      "id": 123,
      "email": "multi@example.com",
      "first_name": "Multi",
      "last_name": "Role",
      "role": "user",
      "phone": "+2348012345678"
    },
    {
      "id": 124,
      "email": "multi@example.com",
      "first_name": "Multi",
      "last_name": "Role",
      "role": "vendor",
      "phone": "+2348012345678",
      "vendor_info": {
        "id": 45,
        "business_name": "Multi's Kitchen",
        "is_verified": true,
        "business_category": "Fast Food"
      }
    },
    {
      "id": 125,
      "email": "multi@example.com",
      "first_name": "Multi",
      "last_name": "Role",
      "role": "courier",
      "phone": "+2348012345678",
      "courier_info": {
        "id": 67,
        "is_verified": true,
        "is_available": true,
        "vehicle_type": "motorcycle"
      }
    }
  ]
}
```

**Frontend Action:** Show profile selector UI.

### 3. Select Specific Profile

**Endpoint:** `POST /api/user/login/select-profile/`

**Request Body:**
```json
{
  "email": "multi@example.com",
  "password": "SecurePass123!",
  "profile_id": 124
}
```

**Success Response (200 OK):**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 124,
    "email": "multi@example.com",
    "first_name": "Multi",
    "last_name": "Role",
    "role": "vendor",
    "phone": "+2348012345678",
    "vendor_info": {
      "business_name": "Multi's Kitchen",
      "is_verified": true
    }
  }
}
```

**Frontend Action:** Store tokens and redirect to vendor dashboard.

---

## 💻 Code Examples

### React/Next.js Example

#### 1. Registration Hook

```typescript
// hooks/useRegistration.ts
import { useState } from 'react';
import axios from 'axios';

const API_BASE = 'https://your-api-domain.com/api/user';

interface UserRegistrationData {
  email: string;
  password: string;
  confirm_password: string;
  phone?: string;
  first_name?: string;
  last_name?: string;
}

interface VendorRegistrationData extends UserRegistrationData {
  roles: ['vendor'];
  business_name: string;
  business_category: string;
  business_address: string;
  opening_hours: string;
  closing_hours: string;
  delivery_radius?: number;
  service_areas?: string;
  cac_number?: string;
  tin_number?: string;
}

export const useRegistration = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const registerUser = async (data: UserRegistrationData) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post(`${API_BASE}/register/multi-role/`, data);
      
      if (response.data.success) {
        // User registered successfully with tokens
        localStorage.setItem('access_token', response.data.tokens.access);
        localStorage.setItem('refresh_token', response.data.tokens.refresh);
        localStorage.setItem('user', JSON.stringify(response.data.user));
        return { success: true, data: response.data };
      }
      
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || 'Registration failed';
      setError(errorMsg);
      return { success: false, error: errorMsg };
    } finally {
      setLoading(false);
    }
  };

  const registerVendor = async (data: VendorRegistrationData) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post(`${API_BASE}/register/multi-role/`, data);
      
      if (response.data.success) {
        // Vendor registration pending verification
        return { 
          success: true, 
          needsVerification: true,
          verificationCode: response.data.verification_code,
          phone: response.data.phone,
          message: response.data.message
        };
      }
      
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || 'Registration failed';
      setError(errorMsg);
      return { success: false, error: errorMsg };
    } finally {
      setLoading(false);
    }
  };

  return { registerUser, registerVendor, loading, error };
};
```

#### 2. Login Hook

```typescript
// hooks/useLogin.ts
import { useState } from 'react';
import axios from 'axios';

const API_BASE = 'https://your-api-domain.com/api/user';

interface LoginCredentials {
  email: string;
  password: string;
}

interface ProfileSelectData {
  email: string;
  password: string;
  profile_id: number;
}

export const useLogin = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = async (credentials: LoginCredentials) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post(`${API_BASE}/login/`, credentials);
      
      if (response.data.multiple_profiles) {
        // User has multiple profiles - return profiles for selection
        return {
          success: true,
          multipleProfiles: true,
          profiles: response.data.profiles,
          message: response.data.message
        };
      } else {
        // Single profile - store tokens and user data
        localStorage.setItem('access_token', response.data.access);
        localStorage.setItem('refresh_token', response.data.refresh);
        localStorage.setItem('user', JSON.stringify(response.data.user));
        
        return {
          success: true,
          multipleProfiles: false,
          user: response.data.user
        };
      }
      
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || 'Login failed';
      setError(errorMsg);
      return { success: false, error: errorMsg };
    } finally {
      setLoading(false);
    }
  };

  const selectProfile = async (data: ProfileSelectData) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post(`${API_BASE}/login/select-profile/`, data);
      
      // Store tokens and user data
      localStorage.setItem('access_token', response.data.access);
      localStorage.setItem('refresh_token', response.data.refresh);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      
      return {
        success: true,
        user: response.data.user
      };
      
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || 'Profile selection failed';
      setError(errorMsg);
      return { success: false, error: errorMsg };
    } finally {
      setLoading(false);
    }
  };

  return { login, selectProfile, loading, error };
};
```

#### 3. User Registration Component

```tsx
// components/UserRegistrationForm.tsx
import React, { useState } from 'react';
import { useRegistration } from '@/hooks/useRegistration';
import { useRouter } from 'next/navigation';

export const UserRegistrationForm = () => {
  const router = useRouter();
  const { registerUser, loading, error } = useRegistration();
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirm_password: '',
    phone: '',
    first_name: '',
    last_name: ''
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const result = await registerUser(formData);
    
    if (result.success) {
      // Registration successful - redirect to dashboard
      router.push('/dashboard');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-2xl font-bold">Sign Up as Customer</h2>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}
      
      <input
        type="email"
        placeholder="Email"
        value={formData.email}
        onChange={(e) => setFormData({...formData, email: e.target.value})}
        required
        className="w-full px-4 py-2 border rounded"
      />
      
      <input
        type="tel"
        placeholder="Phone (e.g., +2348012345678)"
        value={formData.phone}
        onChange={(e) => setFormData({...formData, phone: e.target.value})}
        className="w-full px-4 py-2 border rounded"
      />
      
      <input
        type="text"
        placeholder="First Name"
        value={formData.first_name}
        onChange={(e) => setFormData({...formData, first_name: e.target.value})}
        className="w-full px-4 py-2 border rounded"
      />
      
      <input
        type="text"
        placeholder="Last Name"
        value={formData.last_name}
        onChange={(e) => setFormData({...formData, last_name: e.target.value})}
        className="w-full px-4 py-2 border rounded"
      />
      
      <input
        type="password"
        placeholder="Password"
        value={formData.password}
        onChange={(e) => setFormData({...formData, password: e.target.value})}
        required
        className="w-full px-4 py-2 border rounded"
      />
      
      <input
        type="password"
        placeholder="Confirm Password"
        value={formData.confirm_password}
        onChange={(e) => setFormData({...formData, confirm_password: e.target.value})}
        required
        className="w-full px-4 py-2 border rounded"
      />
      
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
      >
        {loading ? 'Creating Account...' : 'Sign Up'}
      </button>
    </form>
  );
};
```

#### 4. Login Component with Profile Selection

```tsx
// components/LoginForm.tsx
import React, { useState } from 'react';
import { useLogin } from '@/hooks/useLogin';
import { useRouter } from 'next/navigation';

interface Profile {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  phone: string;
  vendor_info?: any;
  courier_info?: any;
}

export const LoginForm = () => {
  const router = useRouter();
  const { login, selectProfile, loading, error } = useLogin();
  
  const [credentials, setCredentials] = useState({
    email: '',
    password: ''
  });
  
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [showProfileSelector, setShowProfileSelector] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const result = await login(credentials);
    
    if (result.success) {
      if (result.multipleProfiles) {
        // Show profile selector
        setProfiles(result.profiles || []);
        setShowProfileSelector(true);
      } else {
        // Single profile - redirect based on role
        redirectToDashboard(result.user.role);
      }
    }
  };

  const handleProfileSelect = async (profileId: number) => {
    const result = await selectProfile({
      email: credentials.email,
      password: credentials.password,
      profile_id: profileId
    });
    
    if (result.success) {
      redirectToDashboard(result.user.role);
    }
  };

  const redirectToDashboard = (role: string) => {
    switch (role) {
      case 'vendor':
        router.push('/vendor/dashboard');
        break;
      case 'courier':
        router.push('/courier/dashboard');
        break;
      default:
        router.push('/dashboard');
    }
  };

  if (showProfileSelector) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">Select Your Profile</h2>
        <p className="text-gray-600">You have multiple profiles. Choose one to continue.</p>
        
        <div className="space-y-3">
          {profiles.map((profile) => (
            <button
              key={profile.id}
              onClick={() => handleProfileSelect(profile.id)}
              disabled={loading}
              className="w-full p-4 border rounded-lg hover:bg-gray-50 text-left"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold">
                    {profile.first_name} {profile.last_name}
                  </div>
                  <div className="text-sm text-gray-600 capitalize">
                    {profile.role}
                    {profile.role === 'vendor' && profile.vendor_info && 
                      ` - ${profile.vendor_info.business_name}`
                    }
                  </div>
                </div>
                <div className="text-blue-600">→</div>
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleLogin} className="space-y-4">
      <h2 className="text-2xl font-bold">Login</h2>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}
      
      <input
        type="email"
        placeholder="Email"
        value={credentials.email}
        onChange={(e) => setCredentials({...credentials, email: e.target.value})}
        required
        className="w-full px-4 py-2 border rounded"
      />
      
      <input
        type="password"
        placeholder="Password"
        value={credentials.password}
        onChange={(e) => setCredentials({...credentials, password: e.target.value})}
        required
        className="w-full px-4 py-2 border rounded"
      />
      
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
      >
        {loading ? 'Logging in...' : 'Login'}
      </button>
    </form>
  );
};
```

#### 5. Axios Interceptor for Token Management

```typescript
// lib/axios.ts
import axios from 'axios';

const API_BASE = 'https://your-api-domain.com';

const axiosInstance = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post(`${API_BASE}/api/token/refresh/`, {
          refresh: refreshToken,
        });

        const { access } = response.data;
        localStorage.setItem('access_token', access);

        originalRequest.headers.Authorization = `Bearer ${access}`;
        return axiosInstance(originalRequest);
      } catch (refreshError) {
        // Refresh failed - logout user
        localStorage.clear();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default axiosInstance;
```

### Vue.js Example

```typescript
// composables/useAuth.ts
import { ref } from 'vue';
import axios from 'axios';

const API_BASE = 'https://your-api-domain.com/api/user';

export const useAuth = () => {
  const loading = ref(false);
  const error = ref<string | null>(null);

  const registerUser = async (data: any) => {
    loading.value = true;
    error.value = null;
    
    try {
      const response = await axios.post(`${API_BASE}/register/multi-role/`, data);
      
      if (response.data.success) {
        localStorage.setItem('access_token', response.data.tokens.access);
        localStorage.setItem('refresh_token', response.data.tokens.refresh);
        localStorage.setItem('user', JSON.stringify(response.data.user));
        return { success: true, data: response.data };
      }
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Registration failed';
      return { success: false, error: error.value };
    } finally {
      loading.value = false;
    }
  };

  const login = async (credentials: { email: string; password: string }) => {
    loading.value = true;
    error.value = null;
    
    try {
      const response = await axios.post(`${API_BASE}/login/`, credentials);
      
      if (response.data.multiple_profiles) {
        return {
          success: true,
          multipleProfiles: true,
          profiles: response.data.profiles
        };
      } else {
        localStorage.setItem('access_token', response.data.access);
        localStorage.setItem('refresh_token', response.data.refresh);
        localStorage.setItem('user', JSON.stringify(response.data.user));
        
        return {
          success: true,
          multipleProfiles: false,
          user: response.data.user
        };
      }
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Login failed';
      return { success: false, error: error.value };
    } finally {
      loading.value = false;
    }
  };

  return { registerUser, login, loading, error };
};
```

### Angular Example

```typescript
// services/auth.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

const API_BASE = 'https://your-api-domain.com/api/user';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  constructor(private http: HttpClient) {}

  registerUser(data: any): Observable<any> {
    return this.http.post(`${API_BASE}/register/multi-role/`, data).pipe(
      tap((response: any) => {
        if (response.success && response.tokens) {
          localStorage.setItem('access_token', response.tokens.access);
          localStorage.setItem('refresh_token', response.tokens.refresh);
          localStorage.setItem('user', JSON.stringify(response.user));
        }
      })
    );
  }

  login(credentials: { email: string; password: string }): Observable<any> {
    return this.http.post(`${API_BASE}/login/`, credentials).pipe(
      tap((response: any) => {
        if (!response.multiple_profiles) {
          localStorage.setItem('access_token', response.access);
          localStorage.setItem('refresh_token', response.refresh);
          localStorage.setItem('user', JSON.stringify(response.user));
        }
      })
    );
  }

  selectProfile(data: any): Observable<any> {
    return this.http.post(`${API_BASE}/login/select-profile/`, data).pipe(
      tap((response: any) => {
        localStorage.setItem('access_token', response.access);
        localStorage.setItem('refresh_token', response.refresh);
        localStorage.setItem('user', JSON.stringify(response.user));
      })
    );
  }
}
```

---

## ⚠️ Error Handling

### Common Error Responses

#### 1. Registration Errors

**Duplicate Role:**
```json
{
  "error": "You already have a user account with this email. Please login to access it."
}
```

**Password Mismatch:**
```json
{
  "confirm_password": "Passwords do not match."
}
```

**Missing Vendor Fields:**
```json
{
  "vendor_business_name": "Business Name is required for vendor registration.",
  "vendor_business_category": "Business Category is required for vendor registration.",
  "vendor_business_address": "Business Address is required for vendor registration."
}
```

**Weak Password:**
```json
{
  "password": [
    "This password is too short. It must contain at least 8 characters.",
    "This password is too common."
  ]
}
```

#### 2. Login Errors

**Invalid Credentials:**
```json
{
  "error": "Invalid email or password"
}
```

**Account Disabled:**
```json
{
  "error": "User account is disabled"
}
```

**Profile Not Found:**
```json
{
  "error": "Profile not found"
}
```

### Error Handling in Code

```typescript
try {
  const result = await registerUser(formData);
  
  if (!result.success) {
    // Handle different error types
    if (result.error.includes('already have')) {
      // Show "already registered" message
      showErrorModal('Account exists', result.error);
    } else if (result.error.includes('Password')) {
      // Show password validation errors
      setPasswordError(result.error);
    } else {
      // Generic error
      showErrorToast(result.error);
    }
  }
} catch (error) {
  // Network or unexpected errors
  showErrorToast('Network error. Please try again.');
}
```

---

## ✅ Best Practices

### 1. **Token Storage**
```typescript
// ✅ DO: Store tokens securely
localStorage.setItem('access_token', accessToken);
localStorage.setItem('refresh_token', refreshToken);

// ❌ DON'T: Store in cookies without httpOnly flag (XSS vulnerability)
```

### 2. **Password Requirements**
- Minimum 8 characters
- Must include uppercase and lowercase letters
- Must include numbers
- Should include special characters

### 3. **Phone Number Format**
```typescript
// ✅ DO: Use international format
phone: "+2348012345678"

// ❌ DON'T: Use local format
phone: "08012345678"
```

### 4. **Profile Selection UX**
```typescript
// Show clear profile cards with:
- Role name (User, Vendor, Courier)
- Business name (for vendors)
- Visual icons for each role
- Clear selection buttons
```

### 5. **Loading States**
```typescript
// Show loading indicators during:
- Registration
- Login
- Profile selection
- Token refresh
```

### 6. **Redirect Logic**
```typescript
const redirectAfterLogin = (role: string) => {
  const routes = {
    user: '/dashboard',
    vendor: '/vendor/dashboard',
    courier: '/courier/dashboard',
    admin: '/admin/dashboard'
  };
  
  router.push(routes[role] || '/dashboard');
};
```

### 7. **Token Refresh**
```typescript
// Implement automatic token refresh before expiration
setInterval(() => {
  refreshAccessToken();
}, 14 * 60 * 1000); // Refresh every 14 minutes (tokens expire in 15 min)
```

### 8. **Logout**
```typescript
const logout = () => {
  // Clear all stored data
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
  
  // Redirect to login
  router.push('/login');
};
```

### 9. **Protected Routes**
```typescript
// Create a HOC or middleware to protect routes
const ProtectedRoute = ({ children, allowedRoles }) => {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  
  if (!user.id) {
    return <Navigate to="/login" />;
  }
  
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/unauthorized" />;
  }
  
  return children;
};
```

### 10. **API Error Handling**
```typescript
// Handle specific HTTP status codes
axios.interceptors.response.use(
  response => response,
  error => {
    const status = error.response?.status;
    
    switch (status) {
      case 401:
        // Unauthorized - refresh token or logout
        handleUnauthorized();
        break;
      case 403:
        // Forbidden - show access denied
        showAccessDenied();
        break;
      case 404:
        // Not found
        showNotFound();
        break;
      case 500:
        // Server error
        showServerError();
        break;
      default:
        showGenericError();
    }
    
    return Promise.reject(error);
  }
);
```

---

## 🔒 Security Considerations

1. **HTTPS Only:** Always use HTTPS in production
2. **Token Expiration:** Access tokens expire in 15 minutes
3. **Refresh Tokens:** Stored securely and rotated on refresh
4. **CORS:** Configure CORS properly on backend
5. **Input Validation:** Validate all user inputs client-side and server-side
6. **Password Strength:** Enforce strong password requirements
7. **Rate Limiting:** Backend has rate limiting on auth endpoints
8. **XSS Protection:** Sanitize all user inputs before display

---

## 📱 Mobile App Integration

For React Native or Flutter apps, the integration is similar but with these modifications:

### React Native with AsyncStorage

```typescript
import AsyncStorage from '@react-native-async-storage/async-storage';

// Store tokens
await AsyncStorage.setItem('access_token', accessToken);
await AsyncStorage.setItem('refresh_token', refreshToken);

// Retrieve tokens
const accessToken = await AsyncStorage.getItem('access_token');

// Clear on logout
await AsyncStorage.clear();
```

### Flutter with SharedPreferences

```dart
import 'package:shared_preferences/shared_preferences.dart';

// Store tokens
final prefs = await SharedPreferences.getInstance();
await prefs.setString('access_token', accessToken);
await prefs.setString('refresh_token', refreshToken);

// Retrieve tokens
final accessToken = prefs.getString('access_token');

// Clear on logout
await prefs.clear();
```

---

## 🧪 Testing

### Test User Accounts

```
User Role:
Email: test.user@bestyy.com
Password: TestPass123!

Vendor Role:
Email: test.vendor@bestyy.com
Password: TestPass123!

Multi-Role:
Email: test.multi@bestyy.com
Password: TestPass123!
Profiles: User, Vendor, Courier
```

### Testing Checklist

- [ ] User registration completes instantly
- [ ] Vendor registration shows verification message
- [ ] Login with single profile returns tokens
- [ ] Login with multiple profiles shows selector
- [ ] Profile selection returns correct role tokens
- [ ] Token refresh works automatically
- [ ] Logout clears all stored data
- [ ] Error messages display correctly
- [ ] Loading states show during API calls
- [ ] Redirect logic works for each role

---

## 🎯 Quick Implementation Guide

### Step-by-Step: Implement Multi-Role Login

#### 1️⃣ User Enters Credentials
```typescript
// User submits login form
const credentials = {
  email: "john@example.com",
  password: "SecurePass123!"
};
```

#### 2️⃣ Call Login Endpoint
```typescript
const response = await axios.post('/api/user/login/', credentials);

// Check if user has multiple roles
if (response.data.multiple_profiles === true) {
  // ⚠️ User has multiple roles - need profile selection
  showProfileSelector(response.data.profiles);
} else {
  // ✅ User has single role - got tokens immediately
  storeTokens(response.data.access, response.data.refresh);
  redirectToDashboard(response.data.user.role);
}
```

#### 3️⃣ Show Profile Selector (If Multiple Roles)
```typescript
function showProfileSelector(profiles) {
  // Display UI showing all available roles
  // Example profiles array:
  // [
  //   { id: 100, role: "user", first_name: "John" },
  //   { id: 101, role: "vendor", first_name: "John", vendor_info: {...} },
  //   { id: 102, role: "courier", first_name: "John", courier_info: {...} }
  // ]
  
  // User clicks on one profile
  // Then call select-profile endpoint...
}
```

#### 4️⃣ Call Select Profile Endpoint
```typescript
async function selectProfile(profileId) {
  const response = await axios.post('/api/user/login/select-profile/', {
    email: credentials.email,
    password: credentials.password,
    profile_id: profileId  // e.g., 101 for vendor
  });
  
  // Now we get tokens for the selected role
  storeTokens(response.data.access, response.data.refresh);
  redirectToDashboard(response.data.user.role);
}
```

#### 5️⃣ Store Tokens & Redirect
```typescript
function storeTokens(access, refresh) {
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
}

function redirectToDashboard(role) {
  const dashboards = {
    'user': '/dashboard',
    'vendor': '/vendor/dashboard',
    'courier': '/courier/dashboard'
  };
  router.push(dashboards[role]);
}
```

### Common Mistakes to Avoid

❌ **DON'T** call `/login/select-profile/` if `multiple_profiles` is `false`
```typescript
// WRONG - This will fail
if (response.data.multiple_profiles === false) {
  await axios.post('/api/user/login/select-profile/', {...}); // ❌ No!
}
```

✅ **DO** check `multiple_profiles` flag first
```typescript
// CORRECT
if (response.data.multiple_profiles === true) {
  // Only then call select-profile endpoint
  await axios.post('/api/user/login/select-profile/', {...}); // ✅ Yes!
}
```

❌ **DON'T** store credentials in state longer than necessary
```typescript
// WRONG - Security risk
const [credentials, setCredentials] = useState({ email: '', password: '' });
// Password stored in state permanently ❌
```

✅ **DO** clear credentials after profile selection
```typescript
// CORRECT
const handleProfileSelect = async (profileId) => {
  await selectProfile(profileId);
  setCredentials({ email: '', password: '' }); // Clear credentials ✅
};
```

---

## 📞 Support

For questions or issues with integration:
- **Email:** dev@bestyy.com
- **Documentation:** https://docs.bestyy.com
- **API Status:** https://status.bestyy.com

---

**Last Updated:** November 21, 2025  
**Version:** 2.0  
**Status:** ✅ Production Ready
