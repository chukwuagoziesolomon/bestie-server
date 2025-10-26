# Banner System API - Backend Only

## Overview

This banner system allows admins to upload and manage banners (1180x192) from the admin dashboard, which are then displayed on the frontend. The system includes Cloudinary integration for optimized image delivery.

## Banner Model Features

- **Image Upload**: Support for banner images (recommended size: 1180x192)
- **Cloudinary Integration**: Automatic image optimization and multiple sizes
- **Scheduling**: Start and end date scheduling for banners
- **Priority System**: Higher priority banners appear first
- **Targeting**: Target specific audiences
- **Status Management**: Active, inactive, scheduled, expired statuses
- **Click Tracking**: Optional click URL for banner interactions

## API Endpoints

### 1. Get Active Banners (Frontend)

**GET** `/api/user/banners/`

Get active banners for frontend display. This endpoint is public and doesn't require authentication.

#### Query Parameters:
- `type` (string, optional): Banner type filter (default: 'homepage')
  - `homepage` - Homepage banners
  - `promotional` - Promotional banners
  - `seasonal` - Seasonal banners
  - `vendor_spotlight` - Vendor spotlight banners
- `limit` (int, optional): Maximum number of banners to return (default: 5)

#### Example Request:
```bash
GET /api/user/banners/?type=homepage&limit=3
```

#### Example Response:
```json
{
  "success": true,
  "count": 3,
  "banner_type": "homepage",
  "banners": [
    {
      "id": 1,
      "title": "Summer Sale Banner",
      "description": "50% off on all food items",
      "banner_image": "https://res.cloudinary.com/your-cloud/image/upload/w_1180,h_192,c_fill,f_auto,q_auto/banners/summer_sale.jpg",
      "banner_type": "homepage",
      "click_url": "https://yoursite.com/summer-sale",
      "priority": 10,
      "target_audience": ["all_users"],
      "display_start_date": "2024-06-01T00:00:00Z",
      "display_end_date": "2024-08-31T23:59:59Z",
      "created_at": "2024-05-15T10:30:00Z"
    },
    {
      "id": 2,
      "title": "New Vendor Spotlight",
      "description": "Check out our newest restaurant partners",
      "banner_image": "https://res.cloudinary.com/your-cloud/image/upload/w_1180,h_192,c_fill,f_auto,q_auto/banners/new_vendors.jpg",
      "banner_type": "homepage",
      "click_url": "https://yoursite.com/new-vendors",
      "priority": 5,
      "target_audience": ["new_users"],
      "display_start_date": "2024-05-01T00:00:00Z",
      "display_end_date": null,
      "created_at": "2024-04-20T14:15:00Z"
    }
  ]
}
```

### 2. Create New Banner (Admin)

**POST** `/api/user/banners/`

Create a new banner. Requires admin authentication.

#### Request Body:
```json
{
  "title": "Summer Sale Banner",
  "description": "50% off on all food items",
  "banner_image": "<file_upload>",
  "banner_type": "homepage",
  "status": "active",
  "priority": 10,
  "click_url": "https://yoursite.com/summer-sale",
  "target_audience": ["all_users"],
  "display_start_date": "2024-06-01T00:00:00Z",
  "display_end_date": "2024-08-31T23:59:59Z"
}
```

#### Response:
```json
{
  "success": true,
  "message": "Banner created successfully",
  "banner": {
    "id": 1,
    "title": "Summer Sale Banner",
    "description": "50% off on all food items",
    "banner_image": "https://res.cloudinary.com/your-cloud/image/upload/w_1180,h_192,c_fill,f_auto,q_auto/banners/summer_sale.jpg",
    "banner_type": "homepage",
    "status": "active",
    "priority": 10,
    "click_url": "https://yoursite.com/summer-sale",
    "target_audience": ["all_users"],
    "display_start_date": "2024-06-01T00:00:00Z",
    "display_end_date": "2024-08-31T23:59:59Z",
    "created_at": "2024-05-15T10:30:00Z"
  }
}
```

### 3. Get Banner Details

