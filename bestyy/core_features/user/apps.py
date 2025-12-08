from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _


def create_admin_user(sender, **kwargs):
    """Create an admin user if one doesn't exist."""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Only create if table exists and no superuser exists
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                email='admin@example.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )
    except Exception as e:
        # Silently fail during migrations if tables aren't ready
        print(f"Info: Skipping admin user creation during migration: {e}")
        pass


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bestyy.core_features.user'
    verbose_name = _('Users')

    def ready(self):
        from bestyy.core_features.user import signals
        # Connect the post_migrate signal to create an admin user
        post_migrate.connect(create_admin_user, sender=self)
