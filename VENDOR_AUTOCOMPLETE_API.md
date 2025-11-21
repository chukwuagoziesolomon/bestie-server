# 🔍 Restaurant/Vendor Autocomplete Search API

## Overview
Fast, intelligent autocomplete search for restaurants/vendors with smart ranking and filtering capabilities.

## Endpoints

### 1. Autocomplete Search (Full Details)
**`GET /api/user/vendors/autocomplete/`**

Fast search with complete vendor information and smart ranking.

#### Parameters
- `q` (required): Search query (minimum 2 characters)
- `limit` (optional): Maximum results (default: 10, max: 50)
- `location` (optional): Filter by location/area
- `category` (optional): Filter by business category

#### Example Request
```bash
GET /api/user/vendors/autocomplete/?q=jo&limit=5&location=Lagos
```

#### Example Response
```json
{
  "success": true,
  "query": "jo",
  "count": 3,
  "results": [
    {
      "id": 2,
      "business_name": "Jos Suya Spot",
      "category": "Street Food",
      "address": "456 Food Avenue, Abuja",
      "service_areas": "Garki, Wuse, Maitama",
      "description": "Best suya in town with special Jos flavors",
      "logo": "http://localhost:8000/media/vendor_logos/jos.jpg",
      "cover_image": "http://localhost:8000/media/vendor_covers/jos_cover.jpg",
      "offers_delivery": true,
      "opening_hours": "10:00:00",
      "closing_hours": "22:00:00",
      "product_count": 15,
      "phone": "+2348012345678"
    },
    {
      "id": 1,
      "business_name": "Jollof Kitchen Lagos",
      "category": "Nigerian Restaurant",
      "address": "123 Main Street, Lagos",
      "service_areas": "Lekki, Victoria Island, Ikoyi",
      "description": "Authentic Nigerian Jollof rice and local dishes",
      "logo": "http://localhost:8000/media/vendor_logos/jollof.jpg",
      "cover_image": null,
      "offers_delivery": true,
      "opening_hours": "09:00:00",
      "closing_hours": "21:00:00",
      "product_count": 25,
      "phone": "+2348098765432"
    }
  ]
}
```

#### Search Features
- **Exact Match**: Highest priority (e.g., "Jollof" matches "Jollof Kitchen")
- **Starts With**: High priority (e.g., "Jo" matches "Jos Suya")
- **Contains**: Medium priority (e.g., "Kit" matches "Jollof Kitchen")
- **Description Search**: Searches in business description
- **Category Search**: Searches in business category
- **Service Area Search**: Searches in service areas

#### Ranking Algorithm
1. Exact name match (score: 100)
2. Name starts with query (score: 50)
3. Product count (more products = higher rank)
4. Alphabetical order

---

### 2. Simple Suggestions (Lightweight)
**`GET /api/user/vendors/suggestions/`**

Lightweight endpoint for autocomplete dropdowns - returns only vendor names.

#### Parameters
- `q` (required): Search query (minimum 2 characters)
- `limit` (optional): Maximum suggestions (default: 5, max: 20)

#### Example Request
```bash
GET /api/user/vendors/suggestions/?q=ma&limit=5
```

#### Example Response
```json
{
  "success": true,
  "query": "ma",
  "suggestions": [
    "Mama Nkechi Kitchen",
    "Marina Seafood Restaurant",
    "Mama Put Joint"
  ]
}
```

#### Use Case
Perfect for autocomplete dropdowns where you only need the vendor names, not full details.

---

### 3. Search by Cuisine
**`GET /api/user/vendors/by-cuisine/`**

Find vendors by cuisine type or food category.

#### Parameters
- `cuisine` (required): Cuisine type (e.g., "Nigerian", "Continental", "Chinese")
- `limit` (optional): Maximum results (default: 10, max: 50)

#### Example Request
```bash
GET /api/user/vendors/by-cuisine/?cuisine=Nigerian&limit=10
```

#### Example Response
```json
{
  "success": true,
  "cuisine": "Nigerian",
  "count": 2,
  "results": [
    {
      "id": 1,
      "business_name": "Jollof Kitchen Lagos",
      "category": "Nigerian Restaurant",
      "address": "123 Main Street, Lagos",
      "logo": "http://localhost:8000/media/vendor_logos/jollof.jpg",
      "offers_delivery": true,
      "product_count": 25
    },
    {
      "id": 3,
      "business_name": "Mama Nkechi Kitchen",
      "category": "Nigerian Restaurant",
      "address": "789 Home Road, Port Harcourt",
      "logo": "http://localhost:8000/media/vendor_logos/mama.jpg",
      "offers_delivery": true,
      "product_count": 18
    }
  ]
}
```

#### Search Scope
Searches in:
- Business category
- Business description  
- Product names
- Product descriptions

---

## Error Responses