**GET** `/api/user/banners/{banner_id}/`

Get detailed information about a specific banner.

#### Example Request:
```bash
GET /api/user/banners/1/
```

#### Example Response:
```json
{
  "success": true,
  "banner": {
    "id": 1,
    "title": "Summer Sale Banner",
    "description": "50% off on all food items",
    "banner_image": "https://res.cloudinary.com/your-cloud/image/upload/w_1180,h_192,c_fill,f_auto,q_auto/banners/summer_sale.jpg",
    "banner_type": "homepage",
    "status": "active",
    "priority": 10,
    "click_url": "https://yoursite.com/summer-sale",
    "target_audience": ["all_users"],
    "display_start_date": "2024-06-01T00:00:00Z",
    "display_end_date": "2024-08-31T23:59:59Z",
    "created_by": "admin",
    "created_at": "2024-05-15T10:30:00Z",
    "updated_at": "2024-05-15T10:30:00Z",
    "is_active": true
  }
}
```

### 4. Update Banner (Admin)

**PUT** `/api/user/banners/{banner_id}/`

Update an existing banner. Requires admin authentication.

#### Request Body:
```json
{
  "title": "Updated Summer Sale Banner",
  "priority": 15,
  "status": "active"
}
```

#### Response:
```json
{
  "success": true,
  "message": "Banner updated successfully",
  "banner": {
    "id": 1,
    "title": "Updated Summer Sale Banner",
    "description": "50% off on all food items",
    "banner_image": "https://res.cloudinary.com/your-cloud/image/upload/w_1180,h_192,c_fill,f_auto,q_auto/banners/summer_sale.jpg",
    "banner_type": "homepage",
    "status": "active",
    "priority": 15,
    "click_url": "https://yoursite.com/summer-sale",
    "target_audience": ["all_users"],
    "display_start_date": "2024-06-01T00:00:00Z",
    "display_end_date": "2024-08-31T23:59:59Z",
    "created_at": "2024-05-15T10:30:00Z",
    "updated_at": "2024-05-15T11:45:00Z",
    "is_active": true
  }
}
```

### 5. Delete Banner (Admin)

**DELETE** `/api/user/banners/{banner_id}/`

Delete a banner. Requires admin authentication.

#### Response:
```json
{
  "success": true,
  "message": "Banner \"Summer Sale Banner\" deleted successfully"
}
```

### 6. Admin Banner Management

**GET** `/api/user/banners/admin/`

Get all banners for admin management with pagination. Requires admin authentication.

#### Query Parameters:
- `type` (string, optional): Filter by banner type
- `status` (string, optional): Filter by status
- `page` (int, default: 1): Page number
- `page_size` (int, default: 20): Results per page

#### Example Request:
```bash
GET /api/user/banners/admin/?type=homepage&status=active&page=1&page_size=10
```

#### Example Response:
```json
{
  "success": true,
  "count": 10,
  "total_count": 25,
  "page": 1,
  "page_size": 10,
  "total_pages": 3,
  "has_next": true,
  "has_previous": false,
  "banners": [
    {
      "id": 1,
      "title": "Summer Sale Banner",
      "description": "50% off on all food items",
      "banner_image": "https://res.cloudinary.com/your-cloud/image/upload/w_1180,h_192,c_fill,f_auto,q_auto/banners/summer_sale.jpg",
      "banner_thumbnail": "https://res.cloudinary.com/your-cloud/image/upload/w_300,h_50,c_fill,f_auto,q_auto/banners/summer_sale.jpg",
      "banner_type": "homepage",
      "status": "active",
      "priority": 10,
      "click_url": "https://yoursite.com/summer-sale",
      "target_audience": ["all_users"],
      "display_start_date": "2024-06-01T00:00:00Z",
      "display_end_date": "2024-08-31T23:59:59Z",
      "created_by": "admin",
      "created_at": "2024-05-15T10:30:00Z",
      "updated_at": "2024-05-15T10:30:00Z",
      "is_active": true
    }
  ]
}
```

## Frontend Integration

### Displaying Banners on Homepage

