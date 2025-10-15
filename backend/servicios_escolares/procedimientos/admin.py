from django.contrib import admin
from .models import Tramite, Bitacora, Proceso

# Register your models here.
admin.site.register(Tramite)
admin.site.register(Bitacora)
admin.site.register(Proceso)