# Vendor Search API - Advanced Search & Filtering

## Overview

This comprehensive vendor search system allows users to search for vendors with advanced filtering capabilities including text search, location filtering, cuisine types, price ranges, ratings, and more. The search is public (no authentication required) and provides personalized results for authenticated users.

## Search Endpoints

### 1. Vendor Search

**GET** `/api/user/search/vendors/`

Advanced vendor search with multiple filters and pagination support.

#### Query Parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | No | Search query (business name, category, description) |
| `state` | string | No | Filter by state |
| `city` | string | No | Filter by city |
| `area` | string | No | Filter by specific area/neighborhood |
| `cuisine` | string | No | Filter by food type/cuisine |
| `min_price` | float | No | Minimum price filter |
| `max_price` | float | No | Maximum price filter |
| `min_rating` | float | No | Minimum rating filter (1-5) |
| `delivery_only` | boolean | No | Show only vendors with delivery |
| `page` | int | No | Page number (default: 1) |
| `page_size` | int | No | Results per page (default: 20) |

#### Example Requests:

```bash
# Basic text search
GET /api/user/search/vendors/?q=pizza

# Search with location filter
GET /api/user/search/vendors/?q=restaurant&state=Lagos&city=Victoria Island

# Search with cuisine and price filters
GET /api/user/search/vendors/?cuisine=Italian&min_price=1000&max_price=5000

# Search with rating and delivery filters
GET /api/user/search/vendors/?min_rating=4&delivery_only=true

# Complex search with multiple filters
GET /api/user/search/vendors/?q=food&state=Lagos&cuisine=Nigerian&min_price=500&min_rating=3&delivery_only=true&page=1&page_size=10
```

#### Example Response:

```json
{
  "success": true,
  "count": 10,
  "total_count": 45,
  "page": 1,
  "page_size": 10,
  "total_pages": 5,
  "has_next": true,
  "has_previous": false,
  "search_params": {
    "query": "pizza",
    "state": "Lagos",
    "city": "",
    "area": "",
    "cuisine": "",
    "min_price": null,
    "max_price": null,
    "min_rating": null,
    "delivery_only": false
  },
  "vendors": [
    {
      "id": 1,
      "business_name": "Galaxy Pizza Lagos",
      "business_category": "Food",
      "business_description": "Authentic Italian pizza with fresh ingredients",
      "business_address": "123 Victoria Island, Lagos",
      "logo": "https://res.cloudinary.com/your-cloud/image/upload/w_300,h_300,c_fill,f_auto,q_auto/vendor_logos/galaxy_pizza.jpg",
      "rating": 4.5,
      "total_reviews": 127,
      "is_featured": true,
      "offers_delivery": true,
      "delivery_time": "30-40 min",
      "service_areas": ["Victoria Island", "Ikoyi", "Lekki"],
      "opening_hours": "08:00",
      "closing_hours": "22:00",
      "is_open": true,
      "price_range": {
        "min": 1500,
        "max": 4500,
        "currency": "NGN"
      },
      "menu_item_count": 25,
      "search_score": 85.2,
      "distance": null
    },
    {
      "id": 2,
      "business_name": "Mama's Kitchen",
      "business_category": "Nigerian Food",
      "business_description": "Traditional Nigerian dishes and local favorites",
      "business_address": "456 Surulere, Lagos",
      "logo": "https://res.cloudinary.com/your-cloud/image/upload/w_300,h_300,c_fill,f_auto,q_auto/vendor_logos/mamas_kitchen.jpg",
      "rating": 4.2,
      "total_reviews": 89,
      "is_featured": false,
      "offers_delivery": true,
      "delivery_time": "25-35 min",
      "service_areas": ["Surulere", "Yaba"],
      "opening_hours": "09:00",
      "closing_hours": "21:00",
      "is_open": false,
      "price_range": {
        "min": 800,
        "max": 2500,
        "currency": "NGN"
      },
      "menu_item_count": 18,
      "search_score": 72.8,
      "distance": null
    }
  ]
}
```

### 2. Search Filters

**GET** `/api/user/search/filters/`

Get available search filters and options to populate dropdown menus and filter UI.

#### Example Request:
```bash
GET /api/user/search/filters/
```

