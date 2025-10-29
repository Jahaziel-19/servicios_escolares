from django.urls import path, include
from rest_framework import routers
from rest_framework.routers import DefaultRouter
from . import views
# from . import views_inscripcion_simple
from . import views_inscripciones_panel
from . import views_auth
from . import views_inscripcion_nueva
from . import views_inscripcion_publico
from . import views_periodos
from . import views_reinscripcion

router = DefaultRouter()
router.register(r'ciclo_escolar', views.PeriodoEscolarViewSet)
router.register(r'carreras', views.CarreraViewSet)
router.register(r'materias', views.MateriaViewSet)
router.register(r'grupos', views.GrupoViewSet)
router.register(r'docentes', views.DocenteViewSet)
router.register(r'planes', views.PlanEstudioViewSet) 
router.register(r'tramites', views.TramiteViewSet)

app_name = 'datos_academicos'

urlpatterns = [
    #path('', views.DatosAcademicosView.as_view(), name='datos'),
    
    # API para obtener datos de alumnos (ANTES del router para evitar conflictos)
    path('api/alumnos/<int:pk>/', views.alumno_detail_api, name='alumno_detail_api'),
    path('api/alumnos/', views.api_alumno_list, name='api_alumno_list'),
    path('api/materias/', views.api_materia_list, name='api_materia_list'),
    
    path('api/', include(router.urls)),
    
    # Rutas de servicios escolares
    
    path('dashboard/', views.dashboard, name="dashboard"),

    # Panel administrativo de Inscripciones (estilo Admisión)
    path('inscripciones/panel/', views_inscripciones_panel.inscripciones_panel_admin, name='inscripciones_panel_admin'),
    # Listado y detalle de Inscripción Nueva (públicas)
    path('inscripciones/publicas/', views_inscripciones_panel.inscripciones_publicas_listar, name='inscripciones_publicas_listar'),
    path('inscripciones/publicas/<int:pk>/', views_inscripciones_panel.inscripcion_publica_detalle, name='inscripcion_publica_detalle'),

    # Reinscripción (panel y flujo interno)
    path('reinscripcion/', views_reinscripcion.reinscripcion_panel, name='reinscripcion_panel'),
    path('reinscripcion/iniciar/', views_reinscripcion.reinscripcion_iniciar_form, name='reinscripcion_iniciar_form'),
    path('reinscripcion/<int:alumno_id>/iniciar/', views_reinscripcion.reinscripcion_iniciar, name='reinscripcion_iniciar'),
    path('reinscripcion/<int:reins_id>/', views_reinscripcion.reinscripcion_detalle, name='reinscripcion_detalle'),
    path('reinscripcion/<int:reins_id>/validar/documentos/', views_reinscripcion.reinscripcion_validar_documentos, name='reinscripcion_validar_documentos'),
    path('reinscripcion/<int:reins_id>/validar/pagos/', views_reinscripcion.reinscripcion_validar_pagos, name='reinscripcion_validar_pagos'),
    path('reinscripcion/<int:reins_id>/asignar/materias/', views_reinscripcion.reinscripcion_asignar_materias, name='reinscripcion_asignar_materias'),
    path('reinscripcion/<int:reins_id>/eliminar/item/<int:item_id>/', views_reinscripcion.reinscripcion_eliminar_materia_item, name='reinscripcion_eliminar_materia_item'),
    path('reinscripcion/<int:reins_id>/confirmar/', views_reinscripcion.reinscripcion_confirmar, name='reinscripcion_confirmar'),
    path('reinscripcion/<int:reins_id>/pago/registrar/', views_reinscripcion.reinscripcion_registrar_pago, name='reinscripcion_registrar_pago'),
    path('reinscripcion/<int:reins_id>/carga/pdf/', views_reinscripcion.reinscripcion_subir_carga_pdf, name='reinscripcion_subir_carga_pdf'),

    # (Reinscripción removida temporalmente)
    
    # Gestión de alumnos por servicios escolares
    path('alumnos/gestion/', views.gestion_alumnos, name='gestion_alumnos'),
    
    # Nuevo Proceso de Inscripción (multi-pasos)
    path('inscripcion-nueva/inicio/', views_inscripcion_nueva.inicio, name='inscripcion_nueva_inicio'),
    path('inscripcion-nueva/paso/<int:paso>/', views_inscripcion_nueva.paso, name='inscripcion_nueva_paso'),
    path('inscripcion-nueva/resumen/', views_inscripcion_nueva.resumen, name='inscripcion_nueva_resumen'),
    path('inscripcion-nueva/confirmacion/<str:folio>/', views_inscripcion_nueva.confirmacion, name='inscripcion_nueva_confirmacion'),

    # Flujo público de Inscripción (similar a Admisión)
    path('inscripcion-publico/inicio/', views_inscripcion_publico.inscripcion_publico_inicio, name='inscripcion_publico_inicio'),
    path('inscripcion-publico/<str:folio>/paso/<int:paso>/', views_inscripcion_publico.inscripcion_publico_paso, name='inscripcion_publico_paso'),
    path('inscripcion-publico/<str:folio>/resumen/', views_inscripcion_publico.inscripcion_publico_resumen, name='inscripcion_publico_resumen'),
    path('inscripcion-publico/confirmacion/<str:folio>/', views_inscripcion_publico.inscripcion_publico_confirmacion, name='inscripcion_publico_confirmacion'),
    
    # AJAX
    path('ajax/buscar-alumno/', views.buscar_alumno_ajax, name='buscar_alumno_ajax'),
    path('alumnos/', views.AlumnoListView.as_view(), name='alumno_list'),
    path('alumnos/nuevo/', views.AlumnoCreateView.as_view(), name='alumno_nuevo'),
    path('alumnos/<int:pk>/', views.AlumnoDetailView.as_view(), name='alumno_detalle'),
    path('alumnos/<int:pk>/editar/', views.AlumnoUpdateView.as_view(), name='alumno_editar'),
    path('alumnos/<int:pk>/eliminar/', views.AlumnoDeleteView.as_view(), name='alumno_eliminar'),
    
    # Gestión de calificaciones
    path('calificaciones/', views.gestion_calificaciones, name='gestion_calificaciones'),
    path('calificaciones/lista/', views.CalificacionListView.as_view(), name='calificacion_list'),
    path('calificaciones/nueva/', views.calificacion_create, name='calificacion_create'),
    path('calificaciones/<int:pk>/', views.calificacion_detail, name='calificacion_detail'),
    path('calificaciones/<int:pk>/editar/', views.calificacion_edit, name='calificacion_edit'),
    
    # Gestión de materias
    path('materias/', views.gestion_materias, name='gestion_materias'),
    path('materias/lista/', views.MateriaListView.as_view(), name='materia_list'),
    path('materias/nueva/', views.materia_create, name='materia_create'),
    path('materias/<int:pk>/', views.materia_detail, name='materia_detail'),
    path('materias/<int:pk>/editar/', views.materia_edit, name='materia_edit'),
    
    # Gestión de planes de estudio
    path('planes/', views.plan_estudio_list, name='plan_estudio_list'),
    path('planes/nuevo/', views.plan_estudio_create, name='plan_estudio_create'),
    path('planes/<int:pk>/', views.plan_estudio_detail, name='plan_estudio_detail'),
    path('planes/<int:pk>/editar/', views.plan_estudio_edit, name='plan_estudio_edit'),

    # Periodos
    path('periodos/', views_periodos.periodos_panel, name='periodos_panel'),
    path('periodos/lista/', views_periodos.periodos_listar, name='periodos_listar'),
    path('periodos/editar/', views_periodos.periodo_editar, name='periodo_editar'),
    path('periodos/<int:periodo_id>/editar/', views_periodos.periodo_editar, name='periodo_editar'),
    path('periodos/<int:periodo_id>/toggle-activo/', views_periodos.periodo_toggle_activo, name='periodo_toggle_activo'),
    path('periodos/transicion/aplicar/', views_periodos.periodo_aplicar_transicion, name='periodo_aplicar_transicion'),
    
    
    # ========== AUTENTICACIÓN DE ALUMNOS ==========
    # Sistema de login y portal para estudiantes
    path('auth/login/', views_auth.alumno_login_view, name='alumno_login'),
    path('auth/logout/', views_auth.alumno_logout_view, name='alumno_logout'),
    path('auth/dashboard/', views_auth.alumno_dashboard_view, name='alumno_dashboard'),
    path('auth/calificaciones/', views_auth.alumno_calificaciones_view, name='alumno_calificaciones'),
    path('auth/tramites/', views_auth.alumno_tramites_view, name='alumno_tramites'),
    path('auth/perfil/', views_auth.alumno_perfil_view, name='alumno_perfil'),

    # ========== AUTENTICACIÓN SERVICIOS ESCOLARES ==========
    path('servicios/login/', views_auth.servicios_login_view, name='servicios_login'),
 
]

