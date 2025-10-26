# Vendor Profile API - Complete Vendor Details & Menu

## Overview

This API provides complete vendor profile information and menu items when users click on a vendor to view their details and place orders. It's perfect for the vendor profile page like the "Burger Palace" example you showed me.

## API Endpoints

### 1. Vendor Profile Details

**GET** `/api/user/vendors/{vendor_id}/profile/`

Get complete vendor profile with all details, menu items organized by categories, reviews, and statistics.

#### Example Request:
```bash
GET /api/user/vendors/2/profile/
```

#### Example Response:
```json
{
  "success": true,
  "vendor": {
    "id": 2,
    "business_name": "Burger Palace",
    "business_category": "Food",
    "business_description": "Delicious and juicy burgers in Enugu. We use quality ingredients to ensure a memorable experience.",
    "business_address": "123 Independence Layout, Enugu",
    "logo": "https://res.cloudinary.com/your-cloud/image/upload/w_400,h_400,c_fill,f_auto,q_auto/vendor_logos/burger_palace.jpg",
    "banner_image": "https://res.cloudinary.com/your-cloud/image/upload/w_1180,h_192,c_fill,f_auto,q_auto/banners/burger_palace_banner.jpg",
    "rating": 4.8,
    "total_reviews": 238,
    "is_featured": true,
    "offers_delivery": true,
    "delivery_time": "15-25 min",
    "service_areas": ["Independence Layout", "GRA", "New Haven"],
    "opening_hours": "08:00",
    "closing_hours": "22:00",
    "is_open": true,
    "price_range": {
      "min": 800,
      "max": 3500,
      "currency": "NGN"
    },
    "contact_phone": "+234-123-456-7890",
    "contact_email": "info@burgerpalace.com",
    "website": "https://burgerpalace.com",
    "social_media": {
      "facebook": "https://facebook.com/burgerpalace",
      "instagram": "https://instagram.com/burgerpalace",
      "twitter": "https://twitter.com/burgerpalace"
    },
    "is_favorited": false,
    "created_at": "2023-01-15T10:30:00Z",
    "verification_date": "2023-01-20T14:15:00Z"
  },
  "menu_categories": [
    {
      "category": "Burgers",
      "item_count": 8,
      "items": [
        {
          "id": 101,
          "name": "Classic Beef Burger",
          "description": "Juicy beef patty with lettuce, tomato, onion, and our special sauce",
          "price": 2500,
          "currency": "NGN",
          "image": "https://res.cloudinary.com/your-cloud/image/upload/w_400,h_400,c_fill,f_auto,q_auto/menu_items/classic_beef_burger.jpg",
          "is_available": true,
          "preparation_time": 15,
          "ingredients": ["Beef Patty", "Lettuce", "Tomato", "Onion", "Special Sauce"],
          "allergens": ["Gluten", "Dairy"],
          "is_vegetarian": false,
          "is_spicy": false,
          "calories": 650,
          "created_at": "2023-01-15T10:30:00Z",
          "updated_at": "2023-06-15T16:45:00Z"
        },
        {
          "id": 102,
          "name": "Chicken Deluxe Burger",
          "description": "Grilled chicken breast with avocado, bacon, and honey mustard",
          "price": 2800,
          "currency": "NGN",
          "image": "https://res.cloudinary.com/your-cloud/image/upload/w_400,h_400,c_fill,f_auto,q_auto/menu_items/chicken_deluxe_burger.jpg",
          "is_available": true,
          "preparation_time": 18,
          "ingredients": ["Chicken Breast", "Avocado", "Bacon", "Honey Mustard"],
          "allergens": ["Gluten", "Dairy"],
          "is_vegetarian": false,
          "is_spicy": false,
          "calories": 720,
          "created_at": "2023-01-15T10:30:00Z",
          "updated_at": "2023-06-15T16:45:00Z"
        }
      ]
    },
    {
      "category": "Sides",
      "item_count": 5,
      "items": [
        {
          "id": 201,
          "name": "French Fries",
          "description": "Crispy golden fries seasoned with sea salt",
          "price": 800,
          "currency": "NGN",
          "image": "https://res.cloudinary.com/your-cloud/image/upload/w_400,h_400,c_fill,f_auto,q_auto/menu_items/french_fries.jpg",
          "is_available": true,
          "preparation_time": 8,
          "ingredients": ["Potatoes", "Sea Salt", "Vegetable Oil"],
          "allergens": [],
          "is_vegetarian": true,
          "is_spicy": false,
          "calories": 320,
          "created_at": "2023-01-15T10:30:00Z",
          "updated_at": "2023-06-15T16:45:00Z"
        }
      ]
    },
    {
      "category": "Drinks",
      "item_count": 6,
      "items": [
        {
          "id": 301,
          "name": "Fresh Orange Juice",
          "description": "Freshly squeezed orange juice",
          "price": 1200,
          "currency": "NGN",
          "image": "https://res.cloudinary.com/your-cloud/image/upload/w_400,h_400,c_fill,f_auto,q_auto/menu_items/orange_juice.jpg",
          "is_available": true,
          "preparation_time": 5,
          "ingredients": ["Fresh Oranges"],
          "allergens": [],
          "is_vegetarian": true,
          "is_spicy": false,
          "calories": 110,
          "created_at": "2023-01-15T10:30:00Z",
          "updated_at": "2023-06-15T16:45:00Z"
        }
      ]
    }
  ],
  "reviews": {
    "recent_reviews": [
      {
        "id": 1001,
        "user_name": "John Doe",
        "user_avatar": "https://res.cloudinary.com/your-cloud/image/upload/w_100,h_100,c_fill,f_auto,q_auto/avatars/john_doe.jpg",
        "rating": 5,
        "review_text": "Amazing burgers! The meat was juicy and the service was fast.",
        "created_at": "2024-01-10T14:30:00Z",
        "is_verified": true
      },
      {
        "id": 1002,
        "user_name": "Sarah Wilson",
        "user_avatar": "https://res.cloudinary.com/your-cloud/image/upload/w_100,h_100,c_fill,f_auto,q_auto/avatars/sarah_wilson.jpg",
        "rating": 4,
        "review_text": "Great food and reasonable prices. Delivery was on time.",
        "created_at": "2024-01-08T19:15:00Z",
        "is_verified": true
      }
    ],
    "total_reviews": 238,
    "average_rating": 4.8,
    "rating_breakdown": {
      "5": 65.2,
      "4": 22.7,
      "3": 8.4,
      "2": 2.5,
      "1": 1.2
    }
  },
  "stats": {
    "total_orders": 1250,
    "total_revenue": 2850000,
    "orders_last_30_days": 89,
    "menu_items": 19,
    "years_in_business": 2,
    "recommendation_score": 92.5
  }
}
```

