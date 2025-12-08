"""
PRODUCTION DATABASE RESET SCRIPT
=================================

This script will DROP ALL TABLES and recreate the database schema.
⚠️ USE ONLY when production database is empty or you want to start fresh.

Run this on Render console or via SSH:
    python reset_production_db.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
django.setup()

from django.db import connection
from django.core.management import call_command

def reset_database():
    """Drop all tables and recreate from migrations"""
    
    print("=" * 60)
    print("🔴 PRODUCTION DATABASE RESET 🔴")
    print("=" * 60)
    
    # Confirm production environment
    if not os.getenv('DATABASE_URL'):
        print("❌ ERROR: Not a production environment (no DATABASE_URL)")
        print("This script should only run on Render with PostgreSQL")
        return
    
    print("\n⚠️  WARNING: This will DELETE ALL DATA in the database!")
    print("\nStarting database reset...")
    
    try:
        with connection.cursor() as cursor:
            # Get all tables
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public';
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"\n📋 Found {len(tables)} tables to drop")
            
            # Disable foreign key checks
            cursor.execute("SET CONSTRAINTS ALL DEFERRED;")
            
            # Drop all tables
            for table in tables:
                print(f"   Dropping table: {table}")
                cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
            
            print("\n✅ All tables dropped successfully")
        
        # Run migrations to recreate schema
        print("\n🔄 Running migrations to recreate database schema...")
        call_command('migrate', verbosity=2)
        
        print("\n" + "=" * 60)
        print("✅ DATABASE RESET COMPLETE!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Create superuser: python manage.py createsuperuser")
        print("2. Load initial data if needed")
        
    except Exception as e:
        print(f"\n❌ ERROR during database reset: {e}")
        print("\nIf this fails, manually delete the database on Render:")
        print("1. Go to Render Dashboard → Your Database")
        print("2. Delete the database")
        print("3. Redeploy your service (it will create a new database)")

if __name__ == '__main__':
    reset_database()
