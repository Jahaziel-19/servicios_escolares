from django.urls import path
from . import views_publico

# No necesitamos app_name aquí porque se define en la inclusión

urlpatterns = [
    # Página principal de registro
    path('registro/', views_publico.registro_aspirante, name='registro_aspirante'),
    
    # Corrección de datos para aspirantes seleccionados
    path('correccion/inicio/', views_publico.correccion_seleccionado_inicio, name='correccion_seleccionado_inicio'),
    path('correccion/<str:folio>/', views_publico.correccion_seleccionado_form, name='correccion_seleccionado_form'),
    path('correccion/exitoso/<str:folio>/', views_publico.correccion_exitoso, name='correccion_exitoso'),
    
    # Página de confirmación después del registro
    path('registro/exitoso/<str:folio>/', views_publico.registro_exitoso, name='registro_exitoso'),
    
    # Consultar estado de solicitud
    path('consultar/', views_publico.consultar_solicitud, name='consultar_solicitud'),
    
    # Información del proceso de admisión
    path('informacion/', views_publico.informacion_proceso, name='informacion_proceso'),
    
    # URLs AJAX para validaciones en tiempo real
    path('ajax/validar-curp/', views_publico.ajax_validar_curp, name='ajax_validar_curp'),
    path('ajax/validar-email/', views_publico.ajax_validar_email, name='ajax_validar_email'),
    path('ajax/estadisticas/', views_publico.ajax_estadisticas_proceso, name='ajax_estadisticas_proceso'),
    path('ajax/reenviar-ficha/', views_publico.ajax_reenviar_ficha, name='ajax_reenviar_ficha'),
]