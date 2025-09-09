# Revenue Analytics API Documentation

This document provides comprehensive documentation for the revenue analytics endpoints designed for the admin dashboard revenue graph.

## Overview

The Revenue Analytics API provides detailed revenue tracking and analytics data suitable for creating revenue graphs, charts, and dashboards. It supports multiple time periods, granularities, and chart formats.

## Base URL

```
http://localhost:8000/api/admin/revenue/
```

## Authentication

All endpoints require:
- **Authentication**: JWT token in Authorization header
- **Permissions**: Superuser access only (`is_superuser=True`)

```javascript
const headers = {
    'Authorization': 'Bearer YOUR_JWT_TOKEN',
    'Content-Type': 'application/json'
};
```

## Endpoints

### 1. Revenue Analytics

**Endpoint:** `GET /api/admin/revenue/analytics/`

**Description:** Provides comprehensive revenue analytics data including time series, summary statistics, and breakdowns.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `period` | string | `month` | Time period: `today`, `week`, `month`, `quarter`, `year`, `custom` |
| `start_date` | date | - | Start date for custom period (YYYY-MM-DD) |
| `end_date` | date | - | End date for custom period (YYYY-MM-DD) |
| `granularity` | string | `day` | Data granularity: `hour`, `day`, `week`, `month` |
| `currency` | string | `NGN` | Currency for revenue data |

#### Example Request

```javascript
// Get monthly revenue data with daily granularity
fetch('/api/admin/revenue/analytics/?period=month&granularity=day', {
    headers: headers
})

// Get custom period revenue data
fetch('/api/admin/revenue/analytics/?period=custom&start_date=2025-07-01&end_date=2025-07-31', {
    headers: headers
})
```

#### Response Format

```json
{
    "summary": {
        "total_revenue": 128700.00,
        "total_orders": 1250,
        "average_order_value": 102.96,
        "growth_percentage": 3.4,
        "previous_period_revenue": 124500.00
    },
    "time_series": [
        {
            "date": "2025-07-29T00:00:00Z",
            "revenue": 220342.76,
            "orders": 45,
            "average_order_value": 4896.51
        },
        {
            "date": "2025-07-30T00:00:00Z",
            "revenue": 185432.10,
            "orders": 38,
            "average_order_value": 4879.79
        }
    ],
    "breakdown": {
        "by_status": {
            "completed": 125000.00,
            "pending": 2500.00,
            "cancelled": 1200.00
        },
        "by_payment_method": {
            "card": 85000.00,
            "bank_transfer": 43700.00
        },
        "top_vendors": [
            {
                "id": 1,
                "business_name": "Tasty Bites",
                "revenue": 25000.00,
                "orders": 150,
                "percentage": 19.4
            }
        ]
    },
    "period": {
        "start_date": "2025-07-01T00:00:00Z",
        "end_date": "2025-07-31T23:59:59Z",
        "granularity": "day"
    }
}
```

### 2. Revenue Chart Data

**Endpoint:** `GET /api/admin/revenue/chart/`

**Description:** Provides revenue data specifically formatted for chart libraries (Chart.js, D3.js, etc.).

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `chart_type` | string | `line` | Chart type: `line`, `bar`, `pie`, `area` |
| `period` | string | `month` | Time period: `today`, `week`, `month`, `quarter`, `year` |
| `granularity` | string | `day` | Data granularity: `hour`, `day`, `week`, `month` |

#### Example Request

```javascript
// Get line chart data for monthly revenue
fetch('/api/admin/revenue/chart/?chart_type=line&period=month&granularity=day', {
    headers: headers
})

// Get bar chart data for weekly revenue
fetch('/api/admin/revenue/chart/?chart_type=bar&period=week&granularity=day', {
    headers: headers
})
```

#### Response Format

