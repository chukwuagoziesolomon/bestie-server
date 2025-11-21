# Cart API Quick Reference

## Base URL
```
https://bestyy-server.onrender.com/api/user/website-cart/
```

---

## 🛒 Add to Cart

**Endpoint:** `POST /api/user/website-cart/add/`

**Request:**
```json
{
  "product_id": 123,
  "quantity": 2,
  "cart_token": "uuid-string"  // Optional for first request
}
```

**Response:**
```json
{
  "success": true,
  "cart_token": "uuid-string",  // ⚠️ SAVE THIS!
  "message": "Product added to cart",
  "total_items": 2,
  "total_amount": 3000.00,
  "product": {
    "id": 123,
    "name": "Jollof Rice",
    "quantity": 2,
    "price": 1500.00,
    "subtotal": 3000.00
  }
}
```

**JavaScript Example:**
```javascript
const addToCart = async (productId, quantity = 1) => {
  const cartToken = localStorage.getItem('cart_token');
  
  const response = await fetch('/api/user/website-cart/add/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      product_id: productId,
      quantity: quantity,
      cart_token: cartToken  // null on first request
    })
  });
  
  const data = await response.json();
  
  if (data.success && data.cart_token) {
    // ⚠️ CRITICAL: Save token for future requests
    localStorage.setItem('cart_token', data.cart_token);
  }
  
  return data;
};
```

---

## 📋 Get Cart Items

**Endpoint:** `GET /api/user/website-cart/`

**Option 1: Query Parameter**
```
GET /api/user/website-cart/?cart_token=uuid-string
```

**Option 2: Header (Recommended)**
```
GET /api/user/website-cart/
Headers: { "X-Cart-Token": "uuid-string" }
```

**Response:**
```json
{
  "success": true,
  "cart_token": "uuid-string",
  "products": [
    {
      "id": 123,
      "name": "Jollof Rice",
      "vendor": {
        "id": 1,
        "name": "Mama's Kitchen"
      },
      "image": "https://...",
      "price": 1500.00,
      "quantity": 2,
      "subtotal": 3000.00,
      "added_at": "2025-11-20T10:30:00Z"
    }
  ],
  "total_items": 2,
  "total_amount": 3000.00,
  "currency": "NGN"
}
```

**JavaScript Example:**
```javascript
const getCart = async () => {
  const cartToken = localStorage.getItem('cart_token');
  if (!cartToken) return { products: [], total_items: 0 };
  
  const response = await fetch('/api/user/website-cart/', {
    headers: {
      'X-Cart-Token': cartToken
    }
  });
  
  return await response.json();
};
```

---

## 🔄 Update Item Quantity

**Endpoint:** `POST /api/user/website-cart/update/`

**Request:**
```json
{
  "product_id": 123,
  "quantity": 5,
  "cart_token": "uuid-string"
}
```

**Response:**
```json
{
  "success": true,
  "cart_token": "uuid-string",
  "product": {
    "id": 123,
    "name": "Jollof Rice",
    "quantity": 5,
    "price": 1500.00,
    "subtotal": 7500.00
  }
}
```

**JavaScript Example:**
```javascript
const updateQuantity = async (productId, quantity) => {
  const cartToken = localStorage.getItem('cart_token');
  
  const response = await fetch('/api/user/website-cart/update/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      product_id: productId,
      quantity: quantity,
      cart_token: cartToken
    })
  });
  
  return await response.json();
};
```

---

## 🗑️ Remove Item

**Endpoint:** `POST /api/user/website-cart/remove/`

**Request:**
```json
{
  "product_id": 123,
  "cart_token": "uuid-string"
}
```

**Response:**
```json
{
  "success": true,
  "cart_token": "uuid-string",
  "message": "Product removed from cart"
}
```

**JavaScript Example:**
```javascript
const removeItem = async (productId) => {
  const cartToken = localStorage.getItem('cart_token');
  
  const response = await fetch('/api/user/website-cart/remove/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      product_id: productId,
      cart_token: cartToken
    })
  });
  
  return await response.json();
};
```

---

## 🧹 Clear Cart

**Endpoint:** `POST /api/user/website-cart/clear/`

**Request:**
```json
{
  "cart_token": "uuid-string"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Cart cleared"
}
```

**JavaScript Example:**
```javascript
const clearCart = async () => {
  const cartToken = localStorage.getItem('cart_token');
  
  const response = await fetch('/api/user/website-cart/clear/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cart_token: cartToken
    })
  });
  
  if (response.ok) {
    localStorage.removeItem('cart_token');
  }
  
  return await response.json();
};
```

---

## 📊 Cart Summary (Quick Count)

**Endpoint:** `GET /api/user/website-cart/summary/`

**Request:**
```
GET /api/user/website-cart/summary/?cart_token=uuid-string
```

**Response:**
```json
{
  "success": true,
  "total_items": 5,
  "total_amount": 12500.00,
  "cart_token": "uuid-string",
  "currency": "NGN"
}
```

**JavaScript Example:**
```javascript
const getCartSummary = async () => {
  const cartToken = localStorage.getItem('cart_token');
  if (!cartToken) return { total_items: 0 };
  
  const response = await fetch(
    `/api/user/website-cart/summary/?cart_token=${cartToken}`
  );
  
  return await response.json();
};

// Use in header badge
<Badge count={summary.total_items}>
  <ShoppingCartIcon />
</Badge>
```

---

## 🔐 Merge Cart After Login

**Endpoint:** `POST /api/user/website-cart/merge/`

**⚠️ Requires Authentication**

**Request:**
```json
{
  "cart_token": "uuid-string"
}
```

