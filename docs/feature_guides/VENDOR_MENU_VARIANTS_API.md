# Vendor Menu Variants API

## 📋 Overview

Vendors can now create and manage menu items with customizable variants (sizes, extras, add-ons, substitutes). The system only displays variants in the frontend if the vendor has actually configured them.

## 🚀 API Endpoints

### **1. Create Menu Item with Variants**
**POST** `/api/user/vendors/menu/`

**Request Body:**
```json
{
  "dish_name": "Classic Beef Burger",
  "item_description": "Juicy beef patty with lettuce, tomato, onion",
  "price": "2500.00",
  "category": "Main Course",
  "available_now": true,
  "quantity": 50,
  "variants": [
    {
      "name": "Small",
      "type": "size",
      "price_modifier": -500,
      "is_required": false,
      "is_available": true,
      "sort_order": 1
    },
    {
      "name": "Regular",
      "type": "size",
      "price_modifier": 0,
      "is_required": false,
      "is_available": true,
      "sort_order": 2
    },
    {
      "name": "Large",
      "type": "size",
      "price_modifier": 2000,
      "is_required": false,
      "is_available": true,
      "sort_order": 3
    },
    {
      "name": "Extra Cheese",
      "type": "extra",
      "price_modifier": 200,
      "is_required": false,
      "is_available": true,
      "sort_order": 1
    },
    {
      "name": "Extra Bacon",
      "type": "extra",
      "price_modifier": 300,
      "is_required": false,
      "is_available": true,
      "sort_order": 2
    },
    {
      "name": "Extra Chips",
      "type": "addon",
      "price_modifier": 500,
      "is_required": false,
      "is_available": true,
      "sort_order": 1
    }
  ]
}
```

**Response:**
```json
{
  "id": 101,
  "dish_name": "Classic Beef Burger",
  "item_description": "Juicy beef patty with lettuce, tomato, onion",
  "price": 2500,
  "category": "Burgers",
  "available_now": true,
  "quantity": 50,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### **2. Update Menu Item with Variants**
**PUT** `/api/user/vendors/menu/{item_id}/`

**Request Body:** (Same as create, but all fields optional)

### **3. Get Menu Item Customization Options**
**GET** `/api/user/menu-items/{item_id}/customize/`

**Response:**
```json
{
  "success": true,
  "menu_item": {
    "id": 101,
    "name": "Classic Beef Burger",
    "description": "Juicy beef patty with lettuce, tomato, onion",
    "base_price": 2500,
    "currency": "NGN",
    "image": "https://res.cloudinary.com/.../burger.jpg",
    "preparation_time": 15,
    "ingredients": ["Beef Patty", "Lettuce", "Tomato", "Onion"],
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
        "price_modifier": 200,
        "is_required": false,
        "formatted_price": "+₦200"
      },
      {
        "id": 5,
        "name": "Extra Bacon",
        "type": "extra",
        "price_modifier": 300,
        "is_required": false,
        "formatted_price": "+₦300"
      }
    ],
    "addon": [
      {
        "id": 6,
        "name": "Extra Chips",
        "type": "addon",
        "price_modifier": 500,
        "is_required": false,
        "formatted_price": "+₦500"
      }
    ]
  },
  "customization_summary": {
    "has_sizes": true,
    "has_extras": true,
    "has_addons": true,
    "has_substitutes": false,
    "total_variants": 6,
    "required_variants": 0
  }
}
```

## 📋 Menu Item Fields

### **Required Fields:**
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `dish_name` | string | Name of the dish | "Classic Beef Burger" |
| `item_description` | string | Description of the menu item | "Juicy beef patty with lettuce, tomato, onion" |
| `price` | string | Price as string | "2500.00" |
| `category` | string | Category of the item | "Main Course", "Appetizer", "Drinks", "Dessert" |

### **Optional Fields:**
| Field | Type | Default | Description | Example |
|-------|------|---------|-------------|---------|
| `image` | File | null | Image file upload | (multipart/form-data) |
| `available_now` | boolean | true | Whether item is currently available | true, false |
| `quantity` | number | 0 | Stock quantity | 50 |
| `variants` | array | [] | List of variants for customization | See variants section |

### **Category Examples:**
- **Main Course**: Burgers, Pizzas, Pasta, Rice dishes
- **Appetizer**: Salads, Soups, Starters, Snacks  
- **Drinks**: Juices, Soft drinks, Coffee, Tea
- **Dessert**: Cakes, Ice cream, Pastries, Sweets

## 📝 Variant Types

### **1. Size**
- Different portion sizes
- Examples: Small, Regular, Large, Extra Large
- Can have positive or negative price modifiers

### **2. Extra**
- Additional toppings or ingredients
- Examples: Extra Cheese, Extra Bacon, Extra Sauce
- Usually positive price modifiers

### **3. Add-on**
- Additional items that come with the main dish
- Examples: Extra Chips, Side Salad, Extra Drink
- Usually positive price modifiers

### **4. Substitute**
- Alternative ingredients
- Examples: Gluten-free bun, Vegan cheese, Sugar-free
- Can have positive or negative price modifiers

## 🔧 Variant Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string | Yes | Display name (e.g., "Large", "Extra Cheese") |
| `type` | string | Yes | One of: size, extra, addon, substitute |
| `price_modifier` | number | Yes | Additional cost (+₦500) or discount (-₦200) |
| `is_required` | boolean | No | Must customer select this? (default: false) |
| `is_available` | boolean | No | Is this variant currently available? (default: true) |
| `sort_order` | number | No | Display order (default: 0) |

## 🎯 Frontend Implementation

### **Vendor Dashboard - Menu Management**

```javascript
// Create menu item with variants
const createMenuItem = async (menuData) => {
  // Handle file upload if image is provided
  const formData = new FormData();
  
  // Required fields
  formData.append('dish_name', menuData.dish_name);
  formData.append('item_description', menuData.item_description);
  formData.append('price', menuData.price); // String format: "2500.00"
  formData.append('category', menuData.category);
  
  // Optional fields
  if (menuData.image) {
    formData.append('image', menuData.image);
  }
  if (menuData.available_now !== undefined) {
    formData.append('available_now', menuData.available_now);
  }
  if (menuData.quantity !== undefined) {
    formData.append('quantity', menuData.quantity);
  }
  if (menuData.variants) {
    formData.append('variants', JSON.stringify(menuData.variants));
  }
  
  const response = await fetch('/api/user/vendors/menu/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${vendorToken}`
      // Don't set Content-Type for FormData, let browser set it with boundary
    },
    body: formData
  });
  
  return response.json();
};

