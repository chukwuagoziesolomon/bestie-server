from django.apps import AppConfig


class OrderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bestyy.restaurant_features.order'
    
    def ready(self):
        # Import signals to register them
        from bestyy.restaurant_features.order import signals  # noqa: F401