**Headers:**
```json
{
  "Authorization": "Bearer JWT_TOKEN",
  "Content-Type": "application/json"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Cart merged successfully",
  "total_items": 5,
  "total_amount": 12500.00
}
```

**JavaScript Example:**
```javascript
const mergeCart = async (jwtToken) => {
  const cartToken = localStorage.getItem('cart_token');
  if (!cartToken) return;
  
  const response = await fetch('/api/user/website-cart/merge/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${jwtToken}`
    },
    body: JSON.stringify({
      cart_token: cartToken
    })
  });
  
  if (response.ok) {
    // Cart merged! Remove old token
    localStorage.removeItem('cart_token');
  }
  
  return await response.json();
};

// Call after login success
const handleLogin = async (credentials) => {
  const loginResponse = await login(credentials);
  const jwtToken = loginResponse.access_token;
  
  // Merge anonymous cart
  await mergeCart(jwtToken);
  
  // Continue with authenticated flow
};
```

---

## ⚠️ Error Handling

**Common Error Responses:**

### Product Not Found (400)
```json
{
  "success": false,
  "error": "Product not found or not available"
}
```

### Stock Exceeded (400)
```json
{
  "success": false,
  "error": "Only 10 items available in stock"
}
```

### Invalid Quantity (400)
```json
{
  "success": false,
  "error": "quantity must be at least 1"
}
```

**Error Handling Example:**
```javascript
const addToCart = async (productId, quantity) => {
  try {
    const response = await fetch('/api/user/website-cart/add/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_id: productId,
        quantity: quantity,
        cart_token: localStorage.getItem('cart_token')
      })
    });
    
    const data = await response.json();
    
    if (!data.success) {
      // Show error message to user
      alert(data.error);
      return null;
    }
    
    // Save token if new
    if (data.cart_token) {
      localStorage.setItem('cart_token', data.cart_token);
    }
    
    return data;
    
  } catch (error) {
    console.error('Cart error:', error);
    alert('Failed to add to cart. Please try again.');
    return null;
  }
};
```

---

## 🎨 React Context Example

```javascript
import React, { createContext, useState, useEffect } from 'react';

export const CartContext = createContext();

export const CartProvider = ({ children }) => {
  const [cartToken, setCartToken] = useState(
    localStorage.getItem('cart_token')
  );
  const [cartItems, setCartItems] = useState([]);
  const [cartSummary, setCartSummary] = useState({
    total_items: 0,
    total_amount: 0
  });

  const loadCart = async () => {
    if (!cartToken) return;
    
    try {
      const response = await fetch('/api/user/website-cart/', {
        headers: { 'X-Cart-Token': cartToken }
      });
      const data = await response.json();
      
      if (data.success) {
        setCartItems(data.products);
        setCartSummary({
          total_items: data.total_items,
          total_amount: data.total_amount
        });
      }
    } catch (error) {
      console.error('Failed to load cart:', error);
    }
  };

  const addToCart = async (productId, quantity = 1) => {
    try {
      const response = await fetch('/api/user/website-cart/add/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: productId,
          quantity,
          cart_token: cartToken
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        if (data.cart_token) {
          setCartToken(data.cart_token);
          localStorage.setItem('cart_token', data.cart_token);
        }
        await loadCart();
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Failed to add to cart:', error);
      return false;
    }
  };

  useEffect(() => {
    loadCart();
  }, [cartToken]);

  return (
    <CartContext.Provider value={{
      cartItems,
      cartSummary,
      addToCart,
      loadCart
    }}>
      {children}
    </CartContext.Provider>
  );
};
```

---

## 🔧 Testing with cURL

```bash
# Add to cart
curl -X POST http://127.0.0.1:8000/api/user/website-cart/add/ \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 2}'

# Get cart (use returned token)
curl http://127.0.0.1:8000/api/user/website-cart/ \
  -H "X-Cart-Token: YOUR_CART_TOKEN"

# Update quantity
curl -X POST http://127.0.0.1:8000/api/user/website-cart/update/ \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 5, "cart_token": "YOUR_CART_TOKEN"}'

# Remove item
curl -X POST http://127.0.0.1:8000/api/user/website-cart/remove/ \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "cart_token": "YOUR_CART_TOKEN"}'
```

---

## 📱 Mobile App Integration

For mobile apps (React Native, Flutter, etc.):

1. Store `cart_token` in AsyncStorage/SecureStore
2. Include in all cart API requests
3. Merge cart when user logs in
4. Clear token after successful merge

**React Native Example:**
```javascript
import AsyncStorage from '@react-native-async-storage/async-storage';

const addToCart = async (productId, quantity) => {
  const cartToken = await AsyncStorage.getItem('cart_token');
  
  const response = await fetch('/api/user/website-cart/add/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      product_id: productId,
      quantity,
      cart_token: cartToken
    })
  });
  
  const data = await response.json();
  
  if (data.cart_token) {
    await AsyncStorage.setItem('cart_token', data.cart_token);
  }
  
  return data;
};
```

---

## ✅ Checklist for Implementation

- [ ] Save `cart_token` from first add response
- [ ] Include `cart_token` in all subsequent requests
- [ ] Handle token expiry (create new cart if needed)
- [ ] Call merge endpoint after login
- [ ] Clear token after successful merge
- [ ] Display cart count in header/badge
- [ ] Show loading states during API calls
- [ ] Handle error responses gracefully
- [ ] Test on multiple browsers
- [ ] Test on mobile devices

---

**Need Help?** Check `WEBSITE_CART_IMPLEMENTATION.md` for detailed documentation.
