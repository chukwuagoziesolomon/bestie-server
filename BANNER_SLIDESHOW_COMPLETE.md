# Banner Slideshow System - Complete Guide

## ✅ Implementation Status: **COMPLETE**

The banner system has been successfully re-implemented with full functionality for admin uploads and frontend slideshow display.

---

## 🎯 Overview

This system allows admins to upload multiple banner images (recommended size: **1180x192 pixels**) that can be displayed as a slideshow on the frontend.

### Key Features:
- ✅ Multiple banner upload support
- ✅ Cloudinary automatic optimization (1180x192)
- ✅ Priority-based ordering for slideshow
- ✅ Banner scheduling (start/end dates)
- ✅ Multiple banner types (homepage, promotional, seasonal, vendor_spotlight)
- ✅ Click-through URLs for banners
- ✅ Active/Inactive status control
- ✅ Django Admin integration

---

## 📡 API Endpoints

### **PUBLIC ENDPOINTS** (No authentication required)

#### 1. Get All Active Banners
```http
GET /api/user/banners/
```

**Query Parameters:**
- `limit` (optional): Maximum number of banners to return (default: 10)
- `type` (optional): Filter by banner type (homepage, promotional, seasonal, vendor_spotlight)

**Response:**
```json
{
  "success": true,
  "count": 3,
  "banner_type": "homepage",
  "banners": [
    {
      "id": 1,
      "title": "Summer Sale",
      "description": "Get 50% off on all items",
      "image_url": "https://res.cloudinary.com/.../upload/w_1180,h_192,c_fill,f_auto,q_auto/banners/...",
      "thumbnail_url": "https://res.cloudinary.com/.../upload/w_300,h_46,c_fill,f_auto,q_auto/banners/...",
      "banner_type": "promotional",
      "priority": 10,
      "click_url": "https://example.com/sale",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### 2. Get Banner Details
```http
GET /api/user/banners/{id}/
```

**Response:**
```json
{
  "success": true,
  "banner": {
    "id": 1,
    "title": "Summer Sale",
    "description": "Get 50% off on all items",
    "image_url": "https://res.cloudinary.com/.../w_1180,h_192/...",
    "thumbnail_url": "https://res.cloudinary.com/.../w_300,h_46/...",
    "banner_type": "promotional",
    "status": "active",
    "priority": 10,
    "click_url": "https://example.com/sale",
    "display_start_date": "2024-01-01T00:00:00Z",
    "display_end_date": "2024-12-31T23:59:59Z",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

---

### **ADMIN ENDPOINTS** (Requires authentication + staff privileges)

#### 3. Create New Banner
```http
POST /api/user/banners/
Content-Type: multipart/form-data
Authorization: Bearer <token>
```

**Form Data:**
- `banner_image` (required): Image file (recommended 1180x192 pixels)
- `title` (required): Banner title
- `description` (optional): Banner description
- `banner_type` (optional): homepage | promotional | seasonal | vendor_spotlight (default: homepage)
- `status` (optional): active | inactive | scheduled | expired (default: active)
- `priority` (optional): Integer for ordering (higher = appears first) (default: 0)
- `click_url` (optional): URL to redirect when clicked
- `is_active` (optional): true | false (default: true)
- `display_start_date` (optional): ISO datetime string
- `display_end_date` (optional): ISO datetime string

**Response:**
```json
{
  "success": true,
  "message": "Banner created successfully",
  "banner": {
    "id": 1,
    "title": "New Banner",
    "description": "Banner description",
    "image_url": "https://res.cloudinary.com/.../w_1180,h_192/...",
    "banner_type": "homepage",
    "status": "active",
    "priority": 0,
    "click_url": "",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

#### 4. Update Banner
```http
PUT /api/user/banners/{id}/
Content-Type: multipart/form-data
Authorization: Bearer <token>
```

**Form Data:** (All optional - only send fields to update)
- `banner_image`: New image file
- `title`: New title
- `description`: New description
- `banner_type`: New type
- `status`: New status
- `priority`: New priority
- `click_url`: New click URL
- `is_active`: New active status
- `display_start_date`: New start date
- `display_end_date`: New end date

**Response:** Same as Create Banner

#### 5. Delete Banner
```http
DELETE /api/user/banners/{id}/
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "message": "Banner deleted successfully"
}
```

---

## 💻 Frontend Integration

### React/Next.js Example

```javascript
import React, { useState, useEffect } from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Autoplay, Pagination } from 'swiper/modules';
import 'swiper/css';
import 'swiper/css/pagination';

