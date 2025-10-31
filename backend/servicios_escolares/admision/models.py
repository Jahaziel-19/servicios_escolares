from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date
import json
import uuid
import random


class PeriodoAdmision(models.Model):
    """Modelo para gestionar los períodos de admisión anuales"""
    nombre = models.CharField(max_length=100, help_text="Ej: Admisión 2025")
    año = models.IntegerField(default=date.today().year)
    fecha_inicio = models.DateTimeField(help_text="Fecha y hora de apertura del proceso")
    fecha_fin = models.DateTimeField(help_text="Fecha y hora de cierre del proceso")
    activo = models.BooleanField(default=False, help_text="Solo puede haber un período activo")
    descripcion = models.TextField(blank=True, null=True)
    
    # Formulario base precargado para este proceso de admisión (opcional)
    formulario_base = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text="(Opcional) Estructura base del formulario específico para este proceso de admisión"
    )
    
    class Meta:
        verbose_name = "Período de Admisión"
        verbose_name_plural = "Períodos de Admisión"
        ordering = ['-año', '-fecha_inicio']
    
    def __str__(self):
        return f"{self.nombre} ({self.año})"
    
    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio >= self.fecha_fin:
            raise ValidationError("La fecha de inicio debe ser anterior a la fecha de fin.")
    
    def save(self, *args, **kwargs):
        # Validar modelo y asegurar unicidad de período activo
        self.full_clean()
        if self.activo:
            PeriodoAdmision.objects.filter(activo=True).exclude(pk=self.pk).update(activo=False)
        super().save(*args, **kwargs)
    
    def get_formulario_base_default(self):
        """Retorna la estructura base por defecto para el formulario de admisión"""
        return {
            "nombre": f"Formulario de Admisión {self.nombre}",
            "descripcion": f"Formulario específico para el proceso {self.nombre}",
            "campos": [
                {
                    "id": "datos_personales_section",
                    "type": "section",
                    "label": "Datos Personales",
                    "required": False
                },
                {
                    "id": "nombre",
                    "type": "text",
                    "label": "Nombre(s)",
                    "name": "nombre",
                    "required": True,
                    "placeholder": "Ingresa tu nombre completo"
                },
                {
                    "id": "apellido_paterno",
                    "type": "text",
                    "label": "Apellido Paterno",
                    "name": "apellido_paterno",
                    "required": True,
                    "placeholder": "Ingresa tu apellido paterno"
                },
                {
                    "id": "apellido_materno",
                    "type": "text",
                    "label": "Apellido Materno",
                    "name": "apellido_materno",
                    "required": True,
                    "placeholder": "Ingresa tu apellido materno"
                },
                {
                    "id": "curp",
                    "type": "text",
                    "label": "CURP",
                    "name": "curp",
                    "required": True,
                    "placeholder": "Clave Única de Registro de Población",
                    "validation": {
                        "pattern": "^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[0-9A-Z][0-9]$",
                        "maxlength": 18,
                        "minlength": 18
                    }
                },
                {
                    "id": "email",
                    "type": "email",
                    "label": "Correo Electrónico",
                    "name": "email",
                    "required": True,
                    "placeholder": "correo@ejemplo.com"
                },
                {
                    "id": "telefono",
                    "type": "text",
                    "label": "Teléfono",
                    "name": "telefono",
                    "required": True,
                    "placeholder": "10 dígitos sin espacios"
                },
                {
                    "id": "fecha_nacimiento",
                    "type": "date",
                    "label": "Fecha de Nacimiento",
                    "name": "fecha_nacimiento",
                    "required": True
                },
                {
                    "id": "datos_academicos_section",
                    "type": "section",
                    "label": "Datos Académicos",
                    "required": False
                },
                {
                    "id": "escuela_procedencia",
                    "type": "text",
                    "label": "Escuela de Procedencia",
                    "name": "escuela_procedencia",
                    "required": True,
                    "placeholder": "Nombre completo de la institución"
                },
                {
                    "id": "promedio",
                    "type": "number",
                    "label": "Promedio General",
                    "name": "promedio",
                    "required": True,
                    "placeholder": "Ej: 8.5",
                    "validation": {
                        "min": 6.0,
                        "max": 10.0,
                        "step": 0.1
                    }
                },
                {
                    "id": "carrera_interes",
                    "type": "select",
                    "label": "Carrera de Interés",
                    "name": "carrera_interes",
                    "required": True,
                    "options": [
                        "Ingeniería en Sistemas Computacionales",
                        "Ingeniería Industrial",
                        "Ingeniería Electromecánica",
                        "Ingeniería en Gestión Empresarial",
                        "Ingeniería en Logística",
                        "Ingeniería en Materiales"
                    ]
                }
            ]
        }
    
    @property
    def esta_abierto(self):
        """Verifica si el período está actualmente abierto para recibir solicitudes"""
        ahora = timezone.now()
        return self.activo and self.fecha_inicio <= ahora <= self.fecha_fin


