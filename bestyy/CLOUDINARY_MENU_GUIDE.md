# Cloudinary Menu Image Integration Guide

This guide explains how to upload and display menu item images using Cloudinary in the vendor menu management system.

## Overview

The menu system is configured to use Cloudinary for image storage and delivery. Images are automatically uploaded to Cloudinary when vendors create or update menu items, and the system provides multiple image sizes for optimal frontend display.

## Image Upload

### Frontend Upload Process

1. **File Selection**: Users select an image file (JPG, PNG, WebP, etc.)
2. **Form Data**: Include the image in a `multipart/form-data` request
3. **Automatic Processing**: Cloudinary automatically:
   - Resizes images to 800x600px (fill crop)
   - Generates multiple sizes (thumbnail, medium, large)
   - Optimizes for web delivery
   - Stores in organized folders: `menu_items/vendor_{vendor_id}/`

### Upload Example

```javascript
// Frontend JavaScript example
const formData = new FormData();
formData.append('dish_name', 'Jollof Rice');
formData.append('item_description', 'Delicious Nigerian jollof rice');
formData.append('price', '15.99');
formData.append('category', 'Main Course');
formData.append('image', imageFile); // File from input[type="file"]
formData.append('available_now', 'true');
formData.append('quantity', '50');

fetch('/api/user/vendors/menu/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`
    },
    body: formData
});
```

## Image Display

### Response Structure

When you fetch menu items, the API returns image URLs in multiple formats:

```json
{
    "id": 1,
    "dish_name": "Jollof Rice",
    "price": 15.99,
    "category": "Main Course",
    "image_url": "https://res.cloudinary.com/your-cloud/image/upload/v1234567890/menu_items/vendor_5/jollof_rice.jpg",
    "image_urls": {
        "thumbnail": "https://res.cloudinary.com/your-cloud/image/upload/w_200,h_150,c_fill,q_auto/menu_items/vendor_5/jollof_rice.jpg",
        "medium": "https://res.cloudinary.com/your-cloud/image/upload/w_400,h_300,c_fill,q_auto/menu_items/vendor_5/jollof_rice.jpg",
        "large": "https://res.cloudinary.com/your-cloud/image/upload/w_800,h_600,c_fill,q_auto/menu_items/vendor_5/jollof_rice.jpg",
        "original": "https://res.cloudinary.com/your-cloud/image/upload/menu_items/vendor_5/jollof_rice.jpg"
    },
    "available_now": true,
    "quantity": 50
}
```

### Frontend Display Examples

#### React Component Example

```jsx
import React from 'react';

const MenuItemCard = ({ item }) => {
    return (
        <div className="menu-item-card">
            <div className="image-container">
                <img 
                    src={item.image_urls?.medium || item.image_url} 
                    alt={item.dish_name}
                    loading="lazy"
                    onError={(e) => {
                        e.target.src = '/placeholder-food.jpg';
                    }}
                />
            </div>
            <div className="item-details">
                <h3>{item.dish_name}</h3>
                <p className="price">₦{item.price}</p>
                <p className="category">{item.category}</p>
            </div>
        </div>
    );
};
```

#### Responsive Image Display

```jsx
const ResponsiveMenuImage = ({ item, size = 'medium' }) => {
    const getImageSrc = () => {
        if (item.image_urls) {
            return item.image_urls[size] || item.image_urls.medium;
        }
        return item.image_url;
    };

    return (
        <picture>
            <source 
                media="(max-width: 480px)" 
                srcSet={item.image_urls?.thumbnail || item.image_url} 
            />
            <source 
                media="(max-width: 768px)" 
                srcSet={item.image_urls?.medium || item.image_url} 
            />
            <img 
                src={getImageSrc()} 
                alt={item.dish_name}
                loading="lazy"
            />
        </picture>
    );
};
```

#### CSS Styling

```css
.menu-item-card {
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.image-container {
    width: 100%;
    height: 200px;
    overflow: hidden;
}

.image-container img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.3s ease;
}

.image-container:hover img {
    transform: scale(1.05);
}

/* Responsive grid */
.menu-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 20px;
    padding: 20px;
}

@media (max-width: 768px) {
    .menu-grid {
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 15px;
        padding: 15px;
    }
}
```

## Image Sizes and Use Cases

| Size | Dimensions | Use Case |
|------|------------|----------|
| `thumbnail` | 200x150px | Menu item lists, small cards |
| `medium` | 400x300px | Menu item cards, medium displays |
| `large` | 800x600px | Detailed views, modals |
| `original` | Original size | Full-size viewing, downloads |

## Error Handling

### Image Load Failures

```javascript
const MenuImage = ({ item }) => {
    const [imageError, setImageError] = useState(false);
    
    const handleImageError = () => {
        setImageError(true);
    };
    
    if (imageError) {
        return (
            <div className="image-placeholder">
                <span>No Image</span>
            </div>
        );
    }
    
    return (
        <img 
            src={item.image_urls?.medium || item.image_url}
            alt={item.dish_name}
            onError={handleImageError}
            loading="lazy"
        />
    );
};
```

### Fallback Images

```css
.image-placeholder {
    width: 100%;
    height: 200px;
    background: #f5f5f5;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #999;
    font-size: 14px;
}
```

## Performance Optimization

### Lazy Loading

```jsx
// Use native lazy loading
<img 
    src={item.image_urls?.medium} 
    alt={item.dish_name}
    loading="lazy"
/>

// Or use Intersection Observer for better control
const LazyImage = ({ item }) => {
    const [isLoaded, setIsLoaded] = useState(false);
    const imgRef = useRef();
    
    useEffect(() => {
        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    setIsLoaded(true);
                    observer.disconnect();
                }
            },
            { threshold: 0.1 }
        );
        
        if (imgRef.current) {
            observer.observe(imgRef.current);
        }
        
        return () => observer.disconnect();
    }, []);
    
    return (
        <div ref={imgRef} className="image-container">
            {isLoaded ? (
                <img 
                    src={item.image_urls?.medium} 
                    alt={item.dish_name}
                />
            ) : (
                <div className="image-placeholder">Loading...</div>
            )}
        </div>
    );
};
```

## API Endpoints

### Create Menu Item with Image
```
POST /api/user/vendors/menu/
Content-Type: multipart/form-data
Authorization: Bearer <token>

dish_name=Jollof Rice
item_description=Delicious Nigerian jollof rice
price=15.99
category=Main Course
image=<file>
available_now=true
quantity=50
```

### Update Menu Item Image
```
PUT /api/user/vendors/menu/1/
Content-Type: multipart/form-data
Authorization: Bearer <token>

image=<new_file>
```

### Get Menu Items
```
GET /api/user/vendors/menu/
Authorization: Bearer <token>
```

## Best Practices

1. **Always provide alt text** for accessibility
2. **Use appropriate image sizes** for different contexts
3. **Implement lazy loading** for better performance
4. **Handle image load errors** gracefully
5. **Use WebP format** when possible (Cloudinary handles this automatically)
6. **Optimize for mobile** with responsive images
7. **Cache images** appropriately in your frontend

## Troubleshooting

### Common Issues

1. **Images not loading**: Check if Cloudinary credentials are properly configured
2. **Large file uploads**: Ensure your server can handle large files (default Django limit is 2.5MB)
3. **CORS issues**: Make sure your frontend domain is allowed in Cloudinary settings
4. **Slow loading**: Use appropriate image sizes and implement lazy loading

### Debug Information

You can check Cloudinary configuration by calling:
```
GET /api/user/test/cloudinary/
```

This will return your current Cloudinary configuration status.

