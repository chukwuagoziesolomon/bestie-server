# 📊 Stock Reservation System - Visual Flow

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        STOCK MANAGEMENT LAYERS                       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                     PRODUCT INVENTORY                      │    │
│  │                                                            │    │
│  │  ┌─────────────────────────────────────────────────┐      │    │
│  │  │          Total Stock: 100 units                 │      │    │
│  │  │                                                 │      │    │
│  │  │  ┌──────────────────┐  ┌───────────────────┐  │      │    │
│  │  │  │   Available: 75  │  │  Reserved: 25     │  │      │    │
│  │  │  │  (Can be sold)   │  │  (Pending orders) │  │      │    │
│  │  │  └──────────────────┘  └───────────────────┘  │      │    │
│  │  │                                                 │      │    │
│  │  └─────────────────────────────────────────────────┘      │    │
│  │                                                            │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Order Lifecycle with Stock Management

```
                    Customer Journey
                    ===============

┌─────────────────┐
│  Browse Products │
│  Check Prices   │
└────────┬────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  ADD TO CART                           │
│  ✓ Validate: available_stock >= qty   │
│  ✓ Create WebsiteCartItem              │
│  ✗ NO stock change                     │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  PLACE ORDER                           │
│  ✓ Validate: available_stock >= qty   │
│  ✓ Create Order (status='pending')    │
│  ✓ Create OrderItems                  │
│  ✗ NO stock change                     │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  CONFIRM PAYMENT                       │
│  ✓ payment_confirmed = True            │
│  ✓ CREATE STOCK RESERVATION (signal)  │
│     → Status: 'reserved'               │
│     → Available stock ↓ (decreased)    │
│     → Total stock → (unchanged)        │
└────────┬───────────────────────────────┘
         │
         ├──────────────────┬─────────────────────┐
         │                  │                     │
         ▼                  ▼                     ▼
┌──────────────────┐ ┌─────────────────┐ ┌──────────────────┐
│  ORDER DELIVERED │ │ ORDER CANCELLED │ │ ORDER IN TRANSIT │
│  status=         │ │ status=         │ │ status=          │
│  'delivered'     │ │ 'cancelled'     │ │ 'out_for_delivery│
└────────┬─────────┘ └────────┬────────┘ └──────────────────┘
         │                    │
         │                    │
         ▼                    ▼
┌──────────────────┐ ┌────────────────────┐
│ FULFILL          │ │ RELEASE            │
│ RESERVATION      │ │ RESERVATION        │
│ (signal)         │ │ (signal)           │
│                  │ │                    │
│ ✓ Deduct stock   │ │ ✓ Mark 'released'  │
│   total_stock ↓  │ │ ✓ Available ↑      │
│ ✓ Mark           │ │   (stock returned) │
│   'fulfilled'    │ │ ✗ Total unchanged  │
│ ✓ vendor_paid    │ │ ✗ No revenue       │
│   = True         │ │                    │
│ ✓ courier_paid   │ │                    │
│   = True         │ │                    │
└──────────────────┘ └────────────────────┘
```

## Database Schema Relationships

```
┌──────────────────┐       ┌──────────────────────┐
│     Product      │       │        Order         │
├──────────────────┤       ├──────────────────────┤
│ id               │◄──┐   │ id                   │◄─┐
│ name             │   │   │ order_number         │  │
│ price            │   │   │ status               │  │
│ stock_quantity   │   │   │ payment_confirmed    │  │
│ is_available     │   │   │ vendor_paid          │  │
└──────────────────┘   │   │ courier_paid         │  │
                       │   │ delivered_at         │  │
                       │   └──────────────────────┘  │
                       │                             │
                       │   ┌──────────────────────┐  │
                       │   │     OrderItem        │  │
                       │   ├──────────────────────┤  │
                       └───┤ product_id (FK)      │  │
                           ├──────────────────────┤  │
                           │ order_id (FK)        ├──┘
                           │ quantity             │
                           │ price                │
                           └──────────────────────┘
                                     │
                                     │
                       ┌─────────────┴─────────────────┐
                       │                               │
                       ▼                               ▼
         ┌──────────────────────────┐   ┌──────────────────────────┐
         │ OrderStockReservation    │   │  WebsiteCartItem         │
         ├──────────────────────────┤   ├──────────────────────────┤
         │ order_id (FK)            │   │ product_id (FK)          │
         │ product_id (FK)          │   │ anonymous_cart_id (FK)   │
         │ quantity                 │   │ user_id (FK)             │
         │ status                   │   │ quantity                 │
         │   'reserved'             │   │ price_snapshot           │
         │   'fulfilled'            │   └──────────────────────────┘
         │   'released'             │
         │ reserved_at              │
         │ fulfilled_at             │
         │ released_at              │
         └──────────────────────────┘
```

## Stock Calculation Example

