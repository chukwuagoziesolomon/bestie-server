**Variant-enabled Vendor Menu Endpoint & Order Summary

Overview
- This document describes the vendor menu creation endpoint that accepts product variants/options with price modifiers, and the order-summary response which includes variant modifier pricing.

**Create Menu Item (Vendor)**
- Endpoint: POST /api/user/vendors/menu/
- Description: Create a new product/menu item and optionally create variant groups and option entries in the same request.

Request JSON example:
{
  "name": "Jollof Rice (Large)",
  "description": "Spicy Nigerian jollof rice",
  "price": 1200.00,
  "category": 3,
  "is_available": true,
  "variants": [
    {
      "name": "Size",
      "required": true,
      "min_select": 1,
      "max_select": 1,
      "sort_order": 1,
      "options": [
        { "name": "Small", "price_modifier": 0.00, "is_available": true, "sort_order": 1 },
        { "name": "Medium", "price_modifier": 200.00, "is_available": true, "sort_order": 2 },
        { "name": "Large", "price_modifier": 400.00, "is_available": true, "sort_order": 3 }
      ]
    },
    {
      "name": "Extras",
      "required": false,
      "min_select": 0,
      "max_select": 5,
      "sort_order": 2,
      "options": [
        { "name": "Extra Chicken", "price_modifier": 350.00, "is_available": true, "sort_order": 1 },
        { "name": "Fried Plantain", "price_modifier": 150.00, "is_available": true, "sort_order": 2 }
      ]
    }
  ]
}

Success Response example (201 Created):
{
  "id": 45,
  "name": "Jollof Rice (Large)",
  "price": "1200.00",
  "variants": [
    {
      "id": 10,
      "name": "Size",
      "required": true,
      "min_select": 1,
      "max_select": 1,
      "options": [
        { "id": 101, "name": "Small", "price_modifier": "0.00" },
        { "id": 102, "name": "Medium", "price_modifier": "200.00" },
        { "id": 103, "name": "Large", "price_modifier": "400.00" }
      ]
    },
    {
      "id": 11,
      "name": "Extras",
      "required": false,
      "min_select": 0,
      "max_select": 5,
      "options": [
        { "id": 111, "name": "Extra Chicken", "price_modifier": "350.00" },
        { "id": 112, "name": "Fried Plantain", "price_modifier": "150.00" }
      ]
    }
  ]
}

Notes about the menu endpoint
- `variants` is optional. When present, the server creates `ProductVariant` rows and `ProductVariantOption` rows linked to the created product.
- Options include `price_modifier` which is added to the product base price when selected.
- Current implementation matches variant/option selections by name (case-insensitive). Using option IDs to select options is recommended for future robustness.

**Order Summary (Cart) including Variant Pricing**
- Endpoint: POST /api/user/order-summary/
- Description: Calculates subtotal, delivery and totals for a cart; includes variant pricing per-item.

Request JSON example:
{
  "cart_items": [
    {
      "product_id": 45,
      "quantity": 2,
      "variants": { "Size": "Large", "Extras": ["Fried Plantain"] }
    }
  ],
  "delivery_address_id": 7
}

Response JSON example:
{
  "items": [
    {
      "product_id": 45,
      "name": "Jollof Rice (Large)",
      "quantity": 2,
      "base_price": "1200.00",
      "variants": { "Size": "Large", "Extras": ["Fried Plantain"] },
      "variant_modifier_per_unit": "550.00",
      "unit_price_including_modifiers": "1750.00",
      "total": "3500.00"
    }
  ],
  "subtotal": "3500.00",
  "delivery_fee": "200.00",
  "total": "3700.00"
}

Notes about order-summary behavior
- For each cart item the backend calculates the variant modifier total by looking up each selected option's `price_modifier` and summing them.
- `variant_modifier_per_unit` is the sum of modifiers for a single unit. `unit_price_including_modifiers` = `base_price` + `variant_modifier_per_unit`.
- `total` for the item = `unit_price_including_modifiers` * `quantity`.
- The cart item `variants` are stored in the `CartItem.variants` JSONField as the selections provided by the frontend (name-to-selection mapping).

Caveats & Recommended Next Steps
- Persisting variant selections to orders: currently `OrderItem` does not include a `variants` JSONField. Add a `variants` field and copy `CartItem.variants` into `OrderItem` at order placement for full auditability.
- Use option IDs instead of names when sending selections from the frontend to avoid fragile matching.
- Add nested DRF serializers and validation to enforce `required`, `min_select`, and `max_select` rules when creating products and when accepting cart selections.
- Run migrations after pulling the code changes (`python manage.py makemigrations` and `python manage.py migrate`).

Examples Recap
- Create product with variants: POST /api/user/vendors/menu/ (see request example above).
- Calculate order summary: POST /api/user/order-summary/ (see request/response examples above).
