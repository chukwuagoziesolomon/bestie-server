from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Setup admin user if none exists'

    def handle(self, *args, **options):
        # Check if any superuser exists
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING('Superuser already exists. Skipping setup.')
            )
            return

        try:
            with transaction.atomic():
                # Create superuser with default credentials
                user = User.objects.create_superuser(
                    email='admin@bestyy.com',
                    password='admin123456',
                    first_name='Admin',
                    last_name='User',
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Admin user created successfully!'
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'📧 Email: admin@bestyy.com'
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'🔑 Password: admin123456'
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'🌐 Admin URL: https://bestie-server.onrender.com/admin/'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating admin user: {str(e)}')
            )