// Complete example with all fields
const exampleMenuData = {
  // Required fields
  dish_name: "Deluxe Pizza",
  item_description: "A delicious pizza with premium toppings and fresh ingredients",
  price: "3500.00", // String format
  category: "Main Course",
  
  // Optional fields
  image: selectedImageFile, // File object from input
  available_now: true,
  quantity: 25,
  
  // Variants array
  variants: [
    {
      name: "Small",
      type: "size",
      price_modifier: -1000,
      is_required: false,
      is_available: true,
      sort_order: 1
    },
    {
      name: "Medium", 
      type: "size",
      price_modifier: 0,
      is_required: false,
      is_available: true,
      sort_order: 2
    },
    {
      name: "Large",
      type: "size", 
      price_modifier: 1500,
      is_required: false,
      is_available: true,
      sort_order: 3
    },
    {
      name: "Extra Cheese",
      type: "extra",
      price_modifier: 300,
      is_required: false,
      is_available: true,
      sort_order: 1
    }
  ]
};

// Example variant configuration
const menuVariants = [
  // Size variants
  {
    name: "Small",
    type: "size",
    price_modifier: -500,
    is_required: false,
    is_available: true,
    sort_order: 1
  },
  {
    name: "Regular",
    type: "size",
    price_modifier: 0,
    is_required: false,
    is_available: true,
    sort_order: 2
  },
  {
    name: "Large",
    type: "size",
    price_modifier: 2000,
    is_required: false,
    is_available: true,
    sort_order: 3
  },
  
  // Extra variants
  {
    name: "Extra Cheese",
    type: "extra",
    price_modifier: 200,
    is_required: false,
    is_available: true,
    sort_order: 1
  },
  {
    name: "Extra Bacon",
    type: "extra",
    price_modifier: 300,
    is_required: false,
    is_available: true,
    sort_order: 2
  },
  
  // Add-on variants
  {
    name: "Extra Chips",
    type: "addon",
    price_modifier: 500,
    is_required: false,
    is_available: true,
    sort_order: 1
  }
];
```

### **Customer Frontend - Customization Modal**

```javascript
// Get customization options
const getCustomizationOptions = async (itemId) => {
  const response = await fetch(`/api/user/menu-items/${itemId}/customize/`);
  const data = await response.json();
  
  if (data.success) {
    // Only show variants if they exist
    if (data.variants && Object.keys(data.variants).length > 0) {
      showCustomizationModal(data);
    } else {
      // No variants, add directly to cart
      addToCartDirectly(itemId);
    }
  }
};

