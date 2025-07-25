# Generated by Django 5.2.4 on 2025-07-20 11:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0007_userprofile_address_userprofile_email_notifications_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Accommodation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('accommodation_type', models.CharField(choices=[('hotel', 'Hotel'), ('airbnb', 'Airbnb'), ('shortlet', 'Shortlet'), ('guesthouse', 'Guest House'), ('apartment', 'Apartment')], default='hotel', max_length=20)),
                ('description', models.TextField(blank=True, null=True)),
                ('address', models.CharField(max_length=255)),
                ('city', models.CharField(max_length=100)),
                ('state', models.CharField(max_length=100)),
                ('photos', models.ImageField(blank=True, null=True, upload_to='accommodation_photos/')),
                ('logo', models.ImageField(blank=True, null=True, upload_to='accommodation_logos/')),
                ('phone', models.CharField(blank=True, max_length=16, null=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('website', models.URLField(blank=True, null=True)),
                ('rating', models.DecimalField(decimal_places=1, default=0.0, max_digits=3)),
                ('price_range', models.CharField(blank=True, max_length=50, null=True)),
                ('amenities', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='booking',
            name='vendor',
        ),
        migrations.AddField(
            model_name='booking',
            name='room_type',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='accommodation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='bookings', to='user.accommodation'),
        ),
    ]
