from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.conf import settings

from .models import Carrera, PeriodoEscolar  # Reusar modelos existentes


def generar_folio(prefix: str = 'INS') -> str:
    """Genera un folio legible y único."""
    return f"{prefix}-{timezone.now().strftime('%Y%m%d')}-{get_random_string(6).upper()}"


class InscripcionNueva(models.Model):
    ESTADO_CHOICES = [
        ('Borrador', 'Borrador'),
        ('Enviado', 'Enviado'),
        ('En Revisión', 'En Revisión'),
        ('Aprobada', 'Aprobada'),
        ('Rechazada', 'Rechazada'),
        ('Completada', 'Completada'),
    ]

    folio = models.CharField(max_length=32, unique=True, default=generar_folio)
    estado = models.CharField(max_length=16, choices=ESTADO_CHOICES, default='Borrador')

    # Datos del aspirante
    nombre = models.CharField(max_length=80)
    apellido_paterno = models.CharField(max_length=80)
    apellido_materno = models.CharField(max_length=80, blank=True)
    curp = models.CharField(max_length=18)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)

    # Programa
    carrera_solicitada = models.ForeignKey(Carrera, on_delete=models.SET_NULL, null=True, blank=True)
    modalidad = models.CharField(max_length=32, blank=True)
    turno = models.CharField(max_length=32, blank=True)
    periodo_escolar = models.ForeignKey(PeriodoEscolar, on_delete=models.SET_NULL, null=True, blank=True)

    # Pago (general, se mantiene por compatibilidad)
    monto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    comprobante_pago = models.FileField(upload_to='inscripciones/comprobantes/', null=True, blank=True)

    # Metadatos
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    observaciones = models.TextField(blank=True)

    def __str__(self):
        return f"{self.folio} - {self.nombre} {self.apellido_paterno}"

    class Meta:
        verbose_name = 'Inscripción (Nuevo Proceso)'
        verbose_name_plural = 'Inscripciones (Nuevo Proceso)'
        ordering = ['-creado_en']


class DocumentoInscripcionNueva(models.Model):
    TIPO_CHOICES = [
        ('SOLICITUD', 'Solicitud'),
        ('FOTO', 'Fotografía'),
        ('ACTA_NAC', 'Acta de Nacimiento'),
        ('CURP', 'CURP'),
        ('CERT_PREPA', 'Certificado de Preparatoria'),
        ('CERT_MEDICO', 'Certificado Médico'),
        ('NO_ANTEC_PENALES', 'Carta de No Antecedentes Penales'),
        ('NSS', 'Número de Seguro Social'),
        ('RENUNCIA_SEG', 'Renuncia Seguro'),
        ('CONST_LAB', 'Constancia Laboral'),
    ]

    inscripcion = models.ForeignKey(InscripcionNueva, related_name='documentos', on_delete=models.CASCADE)
    tipo = models.CharField(max_length=32, choices=TIPO_CHOICES)
    archivo = models.FileField(upload_to='inscripciones/documentos/')
    notas = models.CharField(max_length=255, blank=True)
    cargado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.inscripcion.folio} - {self.tipo}"

    class Meta:
        verbose_name = 'Documento de inscripción (Nuevo)'
        verbose_name_plural = 'Documentos de inscripción (Nuevo)'
        ordering = ['-cargado_en']


class PagoInscripcionConcepto(models.Model):
    CONCEPT_CHOICES = [
        ('FICHA', 'Ficha'),
        ('INSCRIPCION', 'Inscripción'),
        ('PROPEDEUTICO', 'Propedéutico'),
        ('CREDENCIAL', 'Credencial'),
        ('SEGURO', 'Seguro'),
    ]

    ESTADO_CHOICES = [
        ('pagado', 'Pagado'),
        ('condonacion', 'Condonación'),
        ('no_aplica', 'No aplica'),
        ('pendiente', 'Pendiente'),
    ]

    inscripcion = models.ForeignKey(InscripcionNueva, related_name='pagos', on_delete=models.CASCADE)
    concepto = models.CharField(max_length=32, choices=CONCEPT_CHOICES)
    estado = models.CharField(max_length=16, choices=ESTADO_CHOICES, default='pendiente')
    monto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    comprobante = models.FileField(upload_to='inscripciones/comprobantes/', null=True, blank=True)
    notas = models.CharField(max_length=255, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('inscripcion', 'concepto')
        verbose_name = 'Pago de inscripción por concepto'
        verbose_name_plural = 'Pagos de inscripción por concepto'
        ordering = ['concepto']

    def __str__(self):
        return f"{self.inscripcion.folio} - {self.concepto} ({self.estado})"