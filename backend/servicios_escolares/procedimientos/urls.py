from django.urls import path
from . import views
from .views_boleta import (
    BoletaListView, generar_boleta_view, 
    generar_boleta_documento, generar_boleta_pdf, ajax_generar_boleta
)

app_name = 'procedimientos'

urlpatterns = [
    path('tramites/', views.TramiteListView.as_view(), name='lista_tramites'),
    path('tramites/crear/', views.crear_tramite, name='crear_tramite'),
    path('tramites/dashboard/', views.dashboard_tramites, name='dashboard_tramites'),
    path('constancia/<str:matricula>/', views.descargar_constancia, name='descargar_constancia'),
    path('kardex/<str:matricula>/', views.descargar_kardex, name='descargar_kardex'),
    
    path('procesos/', views.ProcesoListView.as_view(), name='lista_procesos'),
    
    # URLs para boletas de calificaciones
    path('boletas/', BoletaListView.as_view(), name='boleta_list'),
    path('boletas/generar/', generar_boleta_view, name='generar_boleta'),
    path('boleta/<str:matricula>/', views.descargar_boleta, name='descargar_boleta'),
    path('boleta/documento/<int:alumno_id>/<int:periodo_id>/', generar_boleta_documento, name='generar_boleta_documento'),
    path('boleta/pdf/<int:alumno_id>/<int:periodo_id>/', generar_boleta_pdf, name='generar_boleta_pdf'),
    path('ajax/generar-boleta/', ajax_generar_boleta, name='ajax_generar_boleta'),
    
    #path('kardex/<str:matricula>/pdf/', views.descargar_kardex_pdf, name='descargar_kardex_pdf'),
    # Agrega vistas para kardex, boleta y otros trámites similares
]
