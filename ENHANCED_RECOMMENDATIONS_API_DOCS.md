# Enhanced Recommendations API Documentation

## Overview
The Enhanced Recommendations API provides intelligent food recommendations with slideshow functionality, meal-time categorization, and vendor attraction metrics optimized for startup growth.

## Base Endpoint
```
GET /api/user/recommendations/
```

## Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `city` | string | - | Filter recommendations by city (e.g., "Lagos", "Abuja") |
| `slideshow` | boolean | false | Enable slideshow mode with multiple images per vendor |
| `vendor_benefits` | boolean | true | Include vendor attraction metrics in response |
| `meal_time` | string | auto | Override automatic meal detection ("breakfast", "lunch", "dinner", "snacks") |
| `limit` | integer | 10 | Maximum number of vendors to return |

## Request Flow

### 1. Standard Recommendations Flow
```
GET /api/user/recommendations/?city=Lagos
```

**Process:**
1. Get current time for meal categorization
2. Find active vendors in specified city
3. Calculate popularity scores based on orders
4. Return vendor recommendations with basic info

### 2. Enhanced Slideshow Flow
```
GET /api/user/recommendations/?city=Lagos&slideshow=true
```

**Process:**
1. Get current time for meal categorization
2. Find active vendors in specified city
3. For each vendor:
   - Get meal-relevant menu items (breakfast/lunch/dinner/snacks)
   - Calculate meal relevance scores
   - Generate slideshow with multiple optimized images
   - Include vendor attraction metrics
4. Return enhanced recommendations with slideshow data

### 3. Startup Metrics Flow
```
GET /api/user/recommendations/?city=Lagos&slideshow=true&vendor_benefits=true
```

**Process:**
1. Execute enhanced slideshow flow
2. Calculate additional vendor attraction metrics:
   - Commission rates and fee structures
   - Marketing support opportunities
   - Growth potential indicators
   - Partnership benefits
3. Return comprehensive startup-focused data

## Response Formats

### Standard Response (slideshow=false)
```json
{
    "recommendations": [
        {
            "vendor_id": 1,
            "vendor_name": "Mama's Kitchen",
            "logo": "https://res.cloudinary.com/dpv2s7bzq/image/upload/c_fill,w_150,h_150/vendor_logos/1/logo.jpg",
            "cover_image": "https://res.cloudinary.com/dpv2s7bzq/image/upload/c_fill,w_600,h_400/vendor_covers/1/cover.jpg",
            "cuisine_type": "Nigerian",
            "rating": 4.5,
            "delivery_time": "25-35 mins",
            "delivery_fee": 500,
            "is_available": true,
            "distance": "2.3 km",
            "popularity_score": 85.7,
            "total_orders": 342,
            "city": "Lagos"
        }
    ],
    "current_meal_time": "lunch",
    "total_vendors": 1,
    "city": "Lagos"
}
```

### Enhanced Slideshow Response (slideshow=true)
```json
{
    "recommendations": [
        {
            "vendor_id": 1,
            "vendor_name": "Mama's Kitchen",
            "primary_image": "https://res.cloudinary.com/dpv2s7bzq/image/upload/c_fill,w_600,h_400/products/1/jollof.jpg",
            "logo": "https://res.cloudinary.com/dpv2s7bzq/image/upload/c_fill,w_150,h_150/products/1/jollof.jpg",
            "cover_image": "https://res.cloudinary.com/dpv2s7bzq/image/upload/c_fill,w_600,h_400/vendor_covers/1/cover.jpg",
            "cuisine_type": "Nigerian",
            "rating": 4.5,
            "delivery_time": "25-35 mins",
            "delivery_fee": 500,
            "is_available": true,
            "distance": "2.3 km",
            "popularity_score": 85.7,
            "total_orders": 342,
            "city": "Lagos",
            "display_priority": "slideshow",
            "slideshow": {
                "images": [
                    {
                        "url": "https://res.cloudinary.com/dpv2s7bzq/image/upload/c_fill,w_600,h_400/products/1/jollof.jpg",
                        "thumbnail": "https://res.cloudinary.com/dpv2s7bzq/image/upload/c_fill,w_150,h_150/products/1/jollof.jpg",
                        "detail": "https://res.cloudinary.com/dpv2s7bzq/image/upload/c_fill,w_800,h_600/products/1/jollof.jpg",
                        "title": "Jollof Rice Special",
                        "description": "Delicious Nigerian jollof rice with chicken",
                        "price": 2500,
                        "meal_category": "lunch",
                        "relevance_score": 92.5
                    },
                    {
                        "url": "https://res.cloudinary.com/dpv2s7bzq/image/upload/c_fill,w_600,h_400/products/2/egusi.jpg",
                        "thumbnail": "https://res.cloudinary.com/dpv2s7bzq/image/upload/c_fill,w_150,h_150/products/2/egusi.jpg",
                        "detail": "https://res.cloudinary.com/dpv2s7bzq/image/upload/c_fill,w_800,h_600/products/2/egusi.jpg",
                        "title": "Egusi Soup",
                        "description": "Traditional Nigerian egusi soup with assorted meat",
                        "price": 3000,
                        "meal_category": "lunch",
                        "relevance_score": 88.3
                    }
                ],
                "total_items": 8,
                "meal_specific_items": 6
            },
            "meal_categorized_items": {
                "breakfast": 2,
                "lunch": 6,
                "dinner": 4,
                "snacks": 3,
                "current_meal_items": 6
            }
        }
    ],
    "current_meal_time": "lunch",
    "total_vendors": 1,
    "city": "Lagos",
    "slideshow_enabled": true
}
```

