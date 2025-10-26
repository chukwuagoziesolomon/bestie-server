# Dashboard KPI API Documentation

This document provides comprehensive documentation for the admin dashboard KPI endpoints that power the stat cards and revenue breakdowns.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Dashboard Stats Endpoint](#dashboard-stats-endpoint)
4. [Revenue Breakdown Endpoint](#revenue-breakdown-endpoint)
5. [Response Examples](#response-examples)
6. [Error Handling](#error-handling)
7. [Frontend Integration](#frontend-integration)

## Overview

The Dashboard KPI API provides real-time statistics for the admin dashboard, including:

- **Total Orders**: Count of completed orders with trend analysis
- **Total Revenue**: Revenue totals with percentage changes
- **Pending Verification**: Count of pending vendor/courier verifications
- **Active Couriers**: Count of active, verified couriers
- **Revenue Breakdown**: Detailed revenue analysis by time periods, vendors, status, etc.

## Authentication

All endpoints require:
- Valid JWT authentication token
- User must be a superuser (`is_superuser=True`)

```javascript
// Example authentication header
Authorization: Bearer <your_jwt_token>
```

## Dashboard Stats Endpoint

### GET /api/admin/dashboard/stats/

Returns KPI statistics for the admin dashboard stat cards.

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `period` | string | No | `week` | Time period for comparison. Options: `today`, `week`, `month` |

#### Response Format

```json
{
  "total_orders": {
    "value": 90,
    "trend": "up",
    "change_percentage": 1.3,
    "comparison_text": "Up from past week",
    "icon": "package"
  },
  "total_revenue": {
    "value": 200000.00,
    "formatted_value": "N200,000",
    "trend": "down",
    "change_percentage": 4.3,
    "comparison_text": "Down from yesterday",
    "icon": "trending-up"
  },
  "pending_verification": {
    "value": 10,
    "trend": "up",
    "change_percentage": 1.8,
    "comparison_text": "Up from yesterday",
    "icon": "check-circle"
  },
  "active_couriers": {
    "value": 8,
    "trend": "up",
    "change_percentage": 1.8,
    "comparison_text": "Up from yesterday",
    "icon": "truck"
  }
}
```

#### Field Descriptions

**total_orders**
- `value`: Total number of completed orders in the current period
- `trend`: Direction of change (`up` or `down`)
- `change_percentage`: Percentage change from comparison period
- `comparison_text`: Human-readable comparison description
- `icon`: Suggested icon for UI display

**total_revenue**
- `value`: Raw revenue amount (decimal)
- `formatted_value`: Formatted currency string (e.g., "N200,000")
- `trend`: Direction of change (`up` or `down`)
- `change_percentage`: Percentage change from comparison period
- `comparison_text`: Human-readable comparison description
- `icon`: Suggested icon for UI display

**pending_verification**
- `value`: Total pending verifications (vendors + couriers)
- `trend`: Direction of change (`up` or `down`)
- `change_percentage`: Percentage change from comparison period
- `comparison_text`: Human-readable comparison description
- `icon`: Suggested icon for UI display

**active_couriers**
- `value`: Number of active, verified couriers
- `trend`: Direction of change (`up` or `down`)
- `change_percentage`: Percentage change from comparison period
- `comparison_text`: Human-readable comparison description
- `icon`: Suggested icon for UI display

## Revenue Breakdown Endpoint

### GET /api/admin/revenue/breakdown/

Returns detailed revenue breakdown for specific periods and analysis types.

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `date` | date | No | today | Specific date for breakdown (YYYY-MM-DD) |
| `period` | string | No | `day` | Period type. Options: `day`, `week`, `month` |
| `breakdown_type` | string | No | `hourly` | Type of breakdown. Options: `hourly`, `daily`, `by_vendor`, `by_status`, `by_payment_method` |

#### Response Format

```json
{
  "period": {
    "date": "2025-09-08",
    "period_type": "day",
    "breakdown_type": "hourly"
  },
  "summary": {
    "total_revenue": 25000.00,
    "total_orders": 45,
    "average_order_value": 555.56
  },
  "breakdown": [
    {
      "time": "09:00",
      "revenue": 2500.00,
      "orders": 5,
      "percentage": 10.0
    },
    {
      "time": "10:00",
      "revenue": 3200.00,
      "orders": 7,
      "percentage": 12.8
    }
  ],
  "top_performers": [
    {
      "vendor_id": 1,
      "vendor_name": "Tasty Bites",
      "revenue": 5000.00,
      "orders": 10,
      "percentage": 20.0
    }
  ]
}
```

#### Breakdown Types

**hourly** (for day period)
- Shows revenue breakdown by hour (00:00 to 23:00)
- `time` field contains hour in "HH:00" format

**daily** (for week period)
- Shows revenue breakdown by day of week
- `time` field contains day name (Monday, Tuesday, etc.)

**by_vendor**
- Shows revenue breakdown by vendor
- `time` field contains vendor business name
- Includes vendor_id for linking

**by_status**
- Shows revenue breakdown by order status
- `time` field contains status name (Completed, Pending, etc.)

**by_payment_method**
- Shows revenue breakdown by payment method
- `time` field contains payment method name

## Response Examples

### Dashboard Stats - Today Comparison

```bash
GET /api/admin/dashboard/stats/?period=today
```

```json
{
  "total_orders": {
    "value": 12,
    "trend": "up",
    "change_percentage": 20.0,
    "comparison_text": "Up from yesterday",
    "icon": "package"
  },
  "total_revenue": {
    "value": 45000.00,
    "formatted_value": "N45,000",
    "trend": "down",
    "change_percentage": 5.2,
    "comparison_text": "Down from yesterday",
    "icon": "trending-up"
  },
  "pending_verification": {
    "value": 3,
    "trend": "down",
    "change_percentage": 25.0,
    "comparison_text": "Down from yesterday",
    "icon": "check-circle"
  },
  "active_couriers": {
    "value": 15,
    "trend": "up",
    "change_percentage": 7.1,
    "comparison_text": "Up from yesterday",
    "icon": "truck"
  }
}
```

### Revenue Breakdown - Hourly

```bash
GET /api/admin/revenue/breakdown/?date=2025-09-08&period=day&breakdown_type=hourly
```

```json
{
  "period": {
    "date": "2025-09-08",
    "period_type": "day",
    "breakdown_type": "hourly"
  },
  "summary": {
    "total_revenue": 25000.00,
    "total_orders": 45,
    "average_order_value": 555.56
  },
  "breakdown": [
    {
      "time": "08:00",
      "revenue": 1200.00,
      "orders": 2,
      "percentage": 4.8
    },
    {
      "time": "09:00",
      "revenue": 2500.00,
      "orders": 5,
      "percentage": 10.0
    },
    {
      "time": "10:00",
      "revenue": 3200.00,
      "orders": 7,
      "percentage": 12.8
    },
    {
      "time": "11:00",
      "revenue": 2800.00,
      "orders": 6,
      "percentage": 11.2
    },
    {
      "time": "12:00",
      "revenue": 4500.00,
      "orders": 9,
      "percentage": 18.0
    },
    {
      "time": "13:00",
      "revenue": 3800.00,
      "orders": 8,
      "percentage": 15.2
    },
    {
      "time": "14:00",
      "revenue": 2200.00,
      "orders": 4,
      "percentage": 8.8
    },
    {
      "time": "15:00",
      "revenue": 1800.00,
      "orders": 3,
      "percentage": 7.2
    },
    {
      "time": "16:00",
      "revenue": 1500.00,
      "orders": 2,
      "percentage": 6.0
    },
    {
      "time": "17:00",
      "revenue": 1000.00,
      "orders": 1,
      "percentage": 4.0
    }
  ],
  "top_performers": [
    {
      "vendor_id": 1,
      "vendor_name": "Tasty Bites",
      "revenue": 5000.00,
      "orders": 10,
      "percentage": 20.0
    },
    {
      "vendor_id": 2,
      "vendor_name": "Quick Eats",
      "revenue": 4500.00,
      "orders": 9,
      "percentage": 18.0
    }
  ]
}
```

### Revenue Breakdown - By Vendor

```bash
GET /api/admin/revenue/breakdown/?date=2025-09-08&period=week&breakdown_type=by_vendor
```

```json
{
  "period": {
    "date": "2025-09-08",
    "period_type": "week",
    "breakdown_type": "by_vendor"
  },
  "summary": {
    "total_revenue": 150000.00,
    "total_orders": 280,
    "average_order_value": 535.71
  },
  "breakdown": [
    {
      "time": "Tasty Bites",
      "revenue": 35000.00,
      "orders": 65,
      "percentage": 23.3
    },
    {
      "time": "Quick Eats",
      "revenue": 28000.00,
      "orders": 52,
      "percentage": 18.7
    },
    {
      "time": "Fresh Market",
      "revenue": 22000.00,
      "orders": 41,
      "percentage": 14.7
    },
    {
      "time": "Gourmet Kitchen",
      "revenue": 18000.00,
      "orders": 33,
      "percentage": 12.0
    },
    {
      "time": "Street Food Hub",
      "revenue": 15000.00,
      "orders": 28,
      "percentage": 10.0
    }
  ],
  "top_performers": [
    {
      "vendor_id": 1,
      "vendor_name": "Tasty Bites",
      "revenue": 35000.00,
      "orders": 65,
      "percentage": 23.3
    },
    {
      "vendor_id": 2,
      "vendor_name": "Quick Eats",
      "revenue": 28000.00,
      "orders": 52,
      "percentage": 18.7
    }
  ]
}
```

## Error Handling

### Common Error Responses

**401 Unauthorized**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden**
```json
{
  "error": "Only superusers can access the admin panel"
}
```

**400 Bad Request**
```json
{
  "error": "Invalid date format. Use YYYY-MM-DD"
}
```

**500 Internal Server Error**
```json
{
  "error": "Failed to fetch dashboard statistics"
}
```

## Frontend Integration

### React/JavaScript Example

```javascript
// Dashboard Stats Component
const DashboardStats = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('/api/admin/dashboard/stats/?period=week', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          setStats(data);
        }
      } catch (error) {
        console.error('Error fetching stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (!stats) return <div>Error loading stats</div>;

  return (
    <div className="dashboard-stats">
      <StatCard
        title="Total Orders"
        value={stats.total_orders.value}
        trend={stats.total_orders.trend}
        change={stats.total_orders.change_percentage}
        icon={stats.total_orders.icon}
      />
      <StatCard
        title="Total Revenue"
        value={stats.total_revenue.formatted_value}
        trend={stats.total_revenue.trend}
        change={stats.total_revenue.change_percentage}
        icon={stats.total_revenue.icon}
      />
      <StatCard
        title="Pending Verification"
        value={stats.pending_verification.value}
        trend={stats.pending_verification.trend}
        change={stats.pending_verification.change_percentage}
        icon={stats.pending_verification.icon}
      />
      <StatCard
        title="Active Couriers"
        value={stats.active_couriers.value}
        trend={stats.active_couriers.trend}
        change={stats.active_couriers.change_percentage}
        icon={stats.active_couriers.icon}
      />
    </div>
  );
};

// Revenue Breakdown Component
const RevenueBreakdown = ({ date, period, breakdownType }) => {
  const [breakdown, setBreakdown] = useState(null);

  useEffect(() => {
    const fetchBreakdown = async () => {
      try {
        const params = new URLSearchParams({
          date: date,
          period: period,
          breakdown_type: breakdownType
        });
        
        const response = await fetch(`/api/admin/revenue/breakdown/?${params}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          setBreakdown(data);
        }
      } catch (error) {
        console.error('Error fetching breakdown:', error);
      }
    };

    fetchBreakdown();
  }, [date, period, breakdownType]);

  return (
    <div className="revenue-breakdown">
      <div className="summary">
        <h3>Revenue Summary</h3>
        <p>Total: {breakdown?.summary.total_revenue}</p>
        <p>Orders: {breakdown?.summary.total_orders}</p>
        <p>Average: {breakdown?.summary.average_order_value}</p>
      </div>
      
      <div className="breakdown-chart">
        {breakdown?.breakdown.map((item, index) => (
          <div key={index} className="breakdown-item">
            <span>{item.time}</span>
            <span>{item.revenue}</span>
            <span>{item.percentage}%</span>
          </div>
        ))}
      </div>
    </div>
  );
};
```

### Chart.js Integration Example

```javascript
// Revenue Chart Component
const RevenueChart = ({ breakdown }) => {
  const chartRef = useRef(null);

  useEffect(() => {
    if (breakdown && chartRef.current) {
      const ctx = chartRef.current.getContext('2d');
      
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: breakdown.breakdown.map(item => item.time),
          datasets: [{
            label: 'Revenue',
            data: breakdown.breakdown.map(item => item.revenue),
            borderColor: 'rgb(75, 192, 192)',
            tension: 0.1
          }]
        },
        options: {
          responsive: true,
          scales: {
            y: {
              beginAtZero: true
            }
          }
        }
      });
    }
  }, [breakdown]);

  return <canvas ref={chartRef}></canvas>;
};
```

## URL Compatibility

The following URL patterns are supported for frontend compatibility:

- `/api/admin/dashboard/stats/` - Primary endpoint
- `/api/api/admin/dashboard/stats/` - Double API prefix compatibility
- `/admin/dashboard/stats/` - No API prefix compatibility
- `/api/user/admin/dashboard/stats/` - User admin prefix compatibility

- `/api/admin/revenue/breakdown/` - Primary endpoint
- `/api/api/admin/revenue/breakdown/` - Double API prefix compatibility
- `/admin/revenue/breakdown/` - No API prefix compatibility
- `/api/user/admin/revenue/breakdown/` - User admin prefix compatibility

## Performance Considerations

- Dashboard stats are calculated in real-time and may take 1-2 seconds for large datasets
- Revenue breakdowns with large date ranges may be slower
- Consider implementing caching for frequently accessed data
- Use appropriate `period` and `breakdown_type` parameters to limit data scope

## Rate Limiting

- No specific rate limiting implemented
- Consider implementing rate limiting for production use
- Recommended: 100 requests per minute per user

## Security Notes

- All endpoints require superuser authentication
- Data is filtered based on user permissions
- No sensitive financial data is exposed beyond authorized users
- Consider implementing audit logging for financial data access
