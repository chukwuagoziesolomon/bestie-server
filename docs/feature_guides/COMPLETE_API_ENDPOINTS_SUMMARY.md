# Complete API Endpoints Summary

## 🛒 **1. ORDER CREATION ENDPOINTS**

### **A. Food Customization Modal**
**GET** `/api/user/menu-items/{item_id}/customize/`

**Response:**
```json
{
  "success": true,
  "menu_item": {
    "id": 101,
    "name": "Classic Beef Burger",
    "description": "Juicy beef patty with lettuce, tomato, onion, and our special sauce",
    "base_price": 2500,
    "currency": "NGN",
    "image": "https://res.cloudinary.com/your-cloud/image/upload/w_400,h_400,c_fill,f_auto,q_auto/menu_items/classic_beef_burger.jpg",
    "preparation_time": 15,
    "ingredients": ["Beef Patty", "Lettuce", "Tomato", "Onion", "Special Sauce"],
    "allergens": ["Gluten", "Dairy"],
    "is_vegetarian": false,
    "is_spicy": false,
    "calories": 650
  },
  "variants": {
    "size": [
      {
        "id": 1,
        "name": "Small",
        "type": "size",
        "price_modifier": -500,
        "is_required": false,
        "formatted_price": "-₦500"
      },
      {
        "id": 2,
        "name": "Regular",
        "type": "size",
        "price_modifier": 0,
        "is_required": false,
        "formatted_price": "Free"
      },
      {
        "id": 3,
        "name": "Large",
        "type": "size",
        "price_modifier": 2000,
        "is_required": false,
        "formatted_price": "+₦2,000"
      }
    ],
    "extra": [
      {
        "id": 4,
        "name": "Extra Cheese",
        "type": "extra",
        "price_modifier": 1500,
        "is_required": false,
        "formatted_price": "+₦1,500"
      },
      {
        "id": 5,
        "name": "Extra Bacon",
        "type": "extra",
        "price_modifier": 2000,
        "is_required": false,
        "formatted_price": "+₦2,000"
      }
    ]
  },
  "customization_options": {
    "allows_special_instructions": true,
    "max_instructions_length": 500,
    "special_instructions_placeholder": "Any special requests? (e.g., no onions, extra spicy)"
  }
}
```

### **B. Add Item to Cart**
**POST** `/api/user/cart/add/`

**Request:**
```json
{
  "menu_item_id": 101,
  "quantity": 1,
  "variants": [
    {
      "id": 2,
      "type": "size"
    },
    {
      "id": 4,
      "type": "extra"
    }
  ],
  "special_instructions": "No onions, extra spicy"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Item added to cart successfully",
  "cart_item": {
    "id": 1,
    "menu_item_name": "Classic Beef Burger",
    "quantity": 1,
    "variants": [
      {
        "id": 2,
        "name": "Regular",
        "type": "size",
        "price_modifier": 0
      },
      {
        "id": 4,
        "name": "Extra Cheese",
        "type": "extra",
        "price_modifier": 1500
      }
    ],
    "special_instructions": "No onions, extra spicy",
    "total_price": 4000,
    "currency": "NGN"
  },
  "cart_summary": {
    "cart_id": 1,
    "vendor_name": "Burger Palace",
    "total_items": 1,
    "total_price": 4000,
    "currency": "NGN"
  }
}
```

### **C. Place Order**
**POST** `/api/user/orders/place/`