```
Initial State:
┌─────────────────────────────────────────┐
│ Product: Jollof Rice                    │
│ Total Stock: 100                        │
│ Reserved: 0                             │
│ Available: 100                          │
└─────────────────────────────────────────┘

Customer A adds 10 to cart:
┌─────────────────────────────────────────┐
│ ✓ Check: available (100) >= 10          │
│ ✓ Cart updated                          │
│ Stock: 100 | Reserved: 0 | Available: 100 │
└─────────────────────────────────────────┘

Customer A places order & pays:
┌─────────────────────────────────────────┐
│ ✓ Order created                         │
│ ✓ Payment confirmed                     │
│ ✓ Reservation created (10 units)       │
│ Stock: 100 | Reserved: 10 | Available: 90 │
└─────────────────────────────────────────┘

Customer B adds 15 to cart:
┌─────────────────────────────────────────┐
│ ✓ Check: available (90) >= 15           │
│ ✓ Cart updated                          │
│ Stock: 100 | Reserved: 10 | Available: 90 │
└─────────────────────────────────────────┘

Customer B places order & pays:
┌─────────────────────────────────────────┐
│ ✓ Order created                         │
│ ✓ Payment confirmed                     │
│ ✓ Reservation created (15 units)       │
│ Stock: 100 | Reserved: 25 | Available: 75 │
└─────────────────────────────────────────┘

Customer A's order delivered:
┌─────────────────────────────────────────┐
│ ✓ Status = 'delivered'                  │
│ ✓ Stock deducted (100 - 10 = 90)       │
│ ✓ Reservation fulfilled                 │
│ ✓ Vendor/courier paid                   │
│ Stock: 90 | Reserved: 15 | Available: 75  │
└─────────────────────────────────────────┘

Customer B cancels order:
┌─────────────────────────────────────────┐
│ ✓ Status = 'cancelled'                  │
│ ✓ Reservation released                  │
│ Stock: 90 | Reserved: 0 | Available: 90   │
└─────────────────────────────────────────┘
```

## Signal Flow Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    Order.save()                          │
└─────────────────────────┬────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │  pre_save signal triggered     │
         │  handle_order_updates()        │
         └────────┬───────────────────────┘
                  │
                  ├──── payment_confirmed changed? ────────┐
                  │                                         │
                  │                                         ▼
                  │                        ┌────────────────────────────┐
                  │                        │ create_stock_reservations  │
                  │                        │ - Validate available stock │
                  │                        │ - Create reservations      │
                  │                        │ - Status: 'reserved'       │
                  │                        └────────────────────────────┘
                  │
                  ├──── status = 'delivered'? ─────────────┐
                  │                                         │
                  │                                         ▼
                  │                        ┌────────────────────────────┐
                  │                        │ fulfill_stock_reservations │
                  │                        │ - Deduct product.stock     │
                  │                        │ - Status: 'fulfilled'      │
                  │                        │ - vendor_paid = True       │
                  │                        │ - courier_paid = True      │
                  │                        └────────────────────────────┘
                  │
                  └──── status = 'cancelled'? ────────────┐
                                                           │
                                                           ▼
                                          ┌────────────────────────────┐
                                          │ release_stock_reservations │
                                          │ - Status: 'released'       │
                                          │ - Available stock ↑        │
                                          └────────────────────────────┘
```

## Error Handling Flow

```
Customer tries to add item to cart
            │
            ▼
    ┌───────────────┐
    │ get_available │
    │    _stock()   │
    └───────┬───────┘
            │
            ▼
   ┌────────────────────┐      Yes      ┌──────────────┐
   │ available >= qty ? ├──────────────►│ Add to cart  │
   └────────┬───────────┘               └──────────────┘
            │
            │ No
            ▼
   ┌────────────────────────────────────┐
   │ Raise ValueError                   │
   │ "Only X available                  │
   │  (some reserved for pending)"      │
   └────────────────────────────────────┘
```

## Monitoring Dashboard (Conceptual)

```
┌──────────────────────────────────────────────────────────┐
│              STOCK INVENTORY DASHBOARD                   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Product: Jollof Rice                                    │
│  ┌────────────────────────────────────────────────┐     │
│  │ Total Stock:     [████████████] 100            │     │
│  │ Reserved:        [████░░░░░░░░] 25             │     │
│  │ Available:       [██████████░░] 75             │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
│  Active Reservations: 3 orders                          │
│  ┌────────────────────────────────────────────────┐     │
│  │ Order #00059 | 10 units | Reserved 5 min ago  │     │
│  │ Order #00060 |  8 units | Reserved 15 min ago │     │
│  │ Order #00061 |  7 units | Reserved 1 hr ago   │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
│  Recent Activity:                                        │
│  ┌────────────────────────────────────────────────┐     │
│  │ ✓ Order #00058 delivered | 5 units deducted   │     │
│  │ ✓ Order #00057 cancelled | 3 units released   │     │
│  │ ✓ Order #00056 delivered | 12 units deducted  │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## Summary: Three Stock States

```
┌───────────────────────────────────────────────────┐
│                 STOCK STATES                      │
├───────────────────────────────────────────────────┤
│                                                   │
│  1️⃣  TOTAL STOCK (product.stock_quantity)        │
│     → Physical inventory count                   │
│     → Only decreases on delivery                 │
│     → Persisted in database                      │
│                                                   │
│  2️⃣  RESERVED STOCK (OrderStockReservation)      │
│     → Held for pending paid orders               │
│     → Can be released if order cancelled         │
│     → Tracked per order                          │
│                                                   │
│  3️⃣  AVAILABLE STOCK (calculated)                │
│     → total_stock - reserved_stock               │
│     → What customers can actually buy            │
│     → Validated on cart add & order place        │
│                                                   │
└───────────────────────────────────────────────────┘

Formula: AVAILABLE = TOTAL - RESERVED
```
