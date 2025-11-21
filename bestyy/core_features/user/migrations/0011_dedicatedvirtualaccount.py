# Generated migration to resolve conflict with Render deployment
# This migration was previously deleted but is still recorded in Render's database

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0010_add_order_fields'),
    ]

    operations = [
        # Empty migration - just to satisfy the migration chain
        # The actual DedicatedVirtualAccount functionality was removed
    ]
