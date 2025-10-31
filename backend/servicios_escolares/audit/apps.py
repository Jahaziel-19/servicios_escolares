from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = 'audit'
    verbose_name = 'Auditoría'

    def ready(self):
        # Importa señales para registrar cambios
        from . import signals  # noqa: F401