class FormularioAdmision(models.Model):
    """Modelo para definir la estructura del formulario de admisión usando JSON"""
    periodo = models.OneToOneField(PeriodoAdmision, on_delete=models.CASCADE, related_name='formulario')
    nombre = models.CharField(max_length=100, default="Formulario de Admisión")
    estructura_json = models.JSONField(
        help_text="Estructura del formulario en formato JSON con campos, tipos y validaciones"
    )
    version = models.CharField(max_length=20, default="1.0")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Formulario de Admisión"
        verbose_name_plural = "Formularios de Admisión"
    
    def __str__(self):
        return f"{self.nombre} - {self.periodo.nombre}"
    
    def clean(self):
        """Validar que la estructura JSON tenga el formato correcto"""
        if self.estructura_json:
            try:
                # Validar que sea un JSON válido y tenga la estructura esperada
                if not isinstance(self.estructura_json, dict):
                    raise ValidationError("La estructura debe ser un objeto JSON válido.")
                
                if 'campos' not in self.estructura_json:
                    raise ValidationError("La estructura debe contener una clave 'campos'.")
                
                campos = self.estructura_json['campos']
                if not isinstance(campos, list):
                    raise ValidationError("Los campos deben ser una lista.")
                
                # Validar cada campo
                for i, campo in enumerate(campos):
                    if not isinstance(campo, dict):
                        raise ValidationError(f"El campo {i+1} debe ser un objeto.")
                    
                    required_keys = ['id', 'tipo', 'etiqueta']
                    for key in required_keys:
                        if key not in campo:
                            raise ValidationError(f"El campo {i+1} debe tener la clave '{key}'.")
                
            except (TypeError, ValueError) as e:
                raise ValidationError(f"Error en la estructura JSON: {str(e)}")


