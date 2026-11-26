from django.apps import AppConfig


class HelpdeskConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'helpdesk'
    verbose_name = 'IT Helpdesk'
    
    def ready(self):
        """Import signals when app is ready."""
        import helpdesk.signals  # noqa