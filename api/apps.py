from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    verbose_name = 'FoodLoop API'
    
    def ready(self):
        """Initialize API-specific configurations"""
        try:
            # Import any API-specific signal handlers or startup tasks
            pass
        except ImportError:
            pass