```json
{
    "chart_type": "line",
    "labels": ["Jul 29", "Jul 30", "Jul 31"],
    "datasets": [
        {
            "label": "Revenue (₦)",
            "data": [220342.76, 185432.10, 198765.43],
            "borderColor": "#10B981",
            "backgroundColor": "rgba(16, 185, 129, 0.1)",
            "fill": true,
            "tension": 0.4
        }
    ],
    "options": {
        "responsive": true,
        "maintainAspectRatio": false,
        "scales": {
            "y": {
                "beginAtZero": true,
                "ticks": {
                    "callback": "function(value) { return '₦' + value.toLocaleString(); }"
                }
            }
        },
        "plugins": {
            "legend": {
                "display": true,
                "position": "top"
            },
            "tooltip": {
                "callbacks": {
                    "label": "function(context) { return '₦' + context.parsed.y.toLocaleString(); }"
                }
            }
        }
    }
}
```

## Frontend Integration Examples

### 1. Basic Revenue Graph (Chart.js)

```javascript
class RevenueChart {
    constructor(containerId) {
        this.containerId = containerId;
        this.chart = null;
    }

    async loadRevenueData(period = 'month', granularity = 'day') {
        try {
            const response = await fetch(
                `/api/admin/revenue/chart/?chart_type=line&period=${period}&granularity=${granularity}`,
                {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                        'Content-Type': 'application/json'
                    }
                }
            );

            if (!response.ok) {
                throw new Error('Failed to fetch revenue data');
            }

            const chartData = await response.json();
            this.renderChart(chartData);
        } catch (error) {
            console.error('Error loading revenue data:', error);
        }
    }

    renderChart(chartData) {
        const ctx = document.getElementById(this.containerId).getContext('2d');
        
        if (this.chart) {
            this.chart.destroy();
        }

        this.chart = new Chart(ctx, {
            type: chartData.chart_type,
            data: {
                labels: chartData.labels,
                datasets: chartData.datasets
            },
            options: chartData.options
        });
    }

    updatePeriod(period) {
        this.loadRevenueData(period);
    }
}

// Usage
const revenueChart = new RevenueChart('revenue-chart');
revenueChart.loadRevenueData('month', 'day');
```

### 2. Revenue Summary Display

```javascript
class RevenueSummary {
    constructor(containerId) {
        this.containerId = containerId;
    }

    async loadSummary(period = 'month') {
        try {
            const response = await fetch(
                `/api/admin/revenue/analytics/?period=${period}`,
                {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                        'Content-Type': 'application/json'
                    }
                }
            );

            if (!response.ok) {
                throw new Error('Failed to fetch revenue summary');
            }

            const data = await response.json();
            this.renderSummary(data.summary);
        } catch (error) {
            console.error('Error loading revenue summary:', error);
        }
    }

    renderSummary(summary) {
        const container = document.getElementById(this.containerId);
        container.innerHTML = `
            <div class="revenue-summary">
                <div class="revenue-total">
                    <h2>₦${summary.total_revenue.toLocaleString()}</h2>
                    <div class="growth-indicator ${summary.growth_percentage >= 0 ? 'positive' : 'negative'}">
                        ${summary.growth_percentage >= 0 ? '+' : ''}${summary.growth_percentage}%
                    </div>
                </div>
                <div class="revenue-stats">
                    <div class="stat">
                        <span class="label">Total Orders</span>
                        <span class="value">${summary.total_orders}</span>
                    </div>
                    <div class="stat">
                        <span class="label">Avg Order Value</span>
                        <span class="value">₦${summary.average_order_value.toLocaleString()}</span>
                    </div>
                </div>
            </div>
        `;
    }
}

// Usage
const revenueSummary = new RevenueSummary('revenue-summary');
revenueSummary.loadSummary('month');
```

### 3. Interactive Revenue Dashboard

