from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from datetime import date, datetime
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Alumno, PeriodoEscolar, Carrera, Materia


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
    """Proceso de reinscripción para alumnos existentes."""
    ESTADOS = [
        ('Borrador', 'Borrador'),
        ('Validacion', 'Validación'),
        ('Pagado', 'Pago Validado'),
        ('Asignado', 'Materias Asignadas'),
        ('Completada', 'Completada'),
        ('Rechazada', 'Rechazada'),
    ]

    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name='reinscripciones')
    periodo_escolar = models.ForeignKey(PeriodoEscolar, on_delete=models.CASCADE, related_name='reinscripciones')
    folio = models.CharField(max_length=20, unique=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Borrador')
    documentos_validados = models.BooleanField(default=False)
    pagos_validados = models.BooleanField(default=False)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_validacion_documentos = models.DateTimeField(null=True, blank=True)
    fecha_validacion_pagos = models.DateTimeField(null=True, blank=True)
    fecha_asignacion_materias = models.DateTimeField(null=True, blank=True)
    fecha_completada = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)
    carga_academica_pdf = models.FileField(upload_to='reinscripciones/carga_pdfs/', null=True, blank=True)

    usuario_registro = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    usuario_ultima_accion = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reinscripciones_modificadas')

    class Meta:
        verbose_name = 'Reinscripción'
        verbose_name_plural = 'Reinscripciones'
        ordering = ['-fecha_solicitud']
        unique_together = ('alumno', 'periodo_escolar')

    def __str__(self):
        return f"REINS-{self.alumno.matricula}-{self.periodo_escolar.año} ({self.estado})"

    def save(self, *args, **kwargs):
        if not self.folio:
            año = timezone.now().year
            contador = Reinscripcion.objects.filter(periodo_escolar__año=año).count() + 1
            self.folio = f"REINS-{año}-{contador:04d}"
        super().save(*args, **kwargs)

    def marcar_documentos_validados(self, usuario: User):
        self.documentos_validados = True
        self.fecha_validacion_documentos = timezone.now()
        self.estado = 'Validacion'
        self.usuario_ultima_accion = usuario
        self.save()

    def marcar_pagos_validados(self, usuario: User):
        self.pagos_validados = True
        self.fecha_validacion_pagos = timezone.now()
        self.estado = 'Pagado' if self.documentos_validados else 'Validacion'
        self.usuario_ultima_accion = usuario
        self.save()

    def marcar_materias_asignadas(self, usuario: User):
        self.fecha_asignacion_materias = timezone.now()
        self.estado = 'Asignado'
        self.usuario_ultima_accion = usuario
        self.save()

    def confirmar(self, usuario: User):
        """Completa la reinscripción y actualiza datos del alumno."""
        # Política actual: no exigir validación previa de documentos/pagos.
        # Se permite confirmar directamente.

        alumno = self.alumno
        if alumno.division_estudio == 'Nuevo Ingreso':
            alumno.division_estudio = 'Reingreso'
        alumno.estatus = 'Inscrito'
        alumno.semestre = (alumno.semestre or 0) + 1

        periodo = self.periodo_escolar
        alumno.inicio_semestre = periodo.fecha_inicio or alumno.inicio_semestre
        alumno.fin_semestre = periodo.fecha_fin or alumno.fin_semestre
        alumno.inicio_vacaciones = periodo.inicio_vacaciones or alumno.inicio_vacaciones
        alumno.fin_vacaciones = periodo.fin_vacaciones or alumno.fin_vacaciones
        alumno.save()

        self.estado = 'Completada'
        self.fecha_completada = timezone.now()
        self.usuario_ultima_accion = usuario
        self.save()

        ReinscripcionLog.objects.create(
            reinscripcion=self,
            alumno=alumno,
            usuario=usuario,
            accion='Confirmar',
            detalles=f'Reinscripción confirmada. Semestre actualizado a {alumno.semestre}.'
        )


class ReinscripcionLog(models.Model):
    """Registro histórico de acciones de reinscripción."""
    reinscripcion = models.ForeignKey(Reinscripcion, on_delete=models.CASCADE, related_name='logs')
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name='reinscripcion_logs')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=50)
    detalles = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log de Reinscripción'
        verbose_name_plural = 'Logs de Reinscripción'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.fecha:%Y-%m-%d %H:%M} - {self.accion} ({self.alumno.matricula})"


class ReinscripcionPago(models.Model):
    """Registro de pagos/recibos durante la reinscripción."""
    reinscripcion = models.ForeignKey(Reinscripcion, on_delete=models.CASCADE, related_name='pagos')
    concepto = models.CharField(max_length=120)
    monto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    comprobante = models.FileField(upload_to='reinscripciones/pagos/', null=True, blank=True)
    condonado = models.BooleanField(default=False)
    motivo_condonacion = models.TextField(blank=True, null=True)
    validado = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'Pago de Reinscripción'
        verbose_name_plural = 'Pagos de Reinscripción'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"{self.concepto} ({'Condonado' if self.condonado else 'Adjunto'})"


class CargaAcademica(models.Model):
    """Carga académica del alumno para un periodo escolar."""
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name='cargas_academicas')
    periodo_escolar = models.ForeignKey(PeriodoEscolar, on_delete=models.CASCADE, related_name='cargas_academicas')
    estado = models.CharField(max_length=20, choices=[('Borrador', 'Borrador'), ('Confirmada', 'Confirmada')], default='Borrador')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)
    confirmada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('alumno', 'periodo_escolar')
        verbose_name = 'Carga Académica'
        verbose_name_plural = 'Cargas Académicas'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Carga {self.alumno.matricula} - {self.periodo_escolar} ({self.estado})"

    @property
    def total_creditos(self):
        return sum(item.materia.creditos for item in self.items.select_related('materia'))

    @property
    def materias_adelantadas(self):
        return self.items.filter(adelantada=True).count()


class CargaAcademicaItem(models.Model):
    """Materia incluida en una carga académica."""
    carga = models.ForeignKey(CargaAcademica, on_delete=models.CASCADE, related_name='items')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    adelantada = models.BooleanField(default=False, help_text="Materia asignada por adelantado respecto al mapa curricular")
    semestre_asignado = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(19)])
    notas = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('carga', 'materia')
        verbose_name = 'Materia de Carga'
        verbose_name_plural = 'Materias de Carga'

    def __str__(self):
        return f"{self.materia.nombre} ({'Adelantada' if self.adelantada else 'Regular'})"