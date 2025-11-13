#!/usr/bin/env python
"""
Script to manually create database tables to bypass migration issues.
"""

import os
import sys
import django

# Add the bestyy directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bestyy'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.settings')
django.setup()

from django.db import connection

def create_tables():
    """Create all database tables manually."""

    with connection.cursor() as cursor:
        # Create tables in dependency order

        # 1. Django auth tables (if not exist)
        print("Creating Django auth tables...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS django_content_type (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_label VARCHAR(100) NOT NULL,
                model VARCHAR(100) NOT NULL,
                UNIQUE(app_label, model)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_permission (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255),
                content_type_id INTEGER REFERENCES django_content_type(id),
                codename VARCHAR(100) NOT NULL,
                UNIQUE(content_type_id, codename)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_group (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(150) NOT NULL UNIQUE
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_group_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER REFERENCES auth_group(id),
                permission_id INTEGER REFERENCES auth_permission(id),
                UNIQUE(group_id, permission_id)
            );
        """)

        # 2. User table
        print("Creating User table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core_features_user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                password VARCHAR(128) NOT NULL,
                last_login DATETIME,
                is_superuser BOOLEAN NOT NULL DEFAULT 0,
                username VARCHAR(150),
                first_name VARCHAR(150),
                last_name VARCHAR(150),
                email VARCHAR(254) NOT NULL UNIQUE,
                is_staff BOOLEAN NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                date_joined DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                social_provider VARCHAR(20),
                social_uid VARCHAR(255),
                is_social_signup BOOLEAN NOT NULL DEFAULT 0,
                profile_complete BOOLEAN NOT NULL DEFAULT 0,
                phone VARCHAR(16),
                role VARCHAR(20) NOT NULL DEFAULT 'user'
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core_features_user_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES core_features_user(id),
                group_id INTEGER REFERENCES auth_group(id),
                UNIQUE(user_id, group_id)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core_features_user_user_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES core_features_user(id),
                permission_id INTEGER REFERENCES auth_permission(id),
                UNIQUE(user_id, permission_id)
            );
        """)

        # 3. User profiles
        print("Creating User profiles...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core_features_userprofile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone VARCHAR(16) NOT NULL,
                address VARCHAR(255),
                nick_name VARCHAR(100),
                language VARCHAR(50),
                profile_picture VARCHAR(100),
                email_notifications BOOLEAN NOT NULL DEFAULT 1,
                push_notifications BOOLEAN NOT NULL DEFAULT 1,
                user_id INTEGER REFERENCES core_features_user(id) UNIQUE
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core_features_userrecommendationhistory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                last_sent DATETIME,
                total_sent INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER REFERENCES core_features_user(id) UNIQUE
            );
        """)

        # 4. Vendor and Courier profiles
        print("Creating Vendor and Courier profiles...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core_features_vendorprofile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone VARCHAR(16) NOT NULL,
                business_name VARCHAR(255) NOT NULL,
                business_category VARCHAR(100) NOT NULL,
                cac_number VARCHAR(100),
                business_description TEXT,
                logo VARCHAR(100),
                business_address VARCHAR(255) NOT NULL,
                delivery_radius VARCHAR(50) NOT NULL,
                service_areas VARCHAR(255) NOT NULL,
                opening_hours TIME,
                closing_hours TIME,
                offers_delivery BOOLEAN NOT NULL DEFAULT 0,
                verification_status VARCHAR(10) NOT NULL DEFAULT 'pending',
                verification_notes TEXT,
                verification_date DATETIME,
                cac_document VARCHAR(100),
                valid_id VARCHAR(100),
                proof_of_address VARCHAR(100),
                is_suspended BOOLEAN NOT NULL DEFAULT 0,
                suspension_reason TEXT,
                suspension_date DATETIME,
                suspension_duration_days INTEGER,
                activation_date DATETIME,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER REFERENCES core_features_user(id) UNIQUE
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core_features_courierprofile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone VARCHAR(16) NOT NULL,
                service_areas VARCHAR(255) NOT NULL,
                delivery_radius VARCHAR(50) NOT NULL,
                opening_hours TIME NOT NULL,
                closing_hours TIME NOT NULL,
                has_bike BOOLEAN NOT NULL DEFAULT 0,
                verification_preference VARCHAR(50) NOT NULL,
                nin_number VARCHAR(20),
                id_upload VARCHAR(100),
                profile_photo VARCHAR(100),
                agreed_to_terms BOOLEAN NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                vehicle_type VARCHAR(20),
                verification_status VARCHAR(10) NOT NULL DEFAULT 'pending',
                is_suspended BOOLEAN NOT NULL DEFAULT 0,
                suspension_reason TEXT,
                suspension_date DATETIME,
                suspension_duration_days INTEGER,
                activation_date DATETIME,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER REFERENCES core_features_user(id) UNIQUE
            );
        """)

        # 5. Addresses
        print("Creating Addresses...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core_features_address (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address_type VARCHAR(10) NOT NULL DEFAULT 'home',
                full_name VARCHAR(255) NOT NULL,
                phone_number VARCHAR(16) NOT NULL,
                street_address VARCHAR(255) NOT NULL,
                city VARCHAR(100) NOT NULL,
                state VARCHAR(100) NOT NULL,
                postal_code VARCHAR(20) NOT NULL,
                is_default BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER REFERENCES core_features_user(id)
            );
        """)

        # 6. Transfer recipients
        print("Creating Transfer recipients...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core_features_transferrecipient (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient_type VARCHAR(20) NOT NULL,
                account_name VARCHAR(255) NOT NULL,
                account_number VARCHAR(20) NOT NULL,
                bank_name VARCHAR(100) NOT NULL,
                bank_code VARCHAR(10) NOT NULL,
                paystack_recipient_code VARCHAR(100),
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER REFERENCES core_features_user(id)
            );
        """)

        # 7. Pending users
        print("Creating Pending users...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core_features_pendinguser (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR(254) NOT NULL UNIQUE,
                password VARCHAR(128) NOT NULL,
                first_name VARCHAR(150) NOT NULL,
                last_name VARCHAR(150) NOT NULL,
                phone VARCHAR(16) NOT NULL,
                user_type VARCHAR(10) NOT NULL,
                verification_code VARCHAR(6) NOT NULL,
                code_generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                profile_data TEXT NOT NULL DEFAULT '{}',
                is_verified BOOLEAN NOT NULL DEFAULT 0,
                verified_at DATETIME,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL
            );
        """)

        # 8. Image uploads
        print("Creating Image uploads...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core_features_imageupload (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_type VARCHAR(20) NOT NULL,
                image_hash VARCHAR(64) NOT NULL,
                cloudinary_public_id VARCHAR(100) NOT NULL UNIQUE,
                cloudinary_url VARCHAR(200) NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                file_size INTEGER NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER REFERENCES core_features_user(id)
            );
        """)

        # Create indexes
        print("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pendinguser_email ON core_features_pendinguser(email);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pendinguser_phone ON core_features_pendinguser(phone);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pendinguser_code ON core_features_pendinguser(verification_code);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pendinguser_expires ON core_features_pendinguser(expires_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_imageupload_hash ON core_features_imageupload(image_hash, image_type, is_active);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_imageupload_user ON core_features_imageupload(user_id, image_type);")

        print("✅ All tables created successfully!")

if __name__ == "__main__":
    create_tables()