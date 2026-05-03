from django.apps import AppConfig


class AuditlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auditlog'
    verbose_name = 'Audit Logs'

    def ready(self):
        import auditlog.signals
