# Banner System - Quick Reference

## 🎯 Purpose
Allow admins to upload banner images (1180x192) for frontend slideshow display.

---

## 📡 API Endpoints

### Frontend (Public)
```bash
# Get all active banners for slideshow
GET /api/user/banners/?limit=5

# Get specific banner
GET /api/user/banners/{id}/
```

### Admin (Auth Required)
```bash
# Upload new banner
POST /api/user/banners/
Content-Type: multipart/form-data
Authorization: Bearer <token>

# Update banner
PUT /api/user/banners/{id}/

# Delete banner
DELETE /api/user/banners/{id}/
```

---

## 💻 Frontend Code (React)

```javascript
// Fetch banners
const response = await fetch('https://bestie-server.onrender.com/api/user/banners/?limit=5');
const data = await response.json();

if (data.success) {
  const banners = data.banners; // Array of banner objects
  // Each banner has: id, title, description, image_url, click_url, priority
}
```

---

## 📤 Admin Upload

### Via Django Admin:
1. Go to: https://bestie-server.onrender.com/admin/
2. Click "Banners" → "Add Banner"
3. Upload 1180x192 image
4. Set priority (higher = first)
5. Save

### Via API:
```javascript
const formData = new FormData();
formData.append('banner_image', file);
formData.append('title', 'Banner Title');
formData.append('priority', '10');
formData.append('is_active', 'true');

await fetch('https://bestie-server.onrender.com/api/user/banners/', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: formData
});
```

---

## 🎨 Banner Types
- `homepage` - Main page banners
- `promotional` - Sales/discounts
- `seasonal` - Holiday/seasonal
- `vendor_spotlight` - Featured vendors

---

## ✅ Display Requirements
Banner shows if ALL true:
- ✅ `is_active = true`
- ✅ `status = 'active'`
- ✅ Within display date range (if set)

Order: Priority (high to low) → Created date (new to old)

---

## 🖼️ Image Specs
- **Recommended Size**: 1180x192 pixels
- **Format**: JPG, PNG, WebP
- **Optimization**: Automatic via Cloudinary
- **URLs**: 
  - Full: `/upload/w_1180,h_192,c_fill,f_auto,q_auto/`
  - Thumbnail: `/upload/w_300,h_46,c_fill,f_auto,q_auto/`

---

## 🧪 Test
```bash
python test_banner_system.py
```

---

## 📊 Response Structure
```json
{
  "success": true,
  "count": 3,
  "banners": [
    {
      "id": 1,
      "title": "Summer Sale",
      "description": "50% off",
      "image_url": "https://cloudinary.com/.../w_1180,h_192/...",
      "thumbnail_url": "https://cloudinary.com/.../w_300,h_46/...",
      "banner_type": "promotional",
      "priority": 10,
      "click_url": "https://example.com/sale",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

## 🚀 Status
✅ **LIVE** - https://bestie-server.onrender.com/api/user/banners/
