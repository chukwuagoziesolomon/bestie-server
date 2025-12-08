#!/bin/bash
# Deployment script to handle migration conflicts on Render

echo "🚀 Starting deployment with migration fix..."

# Check if we're in production (PostgreSQL)
if [ -n "$DATABASE_URL" ]; then
    echo "📦 Production environment detected (PostgreSQL)"
    
    # Check if vendor_id column already exists in product_product table
    COLUMN_EXISTS=$(python manage.py dbshell <<EOF
SELECT COUNT(*) FROM information_schema.columns 
WHERE table_name='product_product' AND column_name='vendor_id';
EOF
)
    
    if [ "$COLUMN_EXISTS" -gt 0 ]; then
        echo "⚠️  vendor_id column already exists. Faking migration product.0002_initial..."
        python manage.py migrate product 0001_initial --fake
        python manage.py migrate product 0002_initial --fake
    fi
fi

# Run all other migrations normally
echo "🔄 Running migrations..."
python manage.py migrate

echo "✅ Migrations completed successfully!"
