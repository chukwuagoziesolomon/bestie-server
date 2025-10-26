# Unified Vendor Recommendation API - Backend Only

## Overview

This is a **single backend endpoint** that combines all recommendation logic into one unified API. Perfect for the homepage design where there's one main section showing vendor recommendations. No admin dashboard or separate endpoints needed - just one clean API.

## Single Endpoint

### GET /api/user/recommendations/

Get unified vendor recommendations that automatically:
- Shows **featured vendors first** (paid subscribers with "FEATURED" badges)
- Applies **location-based filtering** based on user's city/location
- Considers **user preferences** and behavior
- Sorts by **ratings and popularity**
- Includes **social recommendations** from similar users

#### Query Parameters:
- `category` (string, optional): Filter by business category (e.g., "Food", "Restaurant")
- `page` (int, default: 1): Page number for pagination (starts from 1)
- `page_size` (int, default: 20): Number of recommendations per page
- `limit` (int, default: 100): Maximum total results to fetch (for performance)
- `latitude` (float, optional): User's latitude for location-based recommendations
- `longitude` (float, optional): User's longitude for location-based recommendations
- `city` (string, optional): User's city for location-based recommendations

#### Example Requests:
```bash
# First page with default pagination
GET /api/user/recommendations/?category=Food&city=Lagos

# Specific page with custom page size
GET /api/user/recommendations/?category=Food&city=Lagos&page=2&page_size=10

# "View More" functionality - get next page
GET /api/user/recommendations/?category=Food&city=Lagos&page=2&page_size=20
```

#### Example Response:
```json
{
  "success": true,
  "count": 20,
  "page": 1,
  "page_size": 20,
  "total_pages": 5,
  "has_next": true,
  "has_previous": false,
  "next_page": 2,
  "previous_page": null,
  "filters_applied": {
    "category": "Food",
    "user_location": {
      "city": "Lagos"
    },
    "user_authenticated": true
  },
  "recommendations": [
    {
      "id": 1,
      "business_name": "Galaxy Pizza Lagos",
      "business_category": "Food",
      "business_address": "123 Victoria Island, Lagos",
      "logo": "https://res.cloudinary.com/your-cloud/image/upload/w_300,h_300,c_fill,f_auto,q_auto/vendor_logos/galaxy_pizza.jpg",
      "logo_thumbnail": "https://res.cloudinary.com/your-cloud/image/upload/w_150,h_150,c_fill,f_auto,q_auto/vendor_logos/galaxy_pizza.jpg",
      "delivery_time": "30-40 min",
      "rating": 4.5,
      "total_reviews": 127,
      "is_featured": true,
      "featured_priority": 5,
      "recommendation_score": 85.2,
      "offers_delivery": true,
      "service_areas": ["Victoria Island", "Ikoyi", "Lekki"],
      "opening_hours": "08:00",
      "closing_hours": "22:00",
      "is_open": true,
      "distance": null
    },
    {
      "id": 2,
      "business_name": "Regular Restaurant",
      "business_category": "Food",
      "business_address": "456 Surulere, Lagos",
      "logo": "https://res.cloudinary.com/your-cloud/image/upload/w_300,h_300,c_fill,f_auto,q_auto/vendor_logos/regular_restaurant.jpg",
      "logo_thumbnail": "https://res.cloudinary.com/your-cloud/image/upload/w_150,h_150,c_fill,f_auto,q_auto/vendor_logos/regular_restaurant.jpg",
      "delivery_time": "25-35 min",
      "rating": 4.2,
      "total_reviews": 89,
      "is_featured": false,
      "featured_priority": 0,
      "recommendation_score": 72.8,
      "offers_delivery": true,
      "service_areas": ["Surulere", "Yaba"],
      "opening_hours": "09:00",
      "closing_hours": "21:00",
      "is_open": false,
      "distance": null
    }
  ]
}
```

### POST /api/user/recommendations/

Rate a vendor after ordering (combines rating functionality).

#### Request Body:
```json
{
  "vendor_id": 1,
  "rating": 5,
  "review_text": "Excellent service!",
  "order_id": 123
}
```

