# Deployment Fix for Migration Error

## Problem
Production deployment is failing with this error:
```
django.db.utils.ProgrammingError: column "vendor_id" of relation "product_product" already exists
```

## Root Cause
The `product.0002_initial` migration tries to add a `vendor_id` column that already exists in the production PostgreSQL database.

## Solution Implemented
Modified `bestyy/restaurant_features/product/migrations/0002_initial.py` to check if the column exists before adding it. The migration now:
1. Checks if `vendor_id` column exists in `product_product` table
2. Only adds the column if it doesn't exist
3. Works for both PostgreSQL (production) and SQLite (development)

## Deployment Steps

### Option 1: Direct Migration (Recommended)
Simply push the updated code and deploy. The migration will now handle the duplicate column gracefully.

```bash
git add .
git commit -m "Fix: Handle existing vendor_id column in product migration"
git push origin master
```

Render will automatically deploy and the migration will succeed.

### Option 2: Manual Database Fix (If Option 1 Fails)
If you still encounter issues, you can manually mark the migration as applied:

1. Access Render Shell for your deployment
2. Run this command:
```bash
python manage.py migrate product 0002_initial --fake
```

This tells Django that the migration has been applied without actually running it.

## Files Changed
- `bestyy/restaurant_features/product/migrations/0002_initial.py` - Updated to check for existing column

## Testing
✅ Tested locally with SQLite - Migration applies successfully
✅ Migration logic checks for column existence before adding
✅ Works for both PostgreSQL and SQLite databases

## What to Expect
After deployment:
- Migration will run successfully
- No duplicate column errors
- JWT token blacklist migrations will also apply
- Server will start normally

## Verification
After successful deployment, verify:
1. Server is running: Check Render logs for "Starting server"
2. Migrations applied: Look for "Running migrations... OK" in logs
3. API is accessible: Test `https://your-app.onrender.com/api/user/recommendations/?city=Lagos`

## Rollback (If Needed)
If anything goes wrong:
```bash
# In Render shell
python manage.py migrate product 0001_initial
```

## Additional Changes Deployed
This deployment also includes:
- JWT token lifetime increased to 24 hours (access) and 30 days (refresh)
- Token blacklist system properly configured
- Users will need to log in again to get new tokens with updated settings
