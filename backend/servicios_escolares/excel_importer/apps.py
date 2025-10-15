from django.apps import AppConfig


class ExcelImporterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'excel_importer'
    verbose_name = 'Importador de Excel'
