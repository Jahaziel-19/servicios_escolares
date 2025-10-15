from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from datetime import date, datetime
from .models import Alumno, PeriodoEscolar, Carrera


class Inscripcion(models.Model):
    """
    Modelo para el proceso de inscripción de alumnos
    Basado en el archivo Excel '01 Inscripcion IEME-ILOG 2025.xlsx'
    """
    TIPO_INSCRIPCION_CHOICES = [
        ('Nuevo Ingreso', 'Nuevo Ingreso'),
        ('Reingreso', 'Reingreso'),
        ('Convalidación', 'Convalidación'),
        ('Traslado', 'Traslado'),
        ('Equivalencia', 'Equivalencia'),
    ]
    
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('En Proceso', 'En Proceso'),
        ('Aprobada', 'Aprobada'),
        ('Rechazada', 'Rechazada'),
        ('Completada', 'Completada'),
    ]
    
    MODALIDAD_CHOICES = [
        ('A', 'A (Presencial)'),
        ('B', 'B (Sabatino)'),
    ]
    
    # Información básica de la inscripción
    folio = models.CharField(max_length=20, unique=True, blank=True)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    periodo_escolar = models.ForeignKey(PeriodoEscolar, on_delete=models.CASCADE, related_name='inscripciones')
    tipo_inscripcion = models.CharField(max_length=20, choices=TIPO_INSCRIPCION_CHOICES, default='Nuevo Ingreso')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    usuario_aprobacion = models.CharField(max_length=150, null=True, blank=True)
    
    # Datos del aspirante/alumno
    nombre = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=50)
    apellido_materno = models.CharField(max_length=50, blank=True, null=True)
    curp = models.CharField(max_length=18, unique=True)
    fecha_nacimiento = models.DateField()
    sexo = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Femenino')])
    estado_civil = models.CharField(max_length=20, choices=[
        ('Soltero', 'Soltero'), 
        ('Casado', 'Casado'), 
        ('Divorciado', 'Divorciado'), 
        ('Viudo', 'Viudo')
    ], default='Soltero')
    
    # Datos de contacto
    telefono = models.CharField(max_length=15)
    email = models.EmailField()
    
    # Datos de domicilio
    calle = models.CharField(max_length=100)
    numero_exterior = models.CharField(max_length=10)
    numero_interior = models.CharField(max_length=10, blank=True, null=True)
    colonia = models.CharField(max_length=100)
    municipio = models.CharField(max_length=100)
    estado = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=5)
    zona_procedencia = models.CharField(max_length=100, choices=[('Urbana', 'Urbana'), ('Rural', 'Rural')])
    
    # Datos académicos
    carrera_solicitada = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name='inscripciones_solicitadas')
    modalidad = models.CharField(max_length=1, choices=MODALIDAD_CHOICES, default='A')
    semestre_ingreso = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(19)])
    
    # Datos de procedencia académica
    escuela_procedencia = models.CharField(max_length=200)
    promedio_bachillerato = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    año_egreso_bachillerato = models.IntegerField(validators=[MinValueValidator(1990), MaxValueValidator(date.today().year)])
    
    # Documentos requeridos (campos booleanos para marcar si se entregaron)
    acta_nacimiento = models.BooleanField(default=False, verbose_name="Acta de Nacimiento")
    certificado_bachillerato = models.BooleanField(default=False, verbose_name="Certificado de Bachillerato")
    curp_documento = models.BooleanField(default=False, verbose_name="CURP")
    fotografias = models.BooleanField(default=False, verbose_name="Fotografías")
    comprobante_domicilio = models.BooleanField(default=False, verbose_name="Comprobante de Domicilio")
    
    # Datos adicionales
    observaciones = models.TextField(blank=True, null=True)
    alumno_creado = models.ForeignKey(Alumno, on_delete=models.SET_NULL, null=True, blank=True, related_name='inscripcion_origen')
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    usuario_registro = models.CharField(max_length=100, blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if not self.folio:
            # Generar folio automático
            año = self.fecha_solicitud.year if self.fecha_solicitud else date.today().year
            ultimo_folio = Inscripcion.objects.filter(
                fecha_solicitud__year=año
            ).count() + 1
            self.folio = f"INS-{año}-{ultimo_folio:04d}"
        super().save(*args, **kwargs)
    
    def documentos_completos(self):
        """Verifica si todos los documentos requeridos están completos"""
        return all([
            self.acta_nacimiento,
            self.certificado_bachillerato,
            self.curp_documento,
            self.fotografias,
            self.comprobante_domicilio
        ])
    
    def crear_alumno(self):
        """Crea un registro de Alumno basado en los datos de inscripción"""
        if self.estado != 'Aprobada' or self.alumno_creado:
            return None
            
        # Generar matrícula
        año = str(date.today().year)[-2:]
        carrera_codigo = self.carrera_solicitada.clave[:3].upper()
        ultimo_numero = Alumno.objects.filter(
            matricula__startswith=f"{año}{carrera_codigo}"
        ).count() + 1
        matricula = f"{año}{carrera_codigo}{ultimo_numero:03d}"
        
        alumno = Alumno.objects.create(
            matricula=matricula,
            nombre=self.nombre,
            apellido_paterno=self.apellido_paterno,
            apellido_materno=self.apellido_materno,
            carrera=self.carrera_solicitada,
            semestre=self.semestre_ingreso,
            modalidad=self.modalidad,
            fecha_ingreso=date.today(),
            estatus='Inscrito',
            division_estudio=self.tipo_inscripcion,
            curp=self.curp,
            email=self.email,
            fecha_nacimiento=self.fecha_nacimiento,
            sexo=self.sexo,
            estado_civil=self.estado_civil,
            telefono=self.telefono,
            calle=self.calle,
            numero_exterior=self.numero_exterior,
            numero_interior=self.numero_interior,
            colonia=self.colonia,
            municipio=self.municipio,
            estado=self.estado,
            codigo_postal=self.codigo_postal,
            zona_procedencia=self.zona_procedencia,
        )
        
        self.alumno_creado = alumno
        self.estado = 'Completada'
        self.save()
        
        return alumno
    
    class Meta:
        verbose_name = 'Inscripción'
        verbose_name_plural = 'Inscripciones'
        ordering = ['-fecha_solicitud']
    
    def __str__(self):
        return f"{self.folio} - {self.nombre} {self.apellido_paterno} ({self.carrera_solicitada.clave})"


class Reinscripcion(models.Model):
    """
    Modelo para el proceso de reinscripción de alumnos
    Relacionado con el proceso de producto no conforme
    """
    MOTIVO_CHOICES = [
        ('Baja Temporal', 'Baja Temporal'),
        ('Cambio de Modalidad', 'Cambio de Modalidad'),
        ('Cambio de Carrera', 'Cambio de Carrera'),
        ('Cambio de Semestre', 'Cambio de Semestre'),
        ('Reactivación', 'Reactivación'),
        ('Producto No Conforme', 'Producto No Conforme'),
    ]
    
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('En Revisión', 'En Revisión'),
        ('Aprobada', 'Aprobada'),
        ('Rechazada', 'Rechazada'),
        ('Completada', 'Completada'),
    ]
    
    # Información básica
    folio = models.CharField(max_length=20, unique=True, blank=True)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name='reinscripciones')
    periodo_escolar = models.ForeignKey(PeriodoEscolar, on_delete=models.CASCADE, related_name='reinscripciones')
    
    # Datos de la reinscripción
    motivo = models.CharField(max_length=30, choices=MOTIVO_CHOICES)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')
    
    # Datos académicos actuales
    semestre_actual = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(19)])
    promedio_actual = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    creditos_aprobados = models.IntegerField(default=0)
    
    # Cambios solicitados (si aplica)
    nueva_carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, null=True, blank=True, related_name='reinscripciones_destino')
    nueva_modalidad = models.CharField(max_length=1, choices=[('A', 'A (Presencial)'), ('B', 'B (Sabatino)')], blank=True, null=True)
    nuevo_semestre = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(19)])
    
    # Documentos adicionales requeridos
    carta_motivos = models.FileField(upload_to='reinscripciones/cartas_motivos/', null=True, blank=True, verbose_name="Carta de Motivos")
    documentos_actualizados = models.FileField(upload_to='reinscripciones/documentos_actualizados/', null=True, blank=True, verbose_name="Documentos Actualizados")
    comprobante_pago = models.FileField(upload_to='reinscripciones/comprobantes_pago/', null=True, blank=True, verbose_name="Comprobante de Pago")
    
    # Observaciones y seguimiento
    observaciones = models.TextField(blank=True, null=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    usuario_aprobacion = models.CharField(max_length=100, blank=True, null=True)
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    usuario_registro = models.CharField(max_length=100, blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if not self.folio:
            # Generar folio automático
            año = self.fecha_solicitud.year if self.fecha_solicitud else date.today().year
            ultimo_folio = Reinscripcion.objects.filter(
                fecha_solicitud__year=año
            ).count() + 1
            self.folio = f"REINS-{año}-{ultimo_folio:04d}"
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validaciones personalizadas del modelo"""
        super().clean()
        
        # Validar que no existan reinscripciones pendientes para el mismo alumno en el mismo período
        if self.alumno and self.periodo_escolar:
            reinscripciones_existentes = Reinscripcion.objects.filter(
                alumno=self.alumno,
                periodo_escolar=self.periodo_escolar,
                estado__in=['Pendiente', 'En Revisión']
            ).exclude(pk=self.pk if self.pk else None)
            
            if reinscripciones_existentes.exists():
                from django.core.exceptions import ValidationError
                raise ValidationError(
                     f'El alumno {self.alumno.matricula} ya tiene una reinscripción pendiente '
                     f'para el período {self.periodo_escolar}.'
                 )
    
    def aplicar_cambios(self):
        """Aplica los cambios de reinscripción al alumno"""
        if self.estado != 'Aprobada':
            return False
            
        alumno = self.alumno
        
        # Aplicar cambios según el motivo
        if self.nueva_carrera:
            alumno.carrera = self.nueva_carrera
            # Si hay cambio de carrera, actualizar el plan de estudios
            from datos_academicos.models import PlanEstudio
            plan_estudio = PlanEstudio.objects.filter(carrera=self.nueva_carrera).first()
            if plan_estudio:
                alumno.plan_estudio = plan_estudio
            
        if self.nueva_modalidad:
            alumno.modalidad = self.nueva_modalidad
            
        if self.nuevo_semestre:
            alumno.semestre = self.nuevo_semestre
            
        # Actualizar fechas del período activo
        from servicios_escolares.utils import obtener_periodo_activo
        periodo_activo = obtener_periodo_activo()
        if periodo_activo:
            alumno.inicio_semestre = periodo_activo.fecha_inicio
            alumno.fin_semestre = periodo_activo.fecha_fin
            alumno.inicio_vacaciones = periodo_activo.inicio_vacaciones
            alumno.fin_vacaciones = periodo_activo.fin_vacaciones
            
        # Actualizar estatus según el motivo
        if self.motivo == 'Reactivación':
            alumno.estatus = 'Inscrito'
        elif self.motivo == 'Baja Temporal':
            alumno.estatus = 'Baja temporal'
        elif self.motivo == 'Cambio de Semestre':
            alumno.estatus = 'Inscrito'
        elif self.motivo == 'Cambio de Carrera':
            alumno.estatus = 'Inscrito'
        elif self.motivo == 'Cambio de Modalidad':
            alumno.estatus = 'Inscrito'
            
        alumno.save()
        
        # Marcar como completada
        self.estado = 'Completada'
        self.fecha_aprobacion = datetime.now()
        self.save()
        
        return True
    
    class Meta:
        verbose_name = 'Reinscripción'
        verbose_name_plural = 'Reinscripciones'
        ordering = ['-fecha_solicitud']
    
    def __str__(self):
        return f"{self.folio} - {self.alumno.matricula} ({self.motivo})"