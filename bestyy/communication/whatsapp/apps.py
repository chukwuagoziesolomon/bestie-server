from django.apps import AppConfig


class WhatsappAiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bestyy.communication.whatsapp'
    # Backward-compat: keep legacy app label so migrations referencing 'whatsapp_ai' still work
    label = 'whatsapp_ai'
    verbose_name = 'WhatsApp AI'
    
    def ready(self):
        """Import signal handlers when the app is ready"""
        try:
            from bestyy.communication.whatsapp import signals  # noqa: F401
        except ImportError:
            pass