### 2. Vendor Menu Items (Filtered)

**GET** `/api/user/vendors/{vendor_id}/menu/`

Get vendor menu items with optional filtering for search within the vendor's menu.

#### Query Parameters:
- `category` (string, optional): Filter by menu category
- `search` (string, optional): Search within menu items
- `min_price` (float, optional): Minimum price filter
- `max_price` (float, optional): Maximum price filter
- `vegetarian_only` (boolean, optional): Show only vegetarian items

#### Example Requests:
```bash
# Get all menu items
GET /api/user/vendors/2/menu/

# Filter by category
GET /api/user/vendors/2/menu/?category=Burgers

# Search within menu
GET /api/user/vendors/2/menu/?search=chicken

# Filter by price range
GET /api/user/vendors/2/menu/?min_price=1000&max_price=2000

# Vegetarian items only
GET /api/user/vendors/2/menu/?vegetarian_only=true
```

#### Example Response:
```json
{
  "success": true,
  "count": 8,
  "vendor_id": 2,
  "vendor_name": "Burger Palace",
  "filters_applied": {
    "category": "Burgers",
    "search": "",
    "min_price": null,
    "max_price": null,
    "vegetarian_only": false
  },
  "menu_items": [
    {
      "id": 101,
      "name": "Classic Beef Burger",
      "description": "Juicy beef patty with lettuce, tomato, onion, and our special sauce",
      "price": 2500,
      "currency": "NGN",
      "image": "https://res.cloudinary.com/your-cloud/image/upload/w_300,h_300,c_fill,f_auto,q_auto/menu_items/classic_beef_burger.jpg",
      "category": "Burgers",
      "preparation_time": 15,
      "ingredients": ["Beef Patty", "Lettuce", "Tomato", "Onion", "Special Sauce"],
      "allergens": ["Gluten", "Dairy"],
      "is_vegetarian": false,
      "is_spicy": false,
      "calories": 650
    }
  ]
}
```

## Frontend Integration

### Vendor Profile Page Implementation

