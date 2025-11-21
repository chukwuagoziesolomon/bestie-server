# Frontend Migration Guide: Session Cart → JWT Cart

## Overview

This guide helps you migrate from the old session-based cart to the new JWT token-based cart system.

---

## Why Migrate?

### Old System (Session-Based) ❌
- Relies on cookies
- Breaks on Safari with strict cookie settings
- Breaks on mobile browsers
- Issues with cross-domain requests
- Limited to 4KB cookie size

### New System (JWT Token-Based) ✅
- No cookies required
- Works on ALL browsers (Chrome, Safari, Firefox, Edge)
- Works on ALL devices (Desktop, Mobile, iOS, Android)
- No size limitations
- Better for SPAs and mobile apps

---

## Migration Steps

### Step 1: Update Cart Add Function

**Before (Old System):**
```javascript
// ❌ Old - Relies on session cookies
const addToCart = async (productId, quantity) => {
  const response = await fetch('/api/user/cart/add/', {
    method: 'POST',
    credentials: 'include',  // Required for cookies
    body: JSON.stringify({
      product_id: productId,
      quantity: quantity
    })
  });
  
  return await response.json();
};
```

**After (New System):**
```javascript
// ✅ New - Uses cart_token
const addToCart = async (productId, quantity) => {
  const cartToken = localStorage.getItem('cart_token');
  
  const response = await fetch('/api/user/website-cart/add/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      product_id: productId,
      quantity: quantity,
      cart_token: cartToken  // Include saved token
    })
  });
  
  const data = await response.json();
  
  // ⚠️ IMPORTANT: Save token for future requests
  if (data.cart_token) {
    localStorage.setItem('cart_token', data.cart_token);
  }
  
  return data;
};
```

### Step 2: Update Get Cart Function

**Before (Old System):**
```javascript
// ❌ Old
const getCart = async () => {
  const response = await fetch('/api/user/cart/', {
    credentials: 'include'
  });
  
  return await response.json();
};
```

**After (New System):**
```javascript
// ✅ New
const getCart = async () => {
  const cartToken = localStorage.getItem('cart_token');
  if (!cartToken) return { products: [], total_items: 0 };
  
  const response = await fetch('/api/user/website-cart/', {
    headers: {
      'X-Cart-Token': cartToken  // Pass token in header
    }
  });
  
  return await response.json();
};
```

### Step 3: Update Remove Function

**Before (Old System):**
```javascript
// ❌ Old
const removeItem = async (cartItemId) => {
  const response = await fetch('/api/user/cart/remove/', {
    method: 'POST',
    credentials: 'include',
    body: JSON.stringify({
      cart_item_id: cartItemId
    })
  });
  
  return await response.json();
};
```

**After (New System):**
```javascript
// ✅ New
const removeItem = async (productId) => {
  const cartToken = localStorage.getItem('cart_token');
  
  const response = await fetch('/api/user/website-cart/remove/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      product_id: productId,  // Use product_id instead of cart_item_id
      cart_token: cartToken
    })
  });
  
  return await response.json();
};
```

### Step 4: Update Cart Summary

**Before (Old System):**
```javascript
// ❌ Old - No dedicated summary endpoint
const getCartCount = async () => {
  const cart = await getCart();
  return cart.items?.length || 0;
};
```

**After (New System):**
```javascript
// ✅ New - Optimized summary endpoint
const getCartSummary = async () => {
  const cartToken = localStorage.getItem('cart_token');
  if (!cartToken) return { total_items: 0 };
  
  const response = await fetch(
    `/api/user/website-cart/summary/?cart_token=${cartToken}`
  );
  
  return await response.json();
};

// Use in header badge
const CartBadge = () => {
  const [summary, setSummary] = useState({ total_items: 0 });
  
  useEffect(() => {
    getCartSummary().then(setSummary);
  }, []);
  
  return <Badge count={summary.total_items}>🛒</Badge>;
};
```

### Step 5: Add Login Cart Merge

**New Feature - Didn't exist in old system:**

