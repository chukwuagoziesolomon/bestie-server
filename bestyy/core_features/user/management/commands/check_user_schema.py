from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Check the database schema for the User model'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Check if the user table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_user';")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                self.stdout.write(self.style.ERROR("User table does not exist!"))
                return
                
            # Get table info
            cursor.execute("PRAGMA table_info(user_user);")
            columns = cursor.fetchall()
            
            self.stdout.write(self.style.SUCCESS("User table columns:"))
            for col in columns:
                self.stdout.write(f"- {col[1]} ({col[2]})")
                
            # Check if role column exists
            role_column = any(col[1] == 'role' for col in columns)
            if role_column:
                self.stdout.write(self.style.SUCCESS("\nRole column exists in the database"))
                
                # Check role values
                cursor.execute("SELECT DISTINCT role FROM user_user;")
                roles = cursor.fetchall()
                self.stdout.write(self.style.SUCCESS("\nExisting roles in the database:"))
                for role in roles:
                    self.stdout.write(f"- {role[0]}")
            else:
                self.stdout.write(self.style.ERROR("\nRole column does not exist in the database"))
