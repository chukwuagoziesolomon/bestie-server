# Generated migration to add latitude and longitude to VendorProfile

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0014_userprofile_budget_auto_check_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendorprofile',
            name='latitude',
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                help_text='Latitude coordinate of the vendor location',
                max_digits=9,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='vendorprofile',
            name='longitude',
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                help_text='Longitude coordinate of the vendor location',
                max_digits=9,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='vendorprofile',
            name='last_location_update',
            field=models.DateTimeField(
                blank=True,
                help_text='When the location was last updated',
                null=True
            ),
        ),
    ]
