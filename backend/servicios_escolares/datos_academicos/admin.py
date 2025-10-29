from django.contrib import admin
from .models import (
    Carrera, 
    Materia, 
    MateriaCarrera,
    #TipoMateria, 
    Alumno, 
    Docente, 
    PeriodoEscolar, 
    Grupo, 
    #AlumnoGrupo,  # Comentado porque no existe en models.py
    PlanEstudio, 
    Tramite,
    Calificacion
)

# Register your models here.

@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ('matricula', 'nombre', 'apellido_paterno', 'carrera', 'semestre', 'estatus', 'email')
    search_fields = ('matricula', 'nombre', 'apellido_paterno', 'apellido_materno', 'email')
    list_filter = ('carrera', 'estatus', 'modalidad', 'division_estudio')
    ordering = ('matricula',)

@admin.register(Docente)
class DocenteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido_paterno', 'apellido_materno', 'email')
    search_fields = ('nombre', 'apellido_paterno', 'apellido_materno', 'email')

@admin.register(PeriodoEscolar)
class PeriodoEscolarAdmin(admin.ModelAdmin):
    list_display = ('ciclo', 'año', 'activo', 'inscripcion_habilitada')
    list_filter = ('ciclo', 'año', 'activo', 'inscripcion_habilitada')
    search_fields = ('ciclo', 'año')

@admin.register(Carrera)
class CarreraAdmin(admin.ModelAdmin):
    list_display = ('clave', 'nombre')
    search_fields = ('clave', 'nombre')

# Inline para manejar la relación MateriaCarrera
class MateriaCarreraInline(admin.TabularInline):
    model = MateriaCarrera
    extra = 1
    fields = ('carrera', 'semestre')
    verbose_name = "Carrera"
    verbose_name_plural = "Carreras donde se imparte"

@admin.register(MateriaCarrera)
class MateriaCarreraAdmin(admin.ModelAdmin):
    list_display = ('materia', 'carrera', 'semestre', 'get_tipo_materia')
    list_filter = ('carrera', 'semestre', 'materia__tipo')
    search_fields = ('materia__nombre', 'materia__clave', 'carrera__nombre')
    ordering = ('carrera', 'semestre', 'materia__nombre')
    
    def get_tipo_materia(self, obj):
        return obj.materia.tipo
    get_tipo_materia.short_description = 'Tipo'

@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ('clave', 'nombre', 'creditos', 'tipo', 'cuenta_promedio', 'es_universal', 'get_carreras_count')
    search_fields = ('nombre', 'clave')
    list_filter = ('tipo', 'cuenta_promedio', 'es_universal', 'creditos')
    inlines = [MateriaCarreraInline]
    
    def get_carreras_count(self, obj):
        return obj.carreras.count()
    get_carreras_count.short_description = 'Núm. Carreras'
    
    # Remover filter_horizontal ya que ahora usamos through
    # filter_horizontal = ('carreras',)

'''
@admin.register(TipoMateria)
class TipoMateriaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)
'''
@admin.register(Tramite)
class TramiteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'clave', 'precio', 'fecha_creacion')
    search_fields = ('nombre', 'clave')

@admin.register(PlanEstudio)
class PlanEstudioAdmin(admin.ModelAdmin):
    list_display = ('clave', 'año', 'carrera')
    search_fields = ('clave', 'año', 'carrera__nombre')
    #filter_horizontal = ('materias',) # Para seleccionar materias de forma más amigable

@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ('carrera', 'semestre', 'modalidad')
    list_filter = ('carrera', 'semestre', 'modalidad')
    search_fields = ('carrera__nombre',)

@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'materia', 'periodo_escolar', 'calificacion', 'creditos', 'acreditacion', 'fecha_registro')
    list_filter = ('periodo_escolar', 'materia', 'acreditacion')
    search_fields = ('alumno__nombre', 'alumno__matricula', 'materia__nombre')
    ordering = ('alumno', 'materia', 'periodo_escolar')
    readonly_fields = ('fecha_registro',)
    
    fieldsets = (
        (None, {
            'fields': ('alumno', 'materia', 'periodo_escolar')
        }),
        ('Detalles de la calificación', {
            'fields': ('calificacion', 'creditos', 'acreditacion', 'observaciones')
        }),
        ('Información adicional', {
            'fields': ('fecha_registro',),
            'description': 'Fecha en que se registró la calificación, campo de solo lectura.'
        }),
    )
# ========== ADMINISTRACIÓN DE REINSCRIPCIONES (ELIMINADA) ==========
# Se removieron modelos y administración relacionados con Reinscripción y CargaAcadémica.

'''
admin.site.register(Carrera)
admin.site.register(Materia)
admin.site.register(TipoMateria)
admin.site.register(Alumno)
admin.site.register(PeriodoEscolar)
admin.site.register(Grupo)
admin.site.register(PlanEstudio)
admin.site.register(Docente)
admin.site.register(Tramite)  
'''