### Startup Metrics Response (vendor_benefits=true)
```json
{
    "recommendations": [
        {
            "vendor_id": 1,
            "vendor_name": "Mama's Kitchen",
            "logo": "https://res.cloudinary.com/dpv2s7bzq/image/upload/c_fill,w_150,h_150/vendor_logos/1/logo.jpg",
            "cover_image": "https://res.cloudinary.com/dpv2s7bzq/image/upload/c_fill,w_600,h_400/vendor_covers/1/cover.jpg",
            "cuisine_type": "Nigerian",
            "rating": 4.5,
            "delivery_time": "25-35 mins",
            "delivery_fee": 500,
            "is_available": true,
            "distance": "2.3 km",
            "popularity_score": 85.7,
            "total_orders": 342,
            "city": "Lagos",
            "slideshow": {
                "images": [
                    {
                        "url": "https://res.cloudinary.com/dpv2s7bzq/image/upload/c_fill,w_600,h_400/products/1/jollof.jpg",
                        "thumbnail": "https://res.cloudinary.com/dpv2s7bzq/image/upload/c_fill,w_150,h_150/products/1/jollof.jpg",
                        "detail": "https://res.cloudinary.com/dpv2s7bzq/image/upload/c_fill,w_800,h_600/products/1/jollof.jpg",
                        "title": "Jollof Rice Special",
                        "description": "Delicious Nigerian jollof rice with chicken",
                        "price": 2500,
                        "meal_category": "lunch",
                        "relevance_score": 92.5
                    }
                ],
                "total_items": 8,
                "meal_specific_items": 6
            },
            "vendor_attraction_metrics": {
                "partnership_score": 87.5,
                "revenue_potential": "₦45,000 - ₦75,000/month",
                "commission_rate": "12%",
                "onboarding_incentives": [
                    "Zero commission for first month",
                    "Free professional food photography",
                    "Premium listing placement"
                ],
                "marketing_support": {
                    "social_media_promotion": true,
                    "featured_vendor_opportunities": true,
                    "email_marketing_inclusion": true,
                    "app_banner_placement": true
                },
                "growth_indicators": {
                    "market_demand": "High",
                    "competition_level": "Medium",
                    "customer_retention": "85%",
                    "order_frequency": "3.2 orders/week"
                },
                "support_benefits": {
                    "dedicated_account_manager": true,
                    "24_7_technical_support": true,
                    "business_analytics_dashboard": true,
                    "inventory_management_tools": true
                }
            }
        }
    ],
    "current_meal_time": "lunch",
    "total_vendors": 1,
    "city": "Lagos",
    "slideshow_enabled": true,
    "vendor_benefits_included": true,
    "startup_optimization": {
        "total_potential_partners": 45,
        "average_partnership_score": 82.3,
        "market_penetration": "23%",
        "growth_opportunity": "High"
    }
}
```

## Meal Time Categorization

### Automatic Time Detection
- **Breakfast**: 6:00 AM - 11:00 AM
- **Lunch**: 11:00 AM - 4:00 PM  
- **Dinner**: 4:00 PM - 10:00 PM
- **Snacks**: 10:00 PM - 6:00 AM

### Manual Override
Use the `meal_time` parameter to override automatic detection:
```
GET /api/user/recommendations/?city=Lagos&slideshow=true&meal_time=breakfast
```