```javascript
// Load vendor profile page
async function loadVendorProfile(vendorId) {
  try {
    const response = await fetch(`/api/user/vendors/${vendorId}/profile/`);
    const data = await response.json();
    
    if (data.success) {
      // Render vendor details
      renderVendorDetails(data.vendor);
      
      // Render menu categories
      renderMenuCategories(data.menu_categories);
      
      // Render reviews
      renderReviews(data.reviews);
      
      // Render stats
      renderVendorStats(data.stats);
    }
  } catch (error) {
    console.error('Error loading vendor profile:', error);
  }
}

function renderVendorDetails(vendor) {
  // Render vendor header with banner
  const vendorHeader = document.getElementById('vendor-header');
  vendorHeader.innerHTML = `
    <div class="vendor-banner">
      <img src="${vendor.banner_image}" alt="${vendor.business_name}" />
      <div class="vendor-overlay">
        <h1>${vendor.business_name}</h1>
        <div class="vendor-rating">
          <span class="stars">${'★'.repeat(Math.floor(vendor.rating))}</span>
          <span class="rating-value">${vendor.rating} (${vendor.total_reviews})</span>
        </div>
        <div class="delivery-time">${vendor.delivery_time}</div>
        <div class="vendor-status ${vendor.is_open ? 'open' : 'closed'}">
          ${vendor.is_open ? 'Open' : 'Closed'}
        </div>
      </div>
    </div>
  `;
  
  // Render vendor info card
  const vendorInfo = document.getElementById('vendor-info');
  vendorInfo.innerHTML = `
    <div class="vendor-card">
      <div class="vendor-logo">
        <img src="${vendor.logo}" alt="${vendor.business_name}" />
        ${vendor.is_featured ? '<span class="featured-badge">FEATURED</span>' : ''}
      </div>
      
      <div class="vendor-details">
        <h2>About ${vendor.business_name}</h2>
        <p>${vendor.business_description}</p>
        
        <div class="vendor-meta">
          <div class="meta-item">
            <strong>Address:</strong> ${vendor.business_address}
          </div>
          <div class="meta-item">
            <strong>Hours:</strong> ${vendor.opening_hours} - ${vendor.closing_hours}
          </div>
          <div class="meta-item">
            <strong>Price Range:</strong> ₦${vendor.price_range.min} - ₦${vendor.price_range.max}
          </div>
          <div class="meta-item">
            <strong>Delivery:</strong> ${vendor.offers_delivery ? 'Available' : 'Pickup Only'}
          </div>
        </div>
        
        <div class="vendor-actions">
          <button class="favorite-btn ${vendor.is_favorited ? 'favorited' : ''}" 
                  onclick="toggleFavorite(${vendor.id})">
            ${vendor.is_favorited ? '♥' : '♡'} Favorite
          </button>
          <button class="share-btn" onclick="shareVendor(${vendor.id})">
            📤 Share
          </button>
        </div>
      </div>
    </div>
  `;
}

function renderMenuCategories(categories) {
  const menuContainer = document.getElementById('menu-container');
  menuContainer.innerHTML = '';
  
  categories.forEach(category => {
    const categorySection = document.createElement('div');
    categorySection.className = 'menu-category';
    categorySection.innerHTML = `
      <h3 class="category-title">${category.category} (${category.item_count})</h3>
      <div class="menu-items">
        ${category.items.map(item => createMenuItemCard(item)).join('')}
      </div>
    `;
    menuContainer.appendChild(categorySection);
  });
}

function createMenuItemCard(item) {
  return `
    <div class="menu-item-card" onclick="selectMenuItem(${item.id})">
      <div class="item-image">
        <img src="${item.image}" alt="${item.name}" />
        ${item.is_vegetarian ? '<span class="vegetarian-badge">🌱 Veg</span>' : ''}
        ${item.is_spicy ? '<span class="spicy-badge">🌶️ Spicy</span>' : ''}
      </div>
      
      <div class="item-details">
        <h4 class="item-name">${item.name}</h4>
        <p class="item-description">${item.description}</p>
        
        <div class="item-info">
          <div class="item-ingredients">
            <strong>Ingredients:</strong> ${item.ingredients.join(', ')}
          </div>
          ${item.allergens.length > 0 ? `
            <div class="item-allergens">
              <strong>Allergens:</strong> ${item.allergens.join(', ')}
            </div>
          ` : ''}
          ${item.calories ? `
            <div class="item-calories">
              <strong>Calories:</strong> ${item.calories}
            </div>
          ` : ''}
          <div class="item-prep-time">
            <strong>Prep Time:</strong> ${item.preparation_time} min
          </div>
        </div>
        
        <div class="item-footer">
          <div class="item-price">₦${item.price}</div>
          <button class="add-to-cart-btn" onclick="addToCart(${item.id})">
            Add to Cart
          </button>
        </div>
      </div>
    </div>
  `;
}

function renderReviews(reviews) {
  const reviewsContainer = document.getElementById('reviews-container');
  
  // Rating summary
  const ratingSummary = document.createElement('div');
  ratingSummary.className = 'rating-summary';
  ratingSummary.innerHTML = `
    <div class="overall-rating">
      <div class="rating-number">${reviews.average_rating}</div>
      <div class="rating-stars">${'★'.repeat(Math.floor(reviews.average_rating))}</div>
      <div class="rating-count">${reviews.total_reviews} reviews</div>
    </div>
    
    <div class="rating-breakdown">
      ${Object.entries(reviews.rating_breakdown).map(([stars, percentage]) => `
        <div class="rating-bar">
          <span class="stars">${stars}★</span>
          <div class="bar">
            <div class="fill" style="width: ${percentage}%"></div>
          </div>
          <span class="percentage">${percentage}%</span>
        </div>
      `).join('')}
    </div>
  `;
  reviewsContainer.appendChild(ratingSummary);
  
  // Recent reviews
  const recentReviews = document.createElement('div');
  recentReviews.className = 'recent-reviews';
  recentReviews.innerHTML = `
    <h3>Recent Reviews</h3>
    ${reviews.recent_reviews.map(review => `
      <div class="review-card">
        <div class="review-header">
          <div class="reviewer-info">
            <img src="${review.user_avatar}" alt="${review.user_name}" class="reviewer-avatar" />
            <div class="reviewer-details">
              <div class="reviewer-name">${review.user_name}</div>
              <div class="review-rating">${'★'.repeat(review.rating)}</div>
            </div>
          </div>
          <div class="review-date">${new Date(review.created_at).toLocaleDateString()}</div>
        </div>
        <div class="review-text">${review.review_text}</div>
        ${review.is_verified ? '<span class="verified-badge">✓ Verified Purchase</span>' : ''}
      </div>
    `).join('')}
  `;
  reviewsContainer.appendChild(recentReviews);
}

// Load vendor profile when page loads
document.addEventListener('DOMContentLoaded', () => {
  const vendorId = window.location.pathname.split('/').pop();
  loadVendorProfile(vendorId);
});
```

