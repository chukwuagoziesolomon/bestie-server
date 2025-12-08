# How to Reset Production Database on Render

## Problem
The production database has old schema/migrations that conflict with current models, causing warnings about missing models and existing constraints/indexes.

## Solution: Fresh Database Start

Since production database is **EMPTY**, the cleanest approach is to reset it completely.

---

## Method 1: Delete Database (Recommended - Cleanest)

### Steps:

1. **Go to Render Dashboard**
   - Navigate to https://dashboard.render.com/
   - Select your PostgreSQL database

2. **Delete the Database**
   - Click on **Settings** tab
   - Scroll to bottom
   - Click **"Delete Database"** button
   - Confirm deletion

3. **Create New Database**
   - Click **"New +"** → **"PostgreSQL"**
   - Name it (e.g., `bestyy-db`)
   - Select same region as your service
   - Choose Free tier
   - Click **"Create Database"**

4. **Update Service Environment Variable**
   - Go to your Web Service (bestyy-server)
   - Click **"Environment"** tab
   - Update `DATABASE_URL` with new database's Internal Connection String
   - Click **"Save Changes"**

5. **Redeploy**
   - Render will automatically redeploy
   - Fresh migrations will run on clean database
   - ✅ No more warnings!

---

## Method 2: Drop All Tables via Shell (Alternative)

If you want to keep the same database but reset all tables:

1. **Open Render Shell**
   - Go to your Web Service
   - Click **"Shell"** tab
   - Wait for terminal to load

2. **Run the reset script**
   ```bash
   python reset_production_db.py
   ```

   This will:
   - Drop all existing tables
   - Run migrations from scratch
   - Create fresh database schema

3. **Or manually drop tables via psql**
   ```bash
   # Connect to database
   psql $DATABASE_URL
   
   # Drop all tables
   DROP SCHEMA public CASCADE;
   CREATE SCHEMA public;
   GRANT ALL ON SCHEMA public TO postgres;
   GRANT ALL ON SCHEMA public TO public;
   \q
   
   # Run migrations
   python manage.py migrate
   ```

---

## After Reset

### Create Superuser
```bash
python manage.py createsuperuser
```

### Verify Everything Works
1. Check admin panel: https://bestyy-server.onrender.com/admin/
2. Test API endpoints
3. Verify JWT authentication with updated token lifetimes (24h/30d)

---

## Why This Happened

The `0002_initial.py` migrations were trying to add:
- **Models that don't exist anymore**: `Transfer`, `AnonymousCart`, `WebsiteCartItem`
- **Fields that were removed**: `Favorite.vendor`, `anonymous_cart`, etc.
- **Indexes/constraints that already exist**: From previous migration attempts

**Root cause**: Database schema doesn't match current models due to iterative changes during development.

**Solution**: Fresh start = Clean slate = No conflicts ✅

---

## Prevention for Future

1. **Test migrations locally first**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Use squash migrations** when you have many migration files
   ```bash
   python manage.py squashmigrations user 0001 0003
   ```

3. **For major schema changes**, consider:
   - Creating a new migration from scratch
   - Or resetting database if no production data exists

---

## Quick Command Reference

```bash
# Check migration status
python manage.py showmigrations

# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```