#### Example Response:
```json
{
  "success": true,
  "filters": {
    "states": [
      "Lagos",
      "Abuja",
      "Port Harcourt",
      "Kano",
      "Ibadan"
    ],
    "cities": [
      "Victoria Island",
      "Ikoyi",
      "Lekki",
      "Surulere",
      "Yaba",
      "Garki",
      "Wuse",
      "Maitama"
    ],
    "cuisines": [
      "Nigerian",
      "Italian",
      "Chinese",
      "Indian",
      "Fast Food",
      "African",
      "Mediterranean",
      "Continental",
      "Local",
      "International"
    ],
    "price_ranges": [
      {
        "label": "Under ₦500",
        "min": 0,
        "max": 500
      },
      {
        "label": "₦500 - ₦1,000",
        "min": 500,
        "max": 1000
      },
      {
        "label": "₦1,000 - ₦2,000",
        "min": 1000,
        "max": 2000
      },
      {
        "label": "₦2,000 - ₦5,000",
        "min": 2000,
        "max": 5000
      },
      {
        "label": "Above ₦5,000",
        "min": 5000,
        "max": null
      }
    ],
    "rating_options": [
      {
        "label": "4+ Stars",
        "value": 4
      },
      {
        "label": "3+ Stars",
        "value": 3
      },
      {
        "label": "2+ Stars",
        "value": 2
      },
      {
        "label": "1+ Stars",
        "value": 1
      }
    ],
    "delivery_options": [
      {
        "label": "Delivery Available",
        "value": true
      },
      {
        "label": "Pickup Only",
        "value": false
      }
    ]
  }
}
```

## Search Features

### 1. Text Search
- **Business Name**: Search by vendor business name
- **Category**: Search by business category
- **Description**: Search in business description
- **Address**: Search in business address
- **Service Areas**: Search in service areas

### 2. Location Filtering
- **State**: Filter by Nigerian states
- **City**: Filter by cities within states
- **Area**: Filter by specific areas/neighborhoods
- **Combined**: Multiple location filters work together

### 3. Cuisine & Food Type Filtering
- **Cuisine Types**: Nigerian, Italian, Chinese, Indian, etc.
- **Food Categories**: Fast Food, Continental, Local, etc.
- **Flexible Matching**: Partial matches and variations

### 4. Price Range Filtering
- **Menu-Based**: Based on actual menu item prices
- **Range Selection**: Min and max price filters
- **Currency**: Nigerian Naira (NGN)
- **Predefined Ranges**: Common price brackets

### 5. Rating & Quality Filtering
- **Minimum Rating**: Filter by star ratings (1-5)
- **Review Count**: Considered in search ranking
- **Quality Assurance**: Only verified vendors included

### 6. Delivery Options
- **Delivery Available**: Filter vendors that offer delivery
- **Pickup Only**: Show vendors with pickup only
- **Service Areas**: Consider delivery coverage

### 7. Search Ranking & Relevance
- **Text Relevance**: How well the search query matches
- **Rating Score**: Higher rated vendors rank higher
- **Popularity**: Popular vendors get ranking boost
- **Featured Priority**: Featured vendors get priority
- **User Preferences**: Personalized ranking for logged-in users

## Frontend Integration

### Search Interface Implementation

```javascript
// Search vendors with filters
async function searchVendors(searchParams) {
  try {
    const queryString = new URLSearchParams(searchParams).toString();
    const response = await fetch(`/api/user/search/vendors/?${queryString}`);
    const data = await response.json();
    
    if (data.success) {
      // Render search results
      renderSearchResults(data.vendors);
      
      // Update pagination
      updatePagination(data);
      
      // Update search summary
      updateSearchSummary(data);
    }
  } catch (error) {
    console.error('Search error:', error);
  }
}

// Example search calls
function searchExamples() {
  // Basic search
  searchVendors({ q: 'pizza' });
  
  // Location-based search
  searchVendors({ 
    q: 'restaurant', 
    state: 'Lagos', 
    city: 'Victoria Island' 
  });
  
  // Filtered search
  searchVendors({
    cuisine: 'Nigerian',
    min_price: 1000,
    max_price: 3000,
    min_rating: 4,
    delivery_only: true
  });
}

// Load search filters
async function loadSearchFilters() {
  try {
    const response = await fetch('/api/user/search/filters/');
    const data = await response.json();
    
    if (data.success) {
      populateFilterDropdowns(data.filters);
    }
  } catch (error) {
    console.error('Error loading filters:', error);
  }
}

function populateFilterDropdowns(filters) {
  // Populate state dropdown
  const stateSelect = document.getElementById('state-filter');
  filters.states.forEach(state => {
    const option = document.createElement('option');
    option.value = state;
    option.textContent = state;
    stateSelect.appendChild(option);
  });
  
  // Populate cuisine dropdown
  const cuisineSelect = document.getElementById('cuisine-filter');
  filters.cuisines.forEach(cuisine => {
    const option = document.createElement('option');
    option.value = cuisine;
    option.textContent = cuisine;
    cuisineSelect.appendChild(option);
  });
  
  // Populate price range dropdown
  const priceSelect = document.getElementById('price-filter');
  filters.price_ranges.forEach(range => {
    const option = document.createElement('option');
    option.value = `${range.min}-${range.max || 'infinity'}`;
    option.textContent = range.label;
    priceSelect.appendChild(option);
  });
}
```

