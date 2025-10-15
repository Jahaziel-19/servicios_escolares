from django.urls import path, include
from rest_framework import routers
from rest_framework.routers import DefaultRouter
from . import views
from . import views_inscripcion_simple
from . import views_reinscripcion
from . import views_auth

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
    
    # Gestión de alumnos por servicios escolares
    path('alumnos/gestion/', views.gestion_alumnos, name='gestion_alumnos'),
    
    # Inscripciones
    path('inscripcion/nueva/', views.inscripcion_nueva, name='inscripcion_nueva'),
    path('inscripcion/crear/', views.inscripcion_crear, name='inscripcion_crear'),
    path('inscripcion/<int:inscripcion_id>/documento/', views.generar_documento_inscripcion, name='generar_documento_inscripcion'),
    
    # Sistema de Inscripciones Simple
    path('inscripciones/', views_inscripcion_simple.inscripcion_list_view, name='inscripcion_list'),
    path('inscripciones/nueva/', views_inscripcion_simple.inscripcion_simple_view, name='inscripcion_simple'),
    path('inscripciones/<int:pk>/', views_inscripcion_simple.inscripcion_detail_view, name='inscripcion_detail'),
    path('inscripciones/<int:pk>/cambiar-estado/', views_inscripcion_simple.cambiar_estado_inscripcion, name='cambiar_estado_inscripcion'),
    path('inscripciones/<int:pk>/crear-alumno/', views_inscripcion_simple.crear_alumno_desde_inscripcion, name='crear_alumno_desde_inscripcion'),
    path('inscripciones/dashboard/', views_inscripcion_simple.dashboard_inscripciones, name='dashboard_inscripciones'),
    
    # Reinscripciones
    path('reinscripcion/nueva/', views.reinscripcion_nueva, name='reinscripcion_nueva'),
    path('reinscripcion/crear/', views.reinscripcion_crear, name='reinscripcion_crear'),
    path('reinscripcion/<int:reinscripcion_id>/documento/', views.generar_documento_reinscripcion, name='generar_documento_reinscripcion'),
    
    # Gestión de reinscripciones
    path('reinscripciones/', views_reinscripcion.listar_reinscripciones, name='reinscripciones_listar'),
    path('reinscripcion/<int:reinscripcion_id>/', views_reinscripcion.detalle_reinscripcion, name='reinscripcion_detalle'),
    path('reinscripcion/<int:reinscripcion_id>/aprobar/', views_reinscripcion.aprobar_reinscripcion, name='reinscripcion_aprobar'),
    path('reinscripcion/<int:reinscripcion_id>/aplicar/', views_reinscripcion.aplicar_reinscripcion, name='reinscripcion_aplicar'),
    path('reinscripcion/<int:reinscripcion_id>/rechazar/', views_reinscripcion.rechazar_reinscripcion, name='reinscripcion_rechazar'),
    
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
    
    # Gestión de trámites por servicios escolares
    
    # ========== AUTENTICACIÓN DE ALUMNOS ==========
    # Sistema de login y portal para estudiantes
    path('auth/login/', views_auth.alumno_login_view, name='alumno_login'),
    path('auth/logout/', views_auth.alumno_logout_view, name='alumno_logout'),
    path('auth/dashboard/', views_auth.alumno_dashboard_view, name='alumno_dashboard'),
    path('auth/calificaciones/', views_auth.alumno_calificaciones_view, name='alumno_calificaciones'),
    path('auth/tramites/', views_auth.alumno_tramites_view, name='alumno_tramites'),
    path('auth/perfil/', views_auth.alumno_perfil_view, name='alumno_perfil'),
 
]

