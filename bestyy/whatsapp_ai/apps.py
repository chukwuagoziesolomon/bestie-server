from django.apps import AppConfig


class WhatsappAiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'whatsapp_ai'
    verbose_name = 'WhatsApp AI'
    
    def ready(self):
        """Import signal handlers when the app is ready"""
        try:
            import whatsapp_ai.signals
        except ImportError:
            pass