## Image Optimization Sizes

### Slideshow Images (High Quality)
- **Main**: 800x500px (slideshow display) - q_90, auto format, auto DPR
- **Mobile**: 400x300px (mobile display) - q_85, auto format, auto DPR  
- **Thumbnail**: 200x150px (navigation dots) - q_85, auto format, auto DPR
- **Detail**: 1200x800px (full-screen view) - q_95, auto format, auto DPR

### Vendor Images (High Quality)
- **Logo**: 400x400px (main display) - q_90, auto format, auto DPR
- **Logo Thumbnail**: 200x200px (small display) - q_90, auto format, auto DPR
- **Cover**: 1000x500px (card background) - q_90, auto format, auto DPR

### Quality Parameters
- **q_90/q_95**: High quality compression (90-95%)
- **f_auto**: Automatic format selection (WebP, AVIF, etc.)
- **dpr_auto**: Automatic device pixel ratio optimization
- **c_fill**: Smart crop to maintain aspect ratio

## Error Responses

### 400 Bad Request
```json
{
    "error": "Invalid meal_time parameter",
    "message": "meal_time must be one of: breakfast, lunch, dinner, snacks",
    "code": "INVALID_MEAL_TIME"
}
```

### 404 Not Found
```json
{
    "error": "No vendors found",
    "message": "No active vendors found in the specified city",
    "code": "NO_VENDORS_FOUND",
    "city": "InvalidCity"
}
```

### 500 Internal Server Error
```json
{
    "error": "Slideshow generation failed",
    "message": "Unable to process vendor slideshow data",
    "code": "SLIDESHOW_ERROR",
    "vendor_id": 1
}
```

## Performance Considerations

### Response Times
- **Standard**: ~150ms
- **Slideshow**: ~300ms  
- **With Benefits**: ~450ms

### Caching
- Vendor data cached for 15 minutes
- Image URLs cached for 1 hour
- Meal categorization cached for 30 minutes

### Rate Limiting
- 100 requests per minute per user
- 1000 requests per hour per user

## Usage Examples

### Get Morning Breakfast Recommendations
```
GET /api/user/recommendations/?city=Lagos&slideshow=true&meal_time=breakfast&limit=5
```

### Get Evening Dinner with Startup Metrics
```
GET /api/user/recommendations/?city=Abuja&slideshow=true&vendor_benefits=true&meal_time=dinner
```

### Get Simple Lunch Recommendations
```
GET /api/user/recommendations/?city=Lagos&meal_time=lunch
```

## Image Display Priority

The API prioritizes slideshow images over static logos for better visual engagement:

### Display Logic
1. **Primary Display**: Always use `slideshow.images` array if available
2. **Fallback**: Use `primary_image` if slideshow is empty
3. **Logo**: Use as small thumbnail or fallback only

### Frontend Implementation Guide
```javascript
// Recommended display logic
const getDisplayImages = (vendor) => {
    if (vendor.slideshow && vendor.slideshow.images.length > 0) {
        // Use slideshow for main display
        return {
            type: 'slideshow',
            images: vendor.slideshow.images,
            primary: vendor.slideshow.images[0].url
        };
    } else if (vendor.primary_image) {
        // Fallback to primary image
        return {
            type: 'single',
            images: [{ url: vendor.primary_image }],
            primary: vendor.primary_image
        };
    } else {
        // Final fallback to logo
        return {
            type: 'single',
            images: [{ url: vendor.logo }],
            primary: vendor.logo
        };
    }
};
```

### Display Priority Field
- `display_priority: "slideshow"` - Use slideshow for main display
- `display_priority: "logo"` - Use logo as fallback (no menu items available)

## Integration Notes

1. **Authentication**: No authentication required for public recommendations
2. **CORS**: Enabled for all frontend origins
3. **Content-Type**: Returns `application/json`
4. **HTTP Methods**: Only GET supported
5. **Pagination**: Use `limit` parameter (max 50 vendors per request)
6. **Image Priority**: Always check `slideshow` first, then `primary_image`, then `logo`

## Startup Growth Features

### Vendor Attraction Metrics
- Partnership scoring algorithm
- Revenue potential calculations
- Onboarding incentive tracking
- Marketing support benefits
- Growth indicator analysis

### Market Intelligence
- Competition analysis
- Demand forecasting
- Customer retention metrics
- Order frequency patterns

This enhanced API provides comprehensive data for both end-users seeking food recommendations and startup teams looking to attract and retain vendor partners.