```javascript
// ✅ New - Preserve cart when user logs in
const handleLogin = async (credentials) => {
  // 1. Login user
  const loginResponse = await login(credentials);
  const jwtToken = loginResponse.access_token;
  
  // 2. Merge anonymous cart
  const cartToken = localStorage.getItem('cart_token');
  if (cartToken) {
    await fetch('/api/user/website-cart/merge/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${jwtToken}`
      },
      body: JSON.stringify({ cart_token: cartToken })
    });
    
    // 3. Clear old token
    localStorage.removeItem('cart_token');
  }
  
  // 4. Reload cart with auth
  await getCart();
};
```

---

## Endpoint Mapping

| Old Endpoint | New Endpoint | Notes |
|-------------|--------------|-------|
| `POST /api/user/cart/add/` | `POST /api/user/website-cart/add/` | Include `cart_token` |
| `GET /api/user/cart/` | `GET /api/user/website-cart/` | Pass token in header |
| `POST /api/user/cart/remove/` | `POST /api/user/website-cart/remove/` | Use `product_id` |
| N/A | `GET /api/user/website-cart/summary/` | New - optimized count |
| N/A | `POST /api/user/website-cart/update/` | New - update quantity |
| N/A | `POST /api/user/website-cart/clear/` | New - clear all items |
| N/A | `POST /api/user/website-cart/merge/` | New - merge on login |

---

## React Migration Example

### Before (Old System)

```javascript
// ❌ Old cart hook
import { useState, useEffect } from 'react';

const useCart = () => {
  const [items, setItems] = useState([]);
  
  const loadCart = async () => {
    const response = await fetch('/api/user/cart/', {
      credentials: 'include'
    });
    const data = await response.json();
    setItems(data.items || []);
  };
  
  const addItem = async (productId, quantity) => {
    await fetch('/api/user/cart/add/', {
      method: 'POST',
      credentials: 'include',
      body: JSON.stringify({ product_id: productId, quantity })
    });
    await loadCart();
  };
  
  useEffect(() => {
    loadCart();
  }, []);
  
  return { items, addItem, loadCart };
};
```

### After (New System)

```javascript
// ✅ New cart hook
import { useState, useEffect } from 'react';

const useCart = () => {
  const [cartToken, setCartToken] = useState(
    localStorage.getItem('cart_token')
  );
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState({
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
        setItems(data.products);
        setSummary({
          total_items: data.total_items,
          total_amount: data.total_amount
        });
      }
    } catch (error) {
      console.error('Cart load error:', error);
    }
  };
  
  const addItem = async (productId, quantity) => {
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
        // Save new token (important!)
        if (data.cart_token) {
          setCartToken(data.cart_token);
          localStorage.setItem('cart_token', data.cart_token);
        }
        await loadCart();
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Add to cart error:', error);
      return false;
    }
  };
  
  const removeItem = async (productId) => {
    try {
      await fetch('/api/user/website-cart/remove/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: productId,
          cart_token: cartToken
        })
      });
      await loadCart();
      return true;
    } catch (error) {
      console.error('Remove from cart error:', error);
      return false;
    }
  };
  
  const updateQuantity = async (productId, quantity) => {
    try {
      await fetch('/api/user/website-cart/update/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: productId,
          quantity,
          cart_token: cartToken
        })
      });
      await loadCart();
      return true;
    } catch (error) {
      console.error('Update quantity error:', error);
      return false;
    }
  };
  
  const clearCart = async () => {
    try {
      await fetch('/api/user/website-cart/clear/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cart_token: cartToken })
      });
      localStorage.removeItem('cart_token');
      setCartToken(null);
      setItems([]);
      setSummary({ total_items: 0, total_amount: 0 });
      return true;
    } catch (error) {
      console.error('Clear cart error:', error);
      return false;
    }
  };
  
  useEffect(() => {
    loadCart();
  }, [cartToken]);
  
  return {
    items,
    summary,
    addItem,
    removeItem,
    updateQuantity,
    clearCart,
    loadCart
  };
};

export default useCart;
```

---

## Testing Your Migration

### 1. Test Anonymous Cart Flow

```javascript
// 1. Add first item (no token yet)
const data1 = await addToCart(123, 1);
console.log('Cart Token:', data1.cart_token); // Should see UUID