**Request:**
```json
{
  "cart_id": 1,
  "delivery_address_id": 5,
  "payment_method": "cash",
  "delivery_instructions": "Please call when you arrive"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Order placed successfully",
  "order": {
    "id": 123,
    "order_number": "#123",
    "vendor": {
      "id": 2,
      "name": "Burger Palace",
      "logo": "https://res.cloudinary.com/your-cloud/image/upload/w_200,h_200,c_fill,f_auto,q_auto/vendor_logos/burger_palace.jpg",
      "delivery_time": "15-25 min"
    },
    "total_amount": 4000,
    "currency": "NGN",
    "status": "pending",
    "payment_method": "cash",
    "delivery_address": {
      "street": "123 Independence Layout",
      "city": "Enugu",
      "state": "Enugu State",
      "postal_code": "400001",
      "landmark": "Near Central Bank"
    },
    "delivery_instructions": "Please call when you arrive",
    "order_date": "2024-01-15T10:30:00Z",
    "estimated_delivery": "2024-01-15T11:00:00Z",
    "items_count": 1
  },
  "notifications": {
    "whatsapp": {
      "success": true,
      "message": "WhatsApp notification sent successfully",
      "message_id": "SM1234567890",
      "service_used": "twilio",
      "environment": "development"
    },
    "websocket": {
      "success": true,
      "message": "WebSocket notification sent successfully"
    },
    "email": {
      "success": true,
      "message": "Email sent to vendor@burgerpalace.com",
      "vendor_email": "vendor@burgerpalace.com"
    }
  },
  "automatic_replies": {
    "whatsapp": {
      "success": true,
      "message": "Automatic WhatsApp reply sent successfully",
      "message_id": "SM1234567891",
      "service_used": "twilio",
      "environment": "development"
    },
    "websocket": {
      "success": true,
      "message": "Automatic WebSocket reply sent successfully"
    }
  },
  "tracking": {
    "order_id": 123,
    "tracking_url": "/orders/123/track",
    "vendor_contact": {
      "phone": "+234-123-456-7890",
      "whatsapp": "+234-123-456-7890"
    }
  }
}
```

### **D. Update Order Status**
**PUT** `/api/user/orders/{order_id}/status/`

**Request:**
```json
{
  "status": "preparing"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Order status updated from pending to preparing",
  "order": {
    "id": 123,
    "status": "preparing",
    "status_updated_at": "2024-01-15T10:35:00Z",
    "estimated_delivery": "2024-01-15T11:00:00Z"
  }
}
```

---

## 📱 **2. NOTIFICATION ENDPOINTS**

### **A. WhatsApp Configuration Check**
**GET** `/api/user/whatsapp/config/`

**Response:**
```json
{
  "success": true,
  "configuration": {
    "whatsapp_business_api": {
      "access_token_configured": false,
      "phone_number_id_configured": false,
      "verify_token_configured": true
    },
    "twilio_whatsapp": {
      "account_sid_configured": true,
      "auth_token_configured": true,
      "whatsapp_from_configured": true
    }
  },
  "environment": {
    "is_production": false,
    "debug_mode": true
  },
  "available_services": {
    "whatsapp_business_api": false,
    "twilio_whatsapp": true
  },
  "current_service": "twilio",
  "service_preference": {
    "development": "twilio",
    "production": "whatsapp_business_api"
  },
  "recommended_service": "twilio_whatsapp"
}
```

### **B. Test WhatsApp Notification**
**POST** `/api/user/whatsapp/test/`

**Request:**
```json
{
  "vendor_id": 1,
  "message_type": "order_notification"
}
```

**Response:**
```json
{
  "success": true,
  "message": "WhatsApp order_notification sent successfully",
  "phone_number": "2341234567890",
  "vendor": {
    "id": 1,
    "business_name": "Burger Palace"
  },
  "result": {
    "success": true,
    "message": "Twilio WhatsApp message sent successfully",
    "message_id": "SM1234567890",
    "service_used": "twilio",
    "environment": "development"
  },
  "service_info": {
    "service_used": "twilio",
    "environment": "development"
  }
}
```

### **C. Send Manual Vendor Reply**
**POST** `/api/user/vendor/replies/send/`

**Request:**
```json
{
  "order_id": 123,
  "reply_type": "order_confirmation"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Automatic reply sent successfully",
  "reply_type": "order_confirmation",
  "order_id": 123,
  "results": {
    "whatsapp": {
      "success": true,
      "message": "Automatic WhatsApp reply sent successfully",
      "service_used": "twilio"
    },
    "websocket": {
      "success": true,
      "message": "Automatic WebSocket reply sent successfully"
    }
  }
}
```

### **D. Get Vendor Reply History**
**GET** `/api/user/vendor/replies/history/`

**Response:**
```json
{
  "success": true,
  "reply_history": [
    {
      "order_id": 123,
      "order_number": "#123",
      "customer_name": "John Doe",
      "total_amount": 4000,
      "status": "pending",
      "order_date": "2024-01-15T10:30:00Z",
      "reply_sent": true,
      "reply_type": "order_confirmation"
    }
  ],
  "vendor": {
    "id": 1,
    "business_name": "Burger Palace",
    "whatsapp_number": "+234-123-456-7890",
    "contact_email": "vendor@burgerpalace.com"
  }
}
```

### **E. WebSocket Notifications**
**WebSocket Connection:** `ws://localhost:8000/ws/vendor/notifications/?token=YOUR_TOKEN`

