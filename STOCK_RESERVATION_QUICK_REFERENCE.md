# 🔧 Stock Reservation System - Quick Reference

## For Developers

### Check Available Stock
```python
from bestyy.core_features.user.cart_utils import get_available_stock

product = Product.objects.get(id=5)
available = get_available_stock(product)
# Returns: total_stock - reserved_stock
```

### Add to Cart (Automatic Stock Validation)
```python
from bestyy.core_features.user.cart_utils import add_to_cart

try:
    cart_token, cart_item, created = add_to_cart(
        product_id=5,
        quantity=3,
        cart_token=request.data.get('cart_token'),
        user=request.user if request.user.is_authenticated else None
    )
except ValueError as e:
    # Handle stock insufficient error
    # e.g., "Only 2 items available in stock (some items are reserved)"
    pass
```

### Create Order (Automatic Reservation on Payment)
```python
# Step 1: Create order
order = Order.objects.create(
    customer=user,
    vendor=vendor,
    total_amount=Decimal('5000.00'),
    status='pending'
)

# Step 2: Add items
OrderItem.objects.create(
    order=order,
    product=product,
    quantity=3,
    price=product.price
)

# Step 3: Confirm payment
# This AUTOMATICALLY creates stock reservations via signal
order.payment_confirmed = True
order.payment_confirmed_at = timezone.now()
order.save()
# → Stock reservations created automatically!
```

### Mark Order as Delivered
```python
# This AUTOMATICALLY fulfills reservations and tracks revenue via signal
order.status = 'delivered'
order.save()
# → Stock deducted, vendor_paid=True, courier_paid=True
```

### Cancel Order
```python
# This AUTOMATICALLY releases stock reservations via signal
order.status = 'cancelled'
order.save()
# → Stock reservations released
```

### Manual Stock Management (Advanced)

#### Create Reservations Manually
```python
from bestyy.core_features.user.cart_utils import create_stock_reservations_for_order

try:
    reservations = create_stock_reservations_for_order(order)
    # Returns list of OrderStockReservation instances
except ValueError as e:
    # Handle insufficient stock
    pass
```

#### Fulfill Reservations Manually
```python
from bestyy.core_features.user.cart_utils import fulfill_stock_reservations

result = fulfill_stock_reservations(order)
# Returns: {
#   'fulfilled': 2,
#   'failed': 0,
#   'failed_items': []
# }
```

#### Release Reservations Manually
```python
from bestyy.core_features.user.cart_utils import release_stock_reservations

released_count = release_stock_reservations(order)
# Returns: number of reservations released
```

### Query Reservations
```python
from bestyy.restaurant_features.order.models import OrderStockReservation

# Get all reserved stock for a product
reserved_qty = OrderStockReservation.objects.filter(
    product=product,
    status='reserved'
).aggregate(total=Sum('quantity'))['total'] or 0

# Get all reservations for an order
reservations = OrderStockReservation.objects.filter(order=order)

# Check reservation status
for res in reservations:
    print(f"{res.quantity}x {res.product.name} - {res.status}")
```

## Order Status Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Order Created (status='pending')                            │
│ ✓ Order exists in database                                  │
│ ✗ No stock impact                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Payment Confirmed (payment_confirmed=True)                  │
│ ✓ Stock RESERVED (via signal)                              │
│ ✓ Available stock decreases                                │
│ ✗ Actual stock unchanged                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Order Delivered (status='delivered')                        │
│ ✓ Stock DEDUCTED (via signal)                              │
│ ✓ vendor_paid = True                                        │
│ ✓ courier_paid = True (if courier exists)                  │
│ ✓ Reservations marked as 'fulfilled'                       │
└─────────────────────────────────────────────────────────────┘

Alternative Path:
┌─────────────────────────────────────────────────────────────┐
│ Order Cancelled (status='cancelled')                        │
│ ✓ Stock reservations RELEASED (via signal)                 │
│ ✓ Available stock increases                                │
│ ✗ Actual stock unchanged                                   │
└─────────────────────────────────────────────────────────────┘
```

## Stock Calculation

```python
# Available Stock = Total Stock - Reserved Stock
available_stock = product.stock_quantity - reserved_quantity

# Reserved Stock = Sum of all 'reserved' reservations
reserved_quantity = OrderStockReservation.objects.filter(
    product=product,
    status='reserved'
).aggregate(total=Sum('quantity'))['total'] or 0
```

## Error Handling

### Cart Add Error
```json
{
  "success": false,
  "error": "Only 5 items available in stock (some items are reserved for pending orders)"
}
```

### Order Placement Error
```json
{
  "success": false,
  "error": "Insufficient stock for: Jollof Rice (requested: 10, available: 5)",
  "stock_errors": [
    {
      "product": "Jollof Rice",
      "requested": 10,
      "available": 5
    }
  ]
}
```

## Monitoring

Check logs for stock operations:
```
INFO: Created 3 stock reservations for order ORD-20251120-00059
INFO: Fulfilled 3 stock reservations for order ORD-20251120-00059
INFO: Marked vendor as paid for order ORD-20251120-00059
INFO: Marked courier as paid for order ORD-20251120-00059
INFO: Released 2 stock reservations for cancelled order ORD-20251120-00060
WARNING: Failed to fulfill 1 items for order ORD-20251120-00061
```

## Database Queries

### View Reserved Stock by Product
```sql
SELECT 
    p.name,
    p.stock_quantity as total_stock,
    COALESCE(SUM(osr.quantity), 0) as reserved_stock,
    p.stock_quantity - COALESCE(SUM(osr.quantity), 0) as available_stock
FROM product_product p
LEFT JOIN order_orderstockreservation osr ON osr.product_id = p.id AND osr.status = 'reserved'
GROUP BY p.id, p.name, p.stock_quantity;
```

### View Order Reservations
```sql
SELECT 
    o.order_number,
    o.status,
    osr.status as reservation_status,
    p.name,
    osr.quantity,
    osr.reserved_at,
    osr.fulfilled_at,
    osr.released_at
FROM order_orderstockreservation osr
JOIN order_order o ON o.id = osr.order_id
JOIN product_product p ON p.id = osr.product_id
ORDER BY osr.reserved_at DESC;
```

## Important Notes

1. **Signals Handle Everything**: Stock management is automatic via Django signals. Just update order fields.

2. **No Manual Stock Deduction**: Never manually decrease `product.stock_quantity` for orders. Let the signal handle it.

3. **Race Conditions**: The system uses database-level operations to prevent race conditions.

4. **Testing**: Always test stock management changes with `test_stock_reservation_system.py`.

5. **Backward Compatible**: Existing code continues to work. Old orders without reservations still function normally.

## Need Help?

- **Documentation**: `STOCK_RESERVATION_IMPLEMENTATION.md`
- **Test Script**: `test_stock_reservation_system.py`
- **Code Location**: `bestyy/core_features/user/cart_utils.py`
- **Signals**: `bestyy/restaurant_features/order/signals.py`
