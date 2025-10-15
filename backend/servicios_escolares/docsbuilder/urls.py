from django.urls import path
from . import views

app_name = 'docsbuilder'

urlpatterns = [
    path('', views.listar_plantillas.as_view(), name='listar_plantillas'),
    path('subir/', views.subir_plantilla, name='subir_plantilla'),
    path('mapeo/<int:plantilla_id>/', views.mapeo_variables, name='mapeo_variables'),
    path('generar/<int:plantilla_id>/<int:alumno_id>/', views.generar_documento_tramite, name='generar_documento_tramite'),
    path('generar-boleta/<int:plantilla_id>/<int:alumno_id>/<int:periodo_id>/', views.generar_boleta_tramite, name='generar_boleta_tramite'),
    path('eliminar/<int:plantilla_id>/', views.eliminar_plantilla, name='eliminar_plantilla'),
]