// Display customization modal
const showCustomizationModal = (customizationData) => {
  const { menu_item, variants, customization_summary } = customizationData;
  
  // Build UI based on available variants
  let modalContent = `
    <div class="customization-modal">
      <h3>${menu_item.name}</h3>
      <p>${menu_item.description}</p>
      <p class="base-price">Base Price: ₦${menu_item.base_price.toLocaleString()}</p>
  `;
  
  // Show size options if available
  if (variants.size && variants.size.length > 0) {
    modalContent += `
      <div class="variant-section">
        <h4>Size</h4>
        ${variants.size.map(size => `
          <label>
            <input type="radio" name="size" value="${size.id}" data-price="${size.price_modifier}">
            ${size.name} (${size.formatted_price})
          </label>
        `).join('')}
      </div>
    `;
  }
  
  // Show extras if available
  if (variants.extra && variants.extra.length > 0) {
    modalContent += `
      <div class="variant-section">
        <h4>Extras</h4>
        ${variants.extra.map(extra => `
          <label>
            <input type="checkbox" name="extras" value="${extra.id}" data-price="${extra.price_modifier}">
            ${extra.name} (${extra.formatted_price})
          </label>
        `).join('')}
      </div>
    `;
  }
  
  // Show add-ons if available
  if (variants.addon && variants.addon.length > 0) {
    modalContent += `
      <div class="variant-section">
        <h4>Add-ons</h4>
        ${variants.addon.map(addon => `
          <label>
            <input type="checkbox" name="addons" value="${addon.id}" data-price="${addon.price_modifier}">
            ${addon.name} (${addon.formatted_price})
          </label>
        `).join('')}
      </div>
    `;
  }
  
  modalContent += `
      <div class="variant-section">
        <h4>Special Instructions</h4>
        <textarea name="special_instructions" placeholder="Any special requests? (Optional)"></textarea>
      </div>
      
      <div class="price-summary">
        <p>Total: ₦<span id="total-price">${menu_item.base_price.toLocaleString()}</span></p>
      </div>
      
      <button onclick="addToCartWithCustomizations()">Add to Cart</button>
    </div>
  `;
  
  document.getElementById('modal-content').innerHTML = modalContent;
  showModal();
};
```

## 🎨 UI/UX Guidelines

### **For Vendors:**
1. **Variant Management**: Provide easy-to-use forms for adding variants
2. **Preview**: Show how variants will appear to customers
3. **Bulk Actions**: Allow enabling/disabling all variants at once
4. **Pricing Helper**: Calculate total prices with variants

### **For Customers:**
1. **Conditional Display**: Only show customization modal if variants exist
2. **Clear Pricing**: Show base price + variant prices clearly
3. **Required Indicators**: Mark required variants clearly
4. **Price Calculator**: Update total price in real-time

## 📊 Key Features

✅ **Optional Variants**: Only display if vendor configured them  
✅ **Multiple Types**: Size, Extra, Add-on, Substitute support  
✅ **Flexible Pricing**: Positive/negative price modifiers  
✅ **Availability Control**: Enable/disable variants individually  
✅ **Sorting**: Control display order of variants  
✅ **Required Options**: Force customer selection if needed  
✅ **Real-time Updates**: Instant price calculation  
✅ **Backward Compatible**: Works with existing menu items  

## 🔄 Workflow

1. **Vendor creates menu item** → Can optionally add variants
2. **Customer views menu** → Sees item with/without customization options
3. **Customer clicks item** → Customization modal appears (if variants exist)
4. **Customer customizes** → Selects size, extras, add-ons, etc.
5. **Customer adds to cart** → Item saved with selected variants
6. **Order placement** → Vendor receives detailed customization info

This system ensures that vendors have full control over their menu offerings while providing customers with flexible customization options! 🎉