class SolicitudAdmision(models.Model):
    """Modelo para almacenar las solicitudes de admisión de los aspirantes"""
    folio = models.CharField(max_length=20, unique=True, editable=False)
    periodo = models.ForeignKey(PeriodoAdmision, on_delete=models.CASCADE, related_name='solicitudes')
    
    # Datos básicos del aspirante
    curp = models.CharField(
        max_length=18,
        validators=[RegexValidator(
            regex=r'^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[0-9A-Z][0-9]$',
            message='CURP debe tener el formato válido de 18 caracteres'
        )],
        help_text="Clave Única de Registro de Población"
    )
    email = models.EmailField(help_text="Correo electrónico para notificaciones")
    
    # Respuestas del formulario en JSON
    respuestas_json = models.JSONField(help_text="Respuestas del aspirante en formato JSON")
    
    # Metadatos
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    ip_registro = models.GenericIPAddressField(null=True, blank=True)
    
    # Estado de la solicitud
    ESTADOS = [
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada'),
        ('en_revision', 'En Revisión'),
        ('aceptada', 'Aceptada'),
        ('seleccionado', 'Seleccionado'),
        ('no_seleccionado', 'No seleccionado'),
        ('rechazada', 'Rechazada'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador')
    
    class Meta:
        verbose_name = "Solicitud de Admisión"
        verbose_name_plural = "Solicitudes de Admisión"
        unique_together = ['curp', 'periodo']  # Un CURP por período
        ordering = ['-fecha_registro']
    
    def __str__(self):
        return f"Solicitud {self.folio} - {self.curp}"
    
    def save(self, *args, **kwargs):
        if not self.folio:
            self.folio = self.generar_folio()
        super().save(*args, **kwargs)
    
    def generar_folio(self):
        """Genera un folio único para la solicitud"""
        año = self.periodo.año
        prefijo = f"ADM-{año}-"
        # Intentar generar un código numérico de 6 dígitos único dentro del período
        # Mantener bajo riesgo de colisión con intentos limitados
        for _ in range(20):
            codigo = f"{random.randint(0, 999999):06d}"
            folio = f"{prefijo}{codigo}"
            if not SolicitudAdmision.objects.filter(folio=folio).exists():
                return folio
        # Fallback: usar UUID si no se logró en los intentos
        codigo = str(uuid.uuid4().int)[:6]
        return f"{prefijo}{codigo}"
    
    def get_respuesta(self, campo_id):
        """Obtiene la respuesta de un campo específico"""
        return self.respuestas_json.get(campo_id, '')
    
    def get_nombre_completo(self):
        """Obtiene el nombre completo del aspirante desde las respuestas"""
        nombre = self.get_respuesta('nombre') or ''
        apellido_paterno = self.get_respuesta('apellido_paterno') or ''
        apellido_materno = self.get_respuesta('apellido_materno') or ''
        return f"{apellido_paterno} {apellido_materno} {nombre}".strip()


class FichaAdmision(models.Model):
    """Modelo para gestionar las fichas de admisión generadas"""
    solicitud = models.OneToOneField(SolicitudAdmision, on_delete=models.CASCADE, related_name='ficha')
    numero_ficha = models.CharField(max_length=20, unique=True, editable=False)
    
    # Archivos generados
    archivo_pdf = models.FileField(upload_to='fichas_admision/', null=True, blank=True)
    
    # Metadatos
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    generada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Control de envío por email
    email_enviado = models.BooleanField(default=False)
    fecha_envio_email = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Ficha de Admisión"
        verbose_name_plural = "Fichas de Admisión"
        ordering = ['-fecha_generacion']
    
    def __str__(self):
        return f"Ficha {self.numero_ficha} - {self.solicitud.folio}"
    
    def save(self, *args, **kwargs):
        if not self.numero_ficha:
            self.numero_ficha = self.generar_numero_ficha()
        super().save(*args, **kwargs)
    
    def generar_numero_ficha(self):
        """Genera un número único para la ficha"""
        año = self.solicitud.periodo.año
        # Usar el folio de la solicitud como base
        return f"FICHA{año}{self.solicitud.folio[-6:]}"


class SolicitudEstadoLog(models.Model):
    """Registro de cambios de estado de una solicitud de admisión"""
    solicitud = models.ForeignKey('SolicitudAdmision', on_delete=models.CASCADE, related_name='estado_logs')
    estado_anterior = models.CharField(max_length=20, choices=SolicitudAdmision.ESTADOS)
    nuevo_estado = models.CharField(max_length=20, choices=SolicitudAdmision.ESTADOS)
    comentario = models.TextField(blank=True)
    notificacion_enviada = models.BooleanField(default=False)
    resultado_notificacion = models.TextField(blank=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log de Estado de Solicitud"
        verbose_name_plural = "Logs de Estado de Solicitud"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.solicitud.folio}: {self.estado_anterior} -> {self.nuevo_estado} ({self.fecha:%Y-%m-%d %H:%M})"


class SolicitudAdjunto(models.Model):
    """Adjuntos opcionales asociados a una solicitud (p.ej. ordenes de pago)"""
    solicitud = models.ForeignKey('SolicitudAdmision', on_delete=models.CASCADE, related_name='adjuntos')
    log = models.ForeignKey(SolicitudEstadoLog, on_delete=models.SET_NULL, null=True, blank=True, related_name='adjuntos')
    archivo = models.FileField(upload_to='admision_adjuntos/')
    nombre = models.CharField(max_length=255, blank=True)
    descripcion = models.TextField(blank=True)
    subido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Adjunto de Solicitud"
        verbose_name_plural = "Adjuntos de Solicitud"
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"Adjunto {self.id} de {self.solicitud.folio}"


class ConfiguracionAdmision(models.Model):
    """Modelo para configuraciones generales del sistema de admisión"""
    clave = models.CharField(max_length=50, unique=True)
    valor = models.TextField()
    descripcion = models.TextField(blank=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    modificado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Configuración de Admisión"
        verbose_name_plural = "Configuraciones de Admisión"
    
    def __str__(self):
        return f"{self.clave}: {self.valor[:50]}..."
    
    @classmethod
    def get_valor(cls, clave, default=None):
        """Obtiene el valor de una configuración"""
        try:
            config = cls.objects.get(clave=clave)
            return config.valor
        except cls.DoesNotExist:
            return default
    
    @classmethod
    def set_valor(cls, clave, valor, descripcion="", usuario=None):
        """Establece el valor de una configuración"""
        config, created = cls.objects.get_or_create(
            clave=clave,
            defaults={'valor': valor, 'descripcion': descripcion, 'modificado_por': usuario}
        )
        if not created:
            config.valor = valor
            config.descripcion = descripcion
            config.modificado_por = usuario
            config.save()
        return config