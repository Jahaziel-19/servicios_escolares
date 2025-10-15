from django.urls import path
from . import views

app_name = 'formbuilder'

urlpatterns = [
    path('', views.lista_formularios, name='listar_formularios'),
    path('formulario/crear/', views.crear_formulario, name='crear_formulario'),
    path('formulario/<int:formulario_id>/editar/', views.editar_formulario, name='editar_formulario'),
    path('formulario/<int:formulario_id>/eliminar/', views.eliminar_formulario, name='eliminar_formulario'),
    path('formulario/<int:formulario_id>/responder/', views.responder_formulario, name='responder_formulario'),
    path('formulario/<int:formulario_id>/respuestas/', views.ver_respuestas, name='ver_respuestas'),
    path('formulario/importar/', views.importar_formulario, name='importar_formulario'),
    path('formulario/<int:formulario_id>/exportar/', views.exportar_formulario, name='exportar_formulario'),
    path('gracias/', views.gracias, name='gracias'),
    path('formulario/creado/<int:formulario_id>/', views.formulario_creado, name='formulario_creado'),
]