```javascript
// Fetch active banners for homepage
async function loadHomepageBanners() {
  try {
    const response = await fetch('/api/user/banners/?type=homepage&limit=5');
    const data = await response.json();
    
    if (data.success) {
      // Render banners
      data.banners.forEach(banner => {
        renderBanner(banner);
      });
    }
  } catch (error) {
    console.error('Error loading banners:', error);
  }
}

function renderBanner(banner) {
  const bannerContainer = document.getElementById('banner-container');
  
  const bannerElement = document.createElement('div');
  bannerElement.className = 'banner-item';
  bannerElement.innerHTML = `
    <img src="${banner.banner_image}" 
         alt="${banner.title}" 
         class="banner-image"
         style="width: 1180px; height: 192px; object-fit: cover;">
    <div class="banner-overlay">
      <h3>${banner.title}</h3>
      <p>${banner.description}</p>
    </div>
  `;
  
  // Add click handler if click_url exists
  if (banner.click_url) {
    bannerElement.addEventListener('click', () => {
      window.open(banner.click_url, '_blank');
    });
    bannerElement.style.cursor = 'pointer';
  }
  
  bannerContainer.appendChild(bannerElement);
}

// Load banners when page loads
loadHomepageBanners();
```

## Admin Dashboard Integration

### Banner Management Interface

```javascript
// Admin banner management
async function loadBannerManagement() {
  try {
    const response = await fetch('/api/user/banners/admin/?page=1&page_size=20', {
      headers: {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json'
      }
    });
    const data = await response.json();
    
    if (data.success) {
      // Render admin banner list
      data.banners.forEach(banner => {
        renderAdminBannerRow(banner);
      });
      
      // Setup pagination
      setupBannerPagination(data);
    }
  } catch (error) {
    console.error('Error loading banner management:', error);
  }
}

function renderAdminBannerRow(banner) {
  const tbody = document.getElementById('banner-table-body');
  
  const row = document.createElement('tr');
  row.innerHTML = `
    <td>
      <img src="${banner.banner_thumbnail}" 
           alt="${banner.title}" 
           class="banner-thumbnail">
    </td>
    <td>${banner.title}</td>
    <td>${banner.banner_type}</td>
    <td>
      <span class="status-badge status-${banner.status}">
        ${banner.status}
      </span>
    </td>
    <td>${banner.priority}</td>
    <td>${banner.is_active ? 'Yes' : 'No'}</td>
    <td>${banner.created_at}</td>
    <td>
      <button onclick="editBanner(${banner.id})">Edit</button>
      <button onclick="deleteBanner(${banner.id})">Delete</button>
    </td>
  `;
  
  tbody.appendChild(row);
}
```

## Banner Types and Statuses

### Banner Types:
- `homepage` - Homepage banners
- `promotional` - Promotional banners  
- `seasonal` - Seasonal banners
- `vendor_spotlight` - Vendor spotlight banners

### Banner Statuses:
- `active` - Currently active and displayed
- `inactive` - Not displayed
- `scheduled` - Scheduled for future display
- `expired` - Past end date

### Target Audiences:
- `all_users` - Display to all users
- `new_users` - Display to new users only
- `premium_users` - Display to premium users only
- `returning_users` - Display to returning users only

## Cloudinary Integration Features

1. **Automatic Optimization**: Images are automatically optimized for web delivery
2. **Multiple Sizes**: Full-size banners (1180x192) and thumbnails (300x50) for admin preview
3. **Format Optimization**: Automatic format detection and quality optimization
4. **Performance**: Optimized URLs for faster loading and better user experience

## Key Benefits

1. **Admin Control**: Full banner management from admin dashboard
2. **Scheduling**: Time-based banner display with start/end dates
3. **Priority System**: Control banner display order
4. **Targeting**: Display banners to specific user groups
5. **Cloudinary Integration**: Optimized image delivery
6. **Public API**: Frontend can fetch banners without authentication
7. **Admin API**: Full CRUD operations for banner management

This banner system provides everything needed for managing homepage banners with professional admin controls and optimized frontend delivery! 🎉






