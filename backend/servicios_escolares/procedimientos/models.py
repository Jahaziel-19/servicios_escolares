from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from datos_academicos.models import Alumno, PeriodoEscolar

class Tramite(models.Model):
    TIPO_CHOICES = [
        ('constancia', 'Constancia'),
        ('kardex', 'Kardex'),
        ('boleta', 'Boleta'),
        ('acta_residencia', 'Acta de Residencia'),
        # Agrega otros tipos según sea necesario
    ]
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name='tramites')
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_procesado = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(max_length=20, default='Pendiente')  # Pendiente, Procesado, Cancelado, etc.
    plantilla = models.ForeignKey('docsbuilder.Plantilla', on_delete=models.SET_NULL, null=True, blank=True)
    observaciones = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.alumno} - {self.estado}"

class Boleta(models.Model):
    """Modelo para gestionar boletas de calificaciones por periodo"""
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name='boletas')
    periodo_escolar = models.ForeignKey(PeriodoEscolar, on_delete=models.CASCADE, related_name='boletas')
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    generado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ('alumno', 'periodo_escolar')
        verbose_name = 'Boleta de Calificaciones'
        verbose_name_plural = 'Boletas de Calificaciones'
        ordering = ['-fecha_generacion']
    
    def __str__(self):
        return f"Boleta {self.alumno.matricula} - {self.periodo_escolar}"
    
    def get_calificaciones(self):
        """Obtiene las calificaciones del alumno para el periodo específico"""
        return self.alumno.calificaciones.filter(
            periodo_escolar=self.periodo_escolar,
            materia__materiacarrera__carrera=self.alumno.carrera
        ).select_related('materia').order_by('materia__clave')
    
    def calcular_promedio_periodo(self):
        """Calcula el promedio específico para este periodo"""
        calificaciones = self.get_calificaciones().filter(materia__cuenta_promedio=True)
        if not calificaciones.exists():
            return 0.0
        
        total_calificaciones = sum(c.calificacion for c in calificaciones if c.calificacion)
        return round(total_calificaciones / calificaciones.count(), 2) if calificaciones.count() > 0 else 0.0

class Bitacora(models.Model):
    tramite = models.ForeignKey(Tramite, on_delete=models.CASCADE, related_name='bitacoras')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    accion = models.CharField(max_length=100)  # Ej: "Creó trámite", "Generó documento"
    comentario = models.TextField(blank=True)

    def __str__(self):
        return f"{self.tramite} - {self.accion} - {self.fecha.strftime('%Y-%m-%d %H:%M')}"

class Proceso(models.Model):
    TIPO_PROCESO_CHOICES = [
        ('ADMISION', 'Admisión'),
        ('TITULACION', 'Titulación'),
        ('INSCRIPCION', 'Inscripción'),
        ('REINSCRIPCION', 'Reinscripción'),
        ('OTRO', 'Otro'),
    ]

    nombre = models.CharField(max_length=100, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPO_PROCESO_CHOICES, default='OTRO')
    descripcion = models.TextField(blank=True, null=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=True)

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name = "Proceso"
        verbose_name_plural = "Procesos"

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"

    def esta_activo(self):
        """Devuelve True si la fecha actual está dentro del rango del proceso y está marcado como activo"""
        from django.utils import timezone
        hoy = timezone.now().date()
        return self.activo and self.fecha_inicio <= hoy <= self.fecha_fin


class Residencia(models.Model):
    ESTADO_CHOICES = [
        ('SOLICITADA', 'Solicitada'),
        ('EN_CURSO', 'En curso'),
        ('CONCLUIDA', 'Concluida'),
        ('APROBADA', 'Aprobada'),
        ('REPROBADA', 'Reprobada'),
    ]

    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name='residencias')
    periodo_escolar = models.ForeignKey(PeriodoEscolar, on_delete=models.SET_NULL, null=True, blank=True, related_name='residencias')
    empresa = models.CharField(max_length=200)
    proyecto = models.CharField(max_length=200)
    asesor_interno = models.CharField(max_length=150)
    asesor_externo = models.CharField(max_length=150, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    horas_programadas = models.PositiveIntegerField(null=True, blank=True)
    horas_cumplidas = models.PositiveIntegerField(default=0)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='SOLICITADA')

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creado']
        verbose_name = 'Residencia Profesional'
        verbose_name_plural = 'Residencias Profesionales'
        unique_together = ('alumno', 'proyecto')

    def __str__(self):
        return f"{self.alumno.matricula} - {self.empresa} - {self.proyecto}"

    def avance_horas(self):
        if not self.horas_programadas or self.horas_programadas == 0:
            return 0
        return round((self.horas_cumplidas / self.horas_programadas) * 100, 2)


class ResidenciaBitacoraEntry(models.Model):
    residencia = models.ForeignKey(Residencia, on_delete=models.CASCADE, related_name='bitacora')
    fecha = models.DateField()
    actividad = models.TextField()
    horas = models.PositiveIntegerField(default=0)
    evidencia = models.CharField(max_length=255, blank=True)
    hoja = models.CharField(max_length=100, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-creado']
        verbose_name = 'Entrada de Bitácora de Residencia'
        verbose_name_plural = 'Entradas de Bitácora de Residencia'

    def __str__(self):
        return f"{self.residencia.alumno.matricula} - {self.fecha} - {self.horas}h"