```javascript
class RevenueDashboard {
    constructor() {
        this.chart = new RevenueChart('revenue-chart');
        this.summary = new RevenueSummary('revenue-summary');
        this.currentPeriod = 'month';
        this.currentGranularity = 'day';
        
        this.initializeEventListeners();
        this.loadData();
    }

    initializeEventListeners() {
        // Period selector
        document.getElementById('period-selector').addEventListener('change', (e) => {
            this.currentPeriod = e.target.value;
            this.loadData();
        });

        // Granularity selector
        document.getElementById('granularity-selector').addEventListener('change', (e) => {
            this.currentGranularity = e.target.value;
            this.loadData();
        });

        // Refresh button
        document.getElementById('refresh-revenue').addEventListener('click', () => {
            this.loadData();
        });
    }

    async loadData() {
        await Promise.all([
            this.summary.loadSummary(this.currentPeriod),
            this.chart.loadRevenueData(this.currentPeriod, this.currentGranularity)
        ]);
    }
}

// Initialize dashboard
const dashboard = new RevenueDashboard();
```

## HTML Structure

```html
<div class="revenue-dashboard">
    <div class="dashboard-header">
        <h1>Revenue Details</h1>
        <div class="controls">
            <select id="period-selector">
                <option value="today">Today</option>
                <option value="week">This Week</option>
                <option value="month" selected>This Month</option>
                <option value="quarter">This Quarter</option>
                <option value="year">This Year</option>
            </select>
            <select id="granularity-selector">
                <option value="hour">Hourly</option>
                <option value="day" selected>Daily</option>
                <option value="week">Weekly</option>
                <option value="month">Monthly</option>
            </select>
            <button id="refresh-revenue">Refresh</button>
        </div>
    </div>
    
    <div id="revenue-summary" class="revenue-summary"></div>
    
    <div class="chart-container">
        <canvas id="revenue-chart"></canvas>
    </div>
</div>
```

## CSS Styling

```css
.revenue-dashboard {
    padding: 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.dashboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.controls {
    display: flex;
    gap: 10px;
}

.controls select, .controls button {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: white;
}

.revenue-summary {
    margin-bottom: 30px;
}

.revenue-total {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 15px;
}

.revenue-total h2 {
    font-size: 2.5rem;
    font-weight: bold;
    color: #111827;
    margin: 0;
}

.growth-indicator {
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 14px;
    font-weight: bold;
}

.growth-indicator.positive {
    background-color: #D1FAE5;
    color: #065F46;
}

.growth-indicator.negative {
    background-color: #FEE2E2;
    color: #991B1B;
}

.revenue-stats {
    display: flex;
    gap: 30px;
}

.stat {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.stat .label {
    font-size: 14px;
    color: #6B7280;
}

.stat .value {
    font-size: 18px;
    font-weight: 600;
    color: #111827;
}

.chart-container {
    position: relative;
    height: 400px;
    width: 100%;
}
```

## Error Handling

```javascript
async function handleRevenueAPIError(error, context) {
    console.error(`Revenue API Error (${context}):`, error);
    
    if (error.status === 401) {
        // Token expired, redirect to login
        window.location.href = '/login';
    } else if (error.status === 403) {
        // Insufficient permissions
        showError('You do not have permission to view revenue data');
    } else if (error.status === 500) {
        // Server error
        showError('Server error. Please try again later.');
    } else {
        // Network or other error
        showError('Failed to load revenue data. Please check your connection.');
    }
}

function showError(message) {
    // Implement your error notification system
    console.error(message);
}
```

## Performance Considerations

1. **Caching**: Cache API responses for better performance
2. **Pagination**: For large datasets, consider implementing pagination
3. **Debouncing**: Debounce user input for period/granularity changes
4. **Loading States**: Show loading indicators during API calls

## Testing

```javascript
// Test revenue analytics endpoint
async function testRevenueAnalytics() {
    try {
        const response = await fetch('/api/admin/revenue/analytics/?period=month');
        const data = await response.json();
        console.log('Revenue Analytics:', data);
    } catch (error) {
        console.error('Test failed:', error);
    }
}

// Test chart data endpoint
async function testRevenueChart() {
    try {
        const response = await fetch('/api/admin/revenue/chart/?chart_type=line&period=week');
        const data = await response.json();
        console.log('Chart Data:', data);
    } catch (error) {
        console.error('Test failed:', error);
    }
}
```

This API provides everything needed to create the revenue graph shown in your admin dashboard image, with support for different time periods, granularities, and chart types.
