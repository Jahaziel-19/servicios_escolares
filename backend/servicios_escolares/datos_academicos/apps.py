from django.apps import AppConfig


class DatosAcademicosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'datos_academicos'
    verbose_name = 'Datos Académicos'
    
    def ready(self):
        import datos_academicos.signals