## Key Features

### 1. Complete Vendor Information
- **Basic Details**: Name, category, description, address
- **Images**: Logo and banner image with Cloudinary optimization
- **Contact Info**: Phone, email, website, social media
- **Operating Hours**: Opening and closing times with open/closed status
- **Service Areas**: Delivery coverage areas
- **Price Range**: Min/max prices from menu items

### 2. Organized Menu Items
- **Categories**: Menu items grouped by categories (Burgers, Sides, Drinks)
- **Detailed Items**: Name, description, price, images, ingredients
- **Allergen Info**: Allergen warnings for each item
- **Dietary Info**: Vegetarian, spicy indicators
- **Nutrition**: Calorie information when available
- **Preparation Time**: Estimated cooking time

### 3. Reviews & Ratings
- **Overall Rating**: Average rating and total review count
- **Rating Breakdown**: Percentage distribution of star ratings
- **Recent Reviews**: Latest customer reviews with user info
- **Verified Reviews**: Indicators for verified purchases

### 4. Vendor Statistics
- **Business Metrics**: Total orders, revenue, menu item count
- **Activity**: Recent orders (last 30 days)
- **Experience**: Years in business calculation
- **Performance**: Recommendation score

### 5. User Personalization
- **Favorites**: Check if user has favorited the vendor
- **Order History**: Personalized recommendations based on past orders
- **Preferences**: Consider user dietary preferences

## Perfect for Your Use Case

This API provides everything needed for a complete vendor profile page like the "Burger Palace" example:

- ✅ **Vendor Details**: All vendor information displayed prominently
- ✅ **Menu Categories**: Organized menu items for easy browsing
- ✅ **Ratings & Reviews**: Customer feedback and ratings
- ✅ **Ordering Ready**: All menu items with prices and details
- ✅ **Images**: Optimized images for logos, banners, and menu items
- ✅ **Real-time Info**: Open/closed status, delivery times
- ✅ **User Experience**: Favorites, sharing, and personalization

The API is public (no authentication required) so users can browse vendor profiles and menus before deciding to place orders! 🍔✨