// 2. Verify token saved
const savedToken = localStorage.getItem('cart_token');
console.log('Saved Token:', savedToken); // Should match

// 3. Add second item (with token)
const data2 = await addToCart(456, 2);
console.log('Total Items:', data2.total_items); // Should be 3

// 4. Get cart
const cart = await getCart();
console.log('Cart Items:', cart.products.length); // Should be 2 products
```

### 2. Test Browser Compatibility

Test on:
- ✅ Chrome (Desktop)
- ✅ Safari (Desktop)
- ✅ Firefox (Desktop)
- ✅ Edge (Desktop)
- ✅ Chrome (Mobile)
- ✅ Safari (iOS)

### 3. Test Cart Persistence

```javascript
// 1. Add items to cart
await addToCart(123, 2);

// 2. Close browser tab
// 3. Open new browser tab
// 4. Navigate to site

const cart = await getCart();
console.log('Items still there:', cart.products.length); // Should persist
```

### 4. Test Login Merge

```javascript
// 1. Add items as anonymous
await addToCart(123, 2);
await addToCart(456, 1);

// 2. Login
const { access_token } = await login(credentials);

// 3. Merge cart
await mergeCart(access_token);

// 4. Verify items preserved
const cart = await getCart();
console.log('Items after merge:', cart.products.length); // Should still be 2

// 5. Verify token removed
const token = localStorage.getItem('cart_token');
console.log('Token after merge:', token); // Should be null
```

---

## Common Issues & Solutions

### Issue 1: Cart Token Not Saving

**Problem:**
```javascript
// Token not being saved
await addToCart(123, 1);
const token = localStorage.getItem('cart_token'); // null
```

**Solution:**
```javascript
// Make sure to save the token!
const data = await addToCart(123, 1);
if (data.cart_token) {
  localStorage.setItem('cart_token', data.cart_token); // ✅
}
```

### Issue 2: Cart Empty After Refresh

**Problem:** Cart items disappear on page refresh.

**Solution:** Verify token is in localStorage and being passed to API:
```javascript
// Check if token exists
const token = localStorage.getItem('cart_token');
console.log('Cart Token:', token);

// Make sure it's being passed
const cart = await fetch('/api/user/website-cart/', {
  headers: { 'X-Cart-Token': token } // ✅ Must include this
});
```

### Issue 3: Cart Not Merging on Login

**Problem:** Cart items lost after login.

**Solution:** Call merge endpoint:
```javascript
const handleLogin = async (credentials) => {
  const cartToken = localStorage.getItem('cart_token');
  
  // 1. Login first
  const { access_token } = await login(credentials);
  
  // 2. Then merge (if token exists)
  if (cartToken) {
    await fetch('/api/user/website-cart/merge/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ cart_token: cartToken })
    });
    
    // 3. Clear old token
    localStorage.removeItem('cart_token');
  }
};
```

---

## Rollback Plan

If you need to rollback to the old system:

1. Old endpoints still work: `/api/user/cart/*`
2. No backend changes needed
3. Just revert frontend code
4. Old session-based cart remains functional

---

## Benefits After Migration

✅ **Universal Browser Support**
- Works on Safari without issues
- No cookie blocking problems
- Mobile browsers fully supported

✅ **Better User Experience**
- Cart persists 30 days
- Cart preserved during login
- Faster load times (dedicated summary endpoint)

✅ **Developer Experience**
- Simpler API (no cookie management)
- Works with any frontend framework
- Easier mobile app integration

✅ **Future-Proof**
- Ready for third-party cookie deprecation
- Compatible with SPA architecture
- Scalable design

---

## Next Steps

1. ✅ Update cart functions to use new endpoints
2. ✅ Add cart_token storage logic
3. ✅ Implement login merge flow
4. ✅ Test on multiple browsers
5. ✅ Test on mobile devices
6. ✅ Deploy to production

---

**Need Help?**
- API Reference: `CART_API_QUICK_REFERENCE.md`
- Full Documentation: `WEBSITE_CART_IMPLEMENTATION.md`
- Test Examples: `test_website_cart.py`