#### Response:
```json
{
  "success": true,
  "message": "Rating submitted successfully",
  "rating": {
    "id": 1,
    "rating": 5,
    "review_text": "Excellent service!",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### PUT /api/user/recommendations/preferences/

Update user preferences (combines preferences functionality).

#### Request Body:
```json
{
  "preferred_locations": ["Victoria Island", "Ikoyi"],
  "current_city": "Lagos",
  "preferred_cuisines": ["Italian", "Nigerian"],
  "dietary_restrictions": ["Vegetarian"],
  "price_range_min": 1000,
  "price_range_max": 5000,
  "prefers_delivery": true,
  "max_delivery_time": 45
}
```

#### Response:
```json
{
  "success": true,
  "message": "Preferences updated successfully",
  "preferences": {
    "preferred_locations": ["Victoria Island", "Ikoyi"],
    "current_city": "Lagos",
    "preferred_cuisines": ["Italian", "Nigerian"],
    "dietary_restrictions": ["Vegetarian"],
    "price_range_min": 1000,
    "price_range_max": 5000,
    "prefers_delivery": true,
    "max_delivery_time": 45,
    "enable_location_based": true,
    "enable_behavioral": true,
    "enable_social": true
  }
}
```

## Frontend Integration

### Homepage Implementation with "View More" Pagination
Perfect for your homepage design where there's one main section with pagination:

```javascript
// Get first page of recommendations for homepage
let currentPage = 1;
const pageSize = 20;

async function loadRecommendations(page = 1) {
  const response = await fetch(`/api/user/recommendations/?category=Food&page=${page}&page_size=${pageSize}&city=Lagos`);
  const data = await response.json();

  // The API automatically handles all the logic:
  // 1. Featured vendors appear first with is_featured: true
  // 2. Location-based filtering is applied
  // 3. User preferences are considered
  // 4. Ratings and popularity are factored in
  // 5. Social recommendations are included
  // 6. Pagination metadata is provided

  // Render vendors
  data.recommendations.forEach(vendor => {
    if (vendor.is_featured) {
      // Render with "FEATURED" badge
      renderVendorCard(vendor, { showFeaturedBadge: true });
    } else {
      // Render normally
      renderVendorCard(vendor, { showFeaturedBadge: false });
    }
  });

  // Handle "View More" button
  updateViewMoreButton(data.has_next, data.next_page);
}

function updateViewMoreButton(hasNext, nextPage) {
  const viewMoreBtn = document.getElementById('view-more-btn');
  
  if (hasNext) {
    viewMoreBtn.style.display = 'block';
    viewMoreBtn.onclick = () => {
      loadRecommendations(nextPage);
    };
  } else {
    viewMoreBtn.style.display = 'none';
  }
}

// Load initial recommendations
loadRecommendations(1);
```

### Cloudinary Integration Features:
- **Optimized Images**: Automatic image optimization with Cloudinary transformations
- **Multiple Sizes**: Both full-size logos and thumbnails provided
- **Web Optimization**: Auto format, quality, and resizing for better performance
- **Fallback Handling**: Graceful fallback if Cloudinary URLs fail

### Key Benefits of Unified Approach:

1. **Single API Call**: No need to make multiple requests for different recommendation types
2. **Automatic Logic**: All recommendation factors are handled automatically
3. **Featured Priority**: Paid subscribers automatically appear first
4. **Location Intelligence**: Automatically filters by user location
5. **User Preferences**: Considers user preferences and behavior automatically
6. **Rating Integration**: Ratings are factored into the scoring automatically
7. **Social Recommendations**: Includes recommendations from similar users automatically

## How It Works Internally:

1. **Featured Vendors First**: Gets all featured vendors (paid subscribers) and sorts by priority
2. **Location Filtering**: Applies location-based filtering based on user's city/location
3. **User Preferences**: Considers user preferences if authenticated
4. **Regular Recommendations**: Gets non-featured vendors and scores them based on:
   - Popularity (40% weight)
   - Ratings (25% weight)
   - Recent activity (20% weight)
   - User preference alignment (15% weight)
5. **Combined Results**: Returns featured vendors first, followed by regular vendors
6. **Unified Response**: Single response with all vendors in optimal order

This unified approach perfectly matches your homepage design where there's one main recommendation section that shows featured vendors with badges, followed by regular vendors based on intelligent scoring.
