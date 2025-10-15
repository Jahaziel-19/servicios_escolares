from django.urls import path, include
from . import views
from . import views_admin_publico

app_name = 'admision'

urlpatterns = [
    # URLs públicas para aspirantes (nuevo formulario independiente)
    path('publico/', include(('admision.urls_publico', 'admision_publico'))),
    
    # URLs públicas para aspirantes (formulario builder existente)
    path('', views.solicitud_admision, name='solicitud_admision'),
    path('exitosa/<str:folio>/', views.solicitud_exitosa, name='solicitud_exitosa'),
    path('consultar/', views.consultar_solicitud, name='consultar_solicitud'),
    path('editar/<str:folio>/', views.editar_solicitud, name='editar_solicitud'),
    
    # URLs administrativas
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/solicitudes/', views.admin_solicitudes, name='admin_solicitudes'),
    path('admin/solicitud/<int:solicitud_id>/', views.admin_ver_solicitud, name='admin_ver_solicitud'),
    path('admin/solicitud/<int:solicitud_id>/cambiar-estado/', views.admin_cambiar_estado_solicitud, name='admin_cambiar_estado_solicitud'),
    path('admin/solicitud/<int:solicitud_id>/generar-ficha/', views.admin_generar_ficha, name='admin_generar_ficha'),
    path('admin/solicitud/<int:solicitud_id>/enviar-ficha-email/', views.admin_enviar_ficha_email, name='admin_enviar_ficha_email'),
    path('admin/ficha/<int:ficha_id>/descargar/', views.admin_descargar_ficha, name='admin_descargar_ficha'),
    
    # URLs para administración del formulario público
    path('admin/publico/dashboard/', views_admin_publico.admin_dashboard_publico, name='admin_dashboard_publico'),
    path('admin/publico/solicitudes/', views_admin_publico.admin_solicitudes_publico, name='admin_solicitudes_publico'),
    path('admin/publico/solicitud/<str:folio>/', views_admin_publico.admin_ver_solicitud_publico, name='admin_ver_solicitud_publico'),
    path('admin/publico/solicitud/<str:folio>/cambiar-estado/', views_admin_publico.admin_cambiar_estado_solicitud, name='admin_cambiar_estado_solicitud_publico'),
    path('admin/publico/solicitud/<str:folio>/generar-ficha/', views_admin_publico.admin_generar_ficha_publico, name='admin_generar_ficha_publico'),
    path('admin/publico/exportar/', views_admin_publico.admin_exportar_solicitudes, name='admin_exportar_solicitudes'),
    path('admin/publico/estadisticas/', views_admin_publico.admin_estadisticas_avanzadas, name='admin_estadisticas_avanzadas'),
    path('admin/publico/accion-masiva/', views_admin_publico.admin_accion_masiva, name='admin_accion_masiva'),
    
    # URLs para gestión de formularios
    path('admin/formularios/', views.admin_formularios, name='admin_formularios'),
    path('admin/formularios/crear/', views.admin_crear_formulario, name='admin_crear_formulario'),
    path('admin/formularios/<int:periodo_id>/editar/', views.admin_editar_formulario, name='admin_editar_formulario'),
    path('admin/formularios/<int:periodo_id>/ver/', views.admin_ver_formulario, name='admin_ver_formulario'),
    
    # APIs
    path('api/validar-curp/', views.api_validar_curp, name='api_validar_curp'),
    path('api/estadisticas/<int:periodo_id>/', views.api_estadisticas_periodo, name='api_estadisticas_periodo'),
]