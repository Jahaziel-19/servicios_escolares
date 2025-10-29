from django.contrib import admin
from .models import Tramite, Bitacora, Proceso, Residencia, ResidenciaBitacoraEntry

# Register your models here.
admin.site.register(Tramite)
admin.site.register(Bitacora)
admin.site.register(Proceso)
admin.site.register(Residencia)
admin.site.register(ResidenciaBitacoraEntry)