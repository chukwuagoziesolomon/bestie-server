from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a superuser for the application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='admin@bestyy.com',
            help='Email for the superuser'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='admin123456',
            help='Password for the superuser'
        )
        parser.add_argument(
            '--first-name',
            type=str,
            default='Admin',
            help='First name for the superuser'
        )
        parser.add_argument(
            '--last-name',
            type=str,
            default='User',
            help='Last name for the superuser'
        )

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        first_name = options['first_name']
        last_name = options['last_name']

        # Check if superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING('Superuser already exists. Skipping creation.')
            )
            return

        try:
            with transaction.atomic():
                # Create superuser
                user = User.objects.create_superuser(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created superuser: {user.email}'
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Login credentials:'
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  Email: {email}'
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  Password: {password}'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {str(e)}')
            )
