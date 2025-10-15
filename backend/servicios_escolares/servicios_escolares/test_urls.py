from django.urls import path, include

urlpatterns = [
    # Incluir todas las URLs del app `admision` (esto registra el namespace 'admision'
    # y, dentro de él, el subnamespace 'admision_publico' en /admision/publico/)
    path('admision/', include(('admision.urls', 'admision'), namespace='admision')),
]