function BannerSlideshow() {
  const [banners, setBanners] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBanners();
  }, []);

  const fetchBanners = async () => {
    try {
      const response = await fetch(
        'https://bestie-server.onrender.com/api/user/banners/?limit=5'
      );
      const data = await response.json();

      if (data.success) {
        setBanners(data.banners);
      }
    } catch (error) {
      console.error('Failed to fetch banners:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBannerClick = (banner) => {
    if (banner.click_url) {
      window.open(banner.click_url, '_blank');
    }
  };

  if (loading) return <div>Loading banners...</div>;
  if (banners.length === 0) return null;

  return (
    <div className="banner-slideshow">
      <Swiper
        modules={[Autoplay, Pagination]}
        spaceBetween={0}
        slidesPerView={1}
        autoplay={{
          delay: 5000,
          disableOnInteraction: false,
        }}
        pagination={{ clickable: true }}
        loop={banners.length > 1}
      >
        {banners.map((banner) => (
          <SwiperSlide key={banner.id}>
            <div
              className="banner-slide"
              onClick={() => handleBannerClick(banner)}
              style={{
                cursor: banner.click_url ? 'pointer' : 'default',
              }}
            >
              <img
                src={banner.image_url}
                alt={banner.title}
                style={{
                  width: '100%',
                  height: 'auto',
                  objectFit: 'cover',
                }}
              />
              {banner.title && (
                <div className="banner-overlay">
                  <h2>{banner.title}</h2>
                  {banner.description && <p>{banner.description}</p>}
                </div>
              )}
            </div>
          </SwiperSlide>
        ))}
      </Swiper>
    </div>
  );
}

export default BannerSlideshow;
```

### Simple JavaScript (No Framework)

```javascript
// Fetch banners
fetch('https://bestie-server.onrender.com/api/user/banners/?limit=5')
  .then(response => response.json())
  .then(data => {
    if (data.success && data.banners.length > 0) {
      createSlideshow(data.banners);
    }
  })
  .catch(error => console.error('Error:', error));

function createSlideshow(banners) {
  const container = document.getElementById('banner-container');
  let currentIndex = 0;

  // Create slides
  banners.forEach((banner, index) => {
    const slide = document.createElement('div');
    slide.className = 'banner-slide';
    slide.style.display = index === 0 ? 'block' : 'none';
    
    const img = document.createElement('img');
    img.src = banner.image_url;
    img.alt = banner.title;
    img.style.width = '100%';
    img.style.height = 'auto';
    
    if (banner.click_url) {
      slide.style.cursor = 'pointer';
      slide.onclick = () => window.open(banner.click_url, '_blank');
    }
    
    slide.appendChild(img);
    container.appendChild(slide);
  });

  // Auto-rotate every 5 seconds
  setInterval(() => {
    const slides = container.querySelectorAll('.banner-slide');
    slides[currentIndex].style.display = 'none';
    currentIndex = (currentIndex + 1) % banners.length;
    slides[currentIndex].style.display = 'block';
  }, 5000);
}
```

---

## 🔧 Admin Upload Guide

### Method 1: Django Admin Panel

1. Navigate to: `https://bestie-server.onrender.com/admin/`
2. Login with admin credentials
3. Click on **"Banners"** under USER section
4. Click **"Add Banner"** button
5. Fill in the form:
   - **Title**: Banner name
   - **Description**: Optional text
   - **Banner Image**: Upload 1180x192 image
   - **Banner Type**: Choose type
   - **Status**: Set to "Active"
   - **Priority**: Higher numbers appear first (0 = lowest)
   - **Click URL**: Optional redirect URL
   - **Is Active**: Check to enable
6. Click **"Save"**

### Method 2: API Upload (JavaScript)

```javascript
async function uploadBanner(formData, authToken) {
  const response = await fetch(
    'https://bestie-server.onrender.com/api/user/banners/',
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
      },
      body: formData, // FormData object with banner_image, title, etc.
    }
  );

  const data = await response.json();
  return data;
}

// Example usage
const formData = new FormData();
formData.append('banner_image', fileInput.files[0]);
formData.append('title', 'Summer Sale 2024');
formData.append('description', 'Get 50% off all items');
formData.append('banner_type', 'promotional');
formData.append('priority', '10');
formData.append('click_url', 'https://example.com/sale');
formData.append('is_active', 'true');

const result = await uploadBanner(formData, adminToken);
console.log(result);
```

### Method 3: cURL Example

```bash
curl -X POST https://bestie-server.onrender.com/api/user/banners/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "banner_image=@/path/to/banner.jpg" \
  -F "title=Summer Sale" \
  -F "description=Get 50% off" \
  -F "banner_type=promotional" \
  -F "priority=10" \
  -F "is_active=true"
```

---

## 📊 Database Schema

### Banner Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key (auto-generated) |
| `title` | CharField | Banner title (max 200 chars) |
| `description` | TextField | Optional description |
| `banner_image` | ImageField | Banner image (uploaded to Cloudinary) |
| `banner_type` | CharField | Type: homepage, promotional, seasonal, vendor_spotlight |
| `status` | CharField | Status: active, inactive, scheduled, expired |
| `priority` | Integer | Display order (higher = first) |
| `click_url` | URLField | Optional redirect URL |
| `display_start_date` | DateTimeField | Optional start date |
| `display_end_date` | DateTimeField | Optional end date |
| `is_active` | BooleanField | Active status |
| `created_by` | ForeignKey | Admin who created it |
| `created_at` | DateTimeField | Creation timestamp |
| `updated_at` | DateTimeField | Last update timestamp |

---

## 🎨 Image Optimization

Banners are automatically optimized by Cloudinary:

### Full Banner (Frontend Display):
```
w_1180,h_192,c_fill,f_auto,q_auto
```
- Width: 1180px
- Height: 192px
- Format: Auto (WebP when supported)
- Quality: Auto-optimized

### Thumbnail (Admin Preview):
```
w_300,h_46,c_fill,f_auto,q_auto
```
- Width: 300px
- Height: 46px
- Used for admin listings

---

## 🔍 Banner Display Logic

A banner is displayed on the frontend if **ALL** these conditions are met:

1. ✅ `is_active = true`
2. ✅ `status = 'active'`
3. ✅ `display_start_date` is null OR current time >= start date
4. ✅ `display_end_date` is null OR current time <= end date

Banners are ordered by:
1. **Priority** (descending - higher first)
2. **Created At** (descending - newer first)

---

## 🧪 Testing

Run the test script:
```bash
python test_banner_system.py
```

This will verify:
- ✅ GET endpoint works
- ✅ Filtering by type works
- ✅ Limit parameter works
- ✅ Response structure is correct

---

## 🚀 Deployment Notes

### Already Deployed:
- ✅ Banner model created
- ✅ Database migration applied
- ✅ API endpoints enabled
- ✅ Django Admin configured
- ✅ Cloudinary integration active

### No Additional Steps Required:
The banner system is **production-ready** on:
- **Backend**: https://bestie-server.onrender.com
- **Admin Panel**: https://bestie-server.onrender.com/admin/

---

## 📝 Example Banner Types

### 1. Homepage Banner
- Promotes main features
- High priority
- Always visible

### 2. Promotional Banner
- Sales and discounts
- Time-limited
- With click URLs to sale pages

### 3. Seasonal Banner
- Holiday/seasonal campaigns
- Scheduled start/end dates
- Themed designs

### 4. Vendor Spotlight
- Featured vendors
- Click URL to vendor profile
- Rotating weekly/monthly

---

## ⚡ Quick Start Checklist

1. ✅ Upload banner via Django Admin
2. ✅ Set priority and status to "active"
3. ✅ Frontend fetches from `/api/user/banners/?limit=5`
4. ✅ Display in slideshow component
5. ✅ Implement click handler for `click_url`

---

## 🐛 Troubleshooting

### Banner Not Showing?

Check:
1. Is `is_active = true`?
2. Is `status = 'active'`?
3. Is current date within `display_start_date` and `display_end_date` range?
4. Does banner have an uploaded image?

### Image Not Loading?

Check:
1. Cloudinary credentials configured correctly
2. Image uploaded successfully (check Django Admin)
3. Image URL is accessible (test in browser)

### API Returns Empty Array?

Reasons:
1. No banners uploaded yet
2. All banners are inactive
3. All banners are outside their display date range
4. Filter by type excludes all banners

---

## 📞 Support

For issues or questions:
- Check Django logs: `python manage.py runserver`
- Test API: `python test_banner_system.py`
- Verify banner status in Django Admin

---

**System Status**: ✅ **FULLY OPERATIONAL**
