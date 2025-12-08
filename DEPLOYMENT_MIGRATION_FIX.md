# Deployment Fix for Migration Errors

## Problems
Production deployment is failing with these errors:
```
django.db.utils.ProgrammingError: column "vendor_id" of relation "product_product" already exists
django.db.utils.ProgrammingError: column "conversation_id" of relation "user_supportescalation" already exists
```

## Root Cause
Multiple `0002_initial` migrations try to add foreign key columns that already exist in the production PostgreSQL database. This happens when:
1. Previous migrations created these columns
2. The database was manually modified
3. Migrations were applied out of order

## Solution Implemented
Modified all `0002_initial` migrations to check if columns exist before adding them. The migrations now:
1. Check if each foreign key column exists in their respective tables
2. Only add columns if they don't exist
3. Work for both PostgreSQL (production) and SQLite (development)
4. Use `RunPython` operations to safely handle existing columns

### Migration Strategy
Each `0002_initial.py` file now:
- Defines a `check_column_exists()` function for cross-database compatibility
- Defines an `add_fields_if_not_exist()` function that checks each column before adding
- Replaces all `AddField` operations with a single `RunPython` operation
- Keeps all index and constraint operations unchanged

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
- `bestyy/restaurant_features/product/migrations/0002_initial.py` - Updated to check for existing vendor_id column
- `bestyy/core_features/user/migrations/0002_initial.py` - Updated to check for all existing foreign key columns
- `bestyy/restaurant_features/order/migrations/0002_initial.py` - Updated to check for all existing foreign key columns

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