**Message Types:**
```json
// New Order Notification
{
  "type": "order.new",
  "data": {
    "order_id": 123,
    "order_number": "#123",
    "customer": {
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "+234-123-456-7890"
    },
    "items": [
      {
        "name": "Classic Beef Burger",
        "quantity": 1,
        "total_price": 4000
      }
    ],
    "total_amount": 4000,
    "order_time": "2024-01-15T10:30:00Z"
  }
}

// Automatic Reply Notification
{
  "type": "automatic_reply",
  "data": {
    "order_id": 123,
    "order_number": "#123",
    "reply_type": "order_confirmation",
    "message": "Order automatically confirmed and queued",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

---

## 🔍 **3. SEARCH ENDPOINTS**

### **A. Vendor Search**
**GET** `/api/user/search/vendors/`

**Query Parameters:**
- `q` - Search query (vendor name, cuisine, etc.)
- `location` - City or state
- `cuisine` - Type of cuisine
- `min_price` - Minimum price range
- `max_price` - Maximum price range
- `min_rating` - Minimum rating (1-5)
- `delivery` - Filter by delivery options
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20)

**Example Request:**
```
GET /api/user/search/vendors/?q=burger&location=Enugu&cuisine=fast_food&min_rating=4&delivery=true&page=1&page_size=10
```

**Response:**
```json
{
  "success": true,
  "count": 25,
  "page": 1,
  "page_size": 10,
  "total_pages": 3,
  "has_next": true,
  "has_previous": false,
  "next_page": 2,
  "previous_page": null,
  "filters_applied": {
    "query": "burger",
    "location": "Enugu",
    "cuisine": "fast_food",
    "min_rating": 4,
    "delivery": true
  },
  "vendors": [
    {
      "id": 1,
      "business_name": "Burger Palace",
      "business_category": "fast_food",
      "business_address": "123 Independence Layout, Enugu",
      "logo": "https://res.cloudinary.com/your-cloud/image/upload/w_300,h_300,c_fill,f_auto,q_auto/vendor_logos/burger_palace.jpg",
      "delivery_time": "15-25 min",
      "rating": 4.5,
      "total_reviews": 128,
      "is_featured": true,
      "featured_priority": 10,
      "recommendation_score": 85.2,
      "offers_delivery": true,
      "service_areas": ["Enugu", "Awka", "Onitsha"],
      "opening_hours": "08:00",
      "closing_hours": "22:00",
      "is_open": true,
      "distance": null,
      "cuisine_types": ["burgers", "fast_food", "american"],
      "price_range": "₦₦₦",
      "delivery_fee": 500,
      "minimum_order": 1000
    }
  ]
}
```

### **B. Search Filters**
**GET** `/api/user/search/filters/`

**Response:**
```json
{
  "success": true,
  "filters": {
    "cuisines": [
      {
        "value": "fast_food",
        "label": "Fast Food",
        "count": 45
      },
      {
        "value": "nigerian",
        "label": "Nigerian",
        "count": 38
      },
      {
        "value": "chinese",
        "label": "Chinese",
        "count": 12
      }
    ],
    "price_ranges": [
      {
        "value": "budget",
        "label": "Budget (₦0 - ₦2,000)",
        "count": 25
      },
      {
        "value": "moderate",
        "label": "Moderate (₦2,000 - ₦5,000)",
        "count": 45
      },
      {
        "value": "premium",
        "label": "Premium (₦5,000+)",
        "count": 15
      }
    ],
    "ratings": [
      {
        "value": 5,
        "label": "5 Stars",
        "count": 12
      },
      {
        "value": 4,
        "label": "4+ Stars",
        "count": 35
      },
      {
        "value": 3,
        "label": "3+ Stars",
        "count": 48
      }
    ],
    "delivery_options": [
      {
        "value": "delivery",
        "label": "Delivery Available",
        "count": 52
      },
      {
        "value": "pickup",
        "label": "Pickup Only",
        "count": 8
      }
    ],
    "locations": [
      {
        "value": "enugu",
        "label": "Enugu",
        "count": 25
      },
      {
        "value": "awka",
        "label": "Awka",
        "count": 18
      },
      {
        "value": "onitsha",
        "label": "Onitsha",
        "count": 12
      }
    ]
  }
}
```

### **C. Vendor Profile Details**
**GET** `/api/user/vendors/{vendor_id}/profile/`

**Response:**
```json
{
  "success": true,
  "vendor": {
    "id": 1,
    "business_name": "Burger Palace",
    "business_category": "fast_food",
    "business_address": "123 Independence Layout, Enugu",
    "logo": "https://res.cloudinary.com/your-cloud/image/upload/w_400,h_400,c_fill,f_auto,q_auto/vendor_logos/burger_palace.jpg",
    "cover_image": "https://res.cloudinary.com/your-cloud/image/upload/w_800,h_400,c_fill,f_auto,q_auto/vendor_covers/burger_palace.jpg",
    "description": "Best burgers in town with fresh ingredients and fast service",
    "phone": "+234-123-456-7890",
    "email": "info@burgerpalace.com",
    "website": "https://burgerpalace.com",
    "opening_hours": "08:00",
    "closing_hours": "22:00",
    "is_open": true,
    "delivery_time": "15-25 min",
    "delivery_fee": 500,
    "minimum_order": 1000,
    "offers_delivery": true,
    "service_areas": ["Enugu", "Awka", "Onitsha"],
    "cuisine_types": ["burgers", "fast_food", "american"],
    "price_range": "₦₦₦",
    "rating": 4.5,
    "total_reviews": 128,
    "is_featured": true,
    "featured_priority": 10,
    "recommendation_score": 85.2,
    "payment_methods": ["cash", "card", "bank_transfer"],
    "social_media": {
      "instagram": "@burgerpalace",
      "facebook": "BurgerPalaceEnugu",
      "twitter": "@burgerpalace"
    }
  }
}
```

### **D. Vendor Menu Items**
**GET** `/api/user/vendors/{vendor_id}/menu/`

**Query Parameters:**
- `category` - Filter by menu category
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20)

**Response:**
```json
{
  "success": true,
  "count": 25,
  "page": 1,
  "page_size": 20,
  "total_pages": 2,
  "has_next": true,
  "has_previous": false,
  "vendor": {
    "id": 1,
    "business_name": "Burger Palace"
  },
  "categories": [
    {
      "name": "burgers",
      "display_name": "Burgers",
      "count": 8
    },
    {
      "name": "sides",
      "display_name": "Sides",
      "count": 12
    },
    {
      "name": "drinks",
      "display_name": "Drinks",
      "count": 5
    }
  ],
  "menu_items": [
    {
      "id": 101,
      "name": "Classic Beef Burger",
      "description": "Juicy beef patty with lettuce, tomato, onion, and our special sauce",
      "price": 2500,
      "currency": "NGN",
      "category": "burgers",
      "image": "https://res.cloudinary.com/your-cloud/image/upload/w_400,h_400,c_fill,f_auto,q_auto/menu_items/classic_beef_burger.jpg",
      "is_available": true,
      "preparation_time": 15,
      "ingredients": ["Beef Patty", "Lettuce", "Tomato", "Onion", "Special Sauce"],
      "allergens": ["Gluten", "Dairy"],
      "is_vegetarian": false,
      "is_spicy": false,
      "calories": 650,
      "rating": 4.3,
      "total_reviews": 45,
      "is_popular": true,
      "variants_available": true
    }
  ]
}
```

---

## 🎯 **Summary of All Endpoints**

### **Order Creation Flow:**
1. `GET /api/user/menu-items/{id}/customize/` - Get customization options
2. `POST /api/user/cart/add/` - Add customized item to cart
3. `GET /api/user/cart/` - View cart contents
4. `POST /api/user/orders/place/` - Place order (triggers notifications)
5. `PUT /api/user/orders/{id}/status/` - Update order status

### **Notification System:**
1. `GET /api/user/whatsapp/config/` - Check WhatsApp configuration
2. `POST /api/user/whatsapp/test/` - Test WhatsApp notifications
3. `POST /api/user/vendor/replies/send/` - Send manual vendor replies
4. `GET /api/user/vendor/replies/history/` - Get reply history
5. `ws://localhost:8000/ws/vendor/notifications/` - WebSocket notifications

### **Search System:**
1. `GET /api/user/search/vendors/` - Search vendors with filters
2. `GET /api/user/search/filters/` - Get available search filters
3. `GET /api/user/vendors/{id}/profile/` - Get vendor details
4. `GET /api/user/vendors/{id}/menu/` - Get vendor menu items

All endpoints include comprehensive error handling, pagination, and detailed responses! 🎉
