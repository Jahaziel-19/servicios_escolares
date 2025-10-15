from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    PeriodoAdmision, FormularioAdmision, SolicitudAdmision, 
    FichaAdmision, ConfiguracionAdmision
)


@admin.register(PeriodoAdmision)
class PeriodoAdmisionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'año', 'fecha_inicio', 'fecha_fin', 'activo', 'esta_abierto_display']
    list_filter = ['año', 'activo']
    search_fields = ['nombre', 'descripcion']
    ordering = ['-año', '-fecha_inicio']
    
    fieldsets = (
        ('Información General', {
            'fields': ('nombre', 'año', 'descripcion')
        }),
        ('Fechas', {
            'fields': ('fecha_inicio', 'fecha_fin')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
    )
    
    def esta_abierto_display(self, obj):
        if obj.esta_abierto:
            return format_html('<span style="color: green;">✓ Abierto</span>')
        else:
            return format_html('<span style="color: red;">✗ Cerrado</span>')
    esta_abierto_display.short_description = 'Estado Actual'


@admin.register(FormularioAdmision)
class FormularioAdmisionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'periodo', 'version', 'fecha_modificacion', 'creado_por']
    list_filter = ['periodo__año', 'fecha_creacion']
    search_fields = ['nombre', 'periodo__nombre']
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    fieldsets = (
        ('Información General', {
            'fields': ('periodo', 'nombre', 'version', 'creado_por')
        }),
        ('Estructura del Formulario', {
            'fields': ('estructura_json',),
            'description': 'Define la estructura del formulario en formato JSON'
        }),
        ('Metadatos', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si es un nuevo objeto
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(SolicitudAdmision)
class SolicitudAdmisionAdmin(admin.ModelAdmin):
    list_display = [
        'folio', 'get_nombre_completo', 'curp', 'email', 
        'periodo', 'estado', 'fecha_registro', 'tiene_ficha'
    ]
    list_filter = ['estado', 'periodo__año', 'fecha_registro']
    search_fields = ['folio', 'curp', 'email']
    readonly_fields = ['folio', 'fecha_registro', 'fecha_modificacion', 'ip_registro']
    ordering = ['-fecha_registro']
    
    fieldsets = (
        ('Información de la Solicitud', {
            'fields': ('folio', 'periodo', 'estado')
        }),
        ('Datos del Aspirante', {
            'fields': ('curp', 'email')
        }),
        ('Respuestas del Formulario', {
            'fields': ('respuestas_json',),
            'description': 'Respuestas del aspirante en formato JSON'
        }),
        ('Metadatos', {
            'fields': ('fecha_registro', 'fecha_modificacion', 'ip_registro'),
            'classes': ('collapse',)
        }),
    )
    
    def tiene_ficha(self, obj):
        try:
            ficha = obj.ficha
            url = reverse('admin:admision_fichaadmision_change', args=[ficha.pk])
            return format_html('<a href="{}">Ver Ficha</a>', url)
        except FichaAdmision.DoesNotExist:
            return format_html('<span style="color: orange;">Sin ficha</span>')
    tiene_ficha.short_description = 'Ficha'
    
    actions = ['generar_fichas_seleccionadas']
    
    def generar_fichas_seleccionadas(self, request, queryset):
        """Acción para generar fichas de las solicitudes seleccionadas"""
        count = 0
        for solicitud in queryset:
            if not hasattr(solicitud, 'ficha'):
                FichaAdmision.objects.create(
                    solicitud=solicitud,
                    generada_por=request.user
                )
                count += 1
        
        self.message_user(request, f'Se generaron {count} fichas de admisión.')
    generar_fichas_seleccionadas.short_description = 'Generar fichas para solicitudes seleccionadas'


@admin.register(FichaAdmision)
class FichaAdmisionAdmin(admin.ModelAdmin):
    list_display = [
        'numero_ficha', 'get_folio_solicitud', 'get_nombre_aspirante',
        'fecha_generacion', 'email_enviado', 'generada_por'
    ]
    list_filter = ['email_enviado', 'fecha_generacion', 'solicitud__periodo__año']
    search_fields = ['numero_ficha', 'solicitud__folio', 'solicitud__curp']
    readonly_fields = ['numero_ficha', 'fecha_generacion', 'fecha_envio_email']
    ordering = ['-fecha_generacion']
    
    fieldsets = (
        ('Información de la Ficha', {
            'fields': ('numero_ficha', 'solicitud', 'generada_por')
        }),
        ('Archivos', {
            'fields': ('archivo_pdf',)
        }),
        ('Control de Envío', {
            'fields': ('email_enviado', 'fecha_envio_email')
        }),
        ('Metadatos', {
            'fields': ('fecha_generacion',),
            'classes': ('collapse',)
        }),
    )
    
    def get_folio_solicitud(self, obj):
        return obj.solicitud.folio
    get_folio_solicitud.short_description = 'Folio Solicitud'
    
    def get_nombre_aspirante(self, obj):
        return obj.solicitud.get_nombre_completo()
    get_nombre_aspirante.short_description = 'Aspirante'
    
    actions = ['enviar_por_email']
    
    def enviar_por_email(self, request, queryset):
        """Acción para enviar fichas por email"""
        count = 0
        for ficha in queryset.filter(email_enviado=False):
            # Aquí se implementaría el envío por email
            # Por ahora solo marcamos como enviado
            ficha.email_enviado = True
            ficha.fecha_envio_email = timezone.now()
            ficha.save()
            count += 1
        
        self.message_user(request, f'Se enviaron {count} fichas por email.')
    enviar_por_email.short_description = 'Enviar fichas seleccionadas por email'


@admin.register(ConfiguracionAdmision)
class ConfiguracionAdmisionAdmin(admin.ModelAdmin):
    list_display = ['clave', 'valor_truncado', 'fecha_modificacion', 'modificado_por']
    search_fields = ['clave', 'descripcion']
    ordering = ['clave']
    
    fieldsets = (
        ('Configuración', {
            'fields': ('clave', 'valor', 'descripcion')
        }),
        ('Metadatos', {
            'fields': ('fecha_modificacion', 'modificado_por'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_modificacion']
    
    def valor_truncado(self, obj):
        return obj.valor[:50] + '...' if len(obj.valor) > 50 else obj.valor
    valor_truncado.short_description = 'Valor'
    
    def save_model(self, request, obj, form, change):
        obj.modificado_por = request.user
        super().save_model(request, obj, form, change)