### Search Results Rendering

```javascript
function renderSearchResults(vendors) {
  const resultsContainer = document.getElementById('search-results');
  resultsContainer.innerHTML = '';
  
  vendors.forEach(vendor => {
    const vendorCard = createVendorCard(vendor);
    resultsContainer.appendChild(vendorCard);
  });
}

function createVendorCard(vendor) {
  const card = document.createElement('div');
  card.className = 'vendor-card';
  card.innerHTML = `
    <div class="vendor-image">
      <img src="${vendor.logo}" alt="${vendor.business_name}" />
      ${vendor.is_featured ? '<span class="featured-badge">FEATURED</span>' : ''}
    </div>
    <div class="vendor-info">
      <h3>${vendor.business_name}</h3>
      <p class="category">${vendor.business_category}</p>
      <p class="address">${vendor.business_address}</p>
      
      <div class="vendor-stats">
        <div class="rating">
          <span class="stars">${'★'.repeat(Math.floor(vendor.rating))}</span>
          <span class="rating-value">${vendor.rating}</span>
          <span class="review-count">(${vendor.total_reviews} reviews)</span>
        </div>
        
        <div class="price-range">
          ₦${vendor.price_range.min} - ₦${vendor.price_range.max}
        </div>
        
        <div class="delivery-info">
          ${vendor.offers_delivery ? 
            `<span class="delivery-available">Delivery: ${vendor.delivery_time}</span>` : 
            '<span class="pickup-only">Pickup Only</span>'
          }
        </div>
        
        <div class="status">
          ${vendor.is_open ? 
            '<span class="open">Open</span>' : 
            '<span class="closed">Closed</span>'
          }
        </div>
      </div>
      
      <div class="vendor-actions">
        <button class="view-menu-btn">View Menu</button>
        <button class="favorite-btn">♥</button>
      </div>
    </div>
  `;
  
  return card;
}
```

## Search Algorithm Details

### 1. Search Relevance Scoring
- **Text Match Score**: How well the search query matches vendor information
- **Rating Boost**: Higher rated vendors get ranking boost
- **Popularity Score**: Popular vendors rank higher
- **Featured Priority**: Featured vendors get 50-point boost
- **User Personalization**: Previous orders and favorites boost ranking

### 2. Filtering Logic
- **AND Logic**: All active filters must match
- **OR Logic**: Within location filters (state OR city OR area)
- **Price Range**: Based on actual menu item prices
- **Rating Filter**: Minimum rating threshold
- **Delivery Filter**: Boolean filter for delivery availability

### 3. Pagination
- **Page-based**: Traditional page-based pagination
- **Configurable Size**: Adjustable page size (default: 20)
- **Total Count**: Full result count for pagination UI
- **Navigation**: Previous/next page indicators

## Performance Optimizations

1. **Database Indexing**: Optimized queries with proper indexes
2. **Select Related**: Reduced database queries with select_related
3. **Distinct Queries**: Proper use of distinct() for filtered results
4. **Pagination**: Efficient pagination to limit result sets
5. **Caching**: Search filters can be cached for better performance

## Key Benefits

1. **Comprehensive Search**: Multiple search criteria and filters
2. **User-Friendly**: Intuitive search interface with helpful filters
3. **Performance**: Optimized queries and pagination
4. **Personalization**: Better results for authenticated users
5. **Flexibility**: Support for simple and complex search queries
6. **Real-time**: Live search results with instant filtering
7. **Mobile-Friendly**: Responsive design for all devices

This search system provides everything needed for a comprehensive vendor discovery experience! 🔍✨