### Missing Query Parameter
```json
{
  "success": false,
  "error": "Search query is required (parameter: q)"
}
```
**Status Code**: 400

### Query Too Short
```json
{
  "success": false,
  "error": "Search query must be at least 2 characters"
}
```
**Status Code**: 400

### Server Error
```json
{
  "success": false,
  "error": "An error occurred while searching",
  "details": "Detailed error message (only for staff users)"
}
```
**Status Code**: 500

---

## Frontend Integration Examples

### React/Next.js Autocomplete

```typescript
import { useState, useEffect } from 'react';
import debounce from 'lodash/debounce';

function VendorAutocomplete() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  // Debounced search function
  const searchVendors = debounce(async (searchQuery) => {
    if (searchQuery.length < 2) {
      setResults([]);
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `/api/user/vendors/autocomplete/?q=${encodeURIComponent(searchQuery)}&limit=10`
      );
      const data = await response.json();
      
      if (data.success) {
        setResults(data.results);
      }
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  }, 300); // 300ms debounce

  useEffect(() => {
    searchVendors(query);
  }, [query]);

  return (
    <div className="autocomplete">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search restaurants..."
      />
      
      {loading && <div>Loading...</div>}
      
      {results.length > 0 && (
        <ul className="results">
          {results.map((vendor) => (
            <li key={vendor.id}>
              {vendor.logo && <img src={vendor.logo} alt={vendor.business_name} />}
              <div>
                <h4>{vendor.business_name}</h4>
                <p>{vendor.category} • {vendor.product_count} items</p>
                <p>{vendor.address}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

### Simple Dropdown (Lightweight)

```javascript
async function getSuggestions(query) {
  const response = await fetch(
    `/api/user/vendors/suggestions/?q=${encodeURIComponent(query)}&limit=5`
  );
  const data = await response.json();
  return data.suggestions || [];
}

// Usage in autocomplete
const suggestions = await getSuggestions('jo');
// Returns: ["Jos Suya Spot", "Jollof Kitchen Lagos", ...]
```

### Filter by Location

```javascript
async function searchByLocation(query, location) {
  const params = new URLSearchParams({
    q: query,
    location: location,
    limit: 20
  });
  
  const response = await fetch(`/api/user/vendors/autocomplete/?${params}`);
  const data = await response.json();
  return data.results;
}

// Usage
const lagosVendors = await searchByLocation('food', 'Lagos');
```

---

## Performance Optimizations

### Database Indexes
The following indexes are automatically created for optimal performance:
- `business_name` (for name searches)
- `business_category` (for category filtering)
- `verification_status` (for filtering approved vendors)
- `is_suspended` (for filtering active vendors)

### Query Optimization
- Uses `select_related()` for related fields
- Limits results to prevent large responses
- Only queries approved, non-suspended vendors
- Uses `distinct()` to prevent duplicates

### Caching Recommendations
For production, consider caching:
- Popular search queries (e.g., "jollof", "suya")
- Vendor suggestions
- Cuisine-based results

```python
# Example with Django cache
from django.core.cache import cache

def get_cached_suggestions(query):
    cache_key = f'vendor_suggestions:{query.lower()}'
    cached = cache.get(cache_key)
    
    if cached:
        return cached
    
    # Fetch from database
    suggestions = get_suggestions_from_db(query)
    cache.set(cache_key, suggestions, timeout=3600)  # 1 hour
    return suggestions
```

---

## Testing

Test script: `test_vendor_autocomplete_with_data.py`

### Run Tests
```bash
python test_vendor_autocomplete_with_data.py
```

### Test Results
```
✅ Searching for 'jo': 3 results
✅ Searching for 'jollof': 1 result (exact match)
✅ Getting suggestions for 'ma': 1 suggestion
✅ Searching with location 'Lagos': 2 results
```

---

## API Permissions
- **Authentication**: Not required (public endpoint)
- **Rate Limiting**: Consider implementing rate limiting in production
- **CORS**: Ensure CORS is configured for your frontend domains

---

## Next Steps / Future Enhancements

1. **Add ratings**: Include average vendor ratings in results
2. **Distance-based sorting**: Sort by proximity to user location
3. **Popular searches**: Track and highlight trending searches
4. **Image optimization**: Use CDN for vendor images
5. **Fuzzy matching**: Handle typos and misspellings
6. **Voice search**: Add support for voice input
7. **Recent searches**: Save user's recent searches
8. **Favorites**: Mark and filter favorite vendors

---

## Summary

✅ Three endpoints for different use cases  
✅ Smart ranking (exact match > starts with > contains)  
✅ Multiple search fields (name, category, description)  
✅ Location and category filtering  
✅ Optimized queries with indexes  
✅ Public access (no authentication required)  
✅ Clean, consistent JSON responses  
✅ Comprehensive error handling  

**Ready for production use! 🚀**
