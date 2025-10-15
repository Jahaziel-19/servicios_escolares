from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from datetime import date, datetime
from .models import Alumno, PeriodoEscolar, Carrera


class InscripcionSimple(models.Model):
    """
    Modelo simplificado para el proceso de inscripción de alumnos
    Solo incluye los campos esenciales para agilizar el proceso
    """
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Aprobada', 'Aprobada'),
        ('Rechazada', 'Rechazada'),
    ]
    
    MODALIDAD_CHOICES = [
        ('A', 'Presencial'),
        ('B', 'Sabatino'),
    ]
    
    # Información básica
    folio = models.CharField(max_length=20, unique=True, blank=True)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')
    
    # Datos personales básicos
    nombre = models.CharField(max_length=100, verbose_name="Nombre(s)")
    apellido_paterno = models.CharField(max_length=50, verbose_name="Apellido Paterno")
    apellido_materno = models.CharField(max_length=50, blank=True, null=True, verbose_name="Apellido Materno")
    curp = models.CharField(max_length=18, unique=True, verbose_name="CURP")
    
    # Datos personales adicionales (basados en Excel)
    fecha_nacimiento = models.DateField(blank=True, null=True, verbose_name="Fecha de Nacimiento")
    sexo = models.CharField(
        max_length=1, 
        choices=[('M', 'Masculino'), ('F', 'Femenino')], 
        blank=True, 
        null=True, 
        verbose_name="Sexo"
    )
    estado_civil = models.CharField(
        max_length=20, 
        choices=[
            ('Soltero', 'Soltero'), 
            ('Casado', 'Casado'), 
            ('Divorciado', 'Divorciado'), 
            ('Viudo', 'Viudo')
        ], 
        blank=True, 
        null=True, 
        verbose_name="Estado Civil"
    )
    rfc = models.CharField(max_length=13, blank=True, null=True, verbose_name="RFC")
    nss = models.CharField(max_length=11, blank=True, null=True, verbose_name="NSS")
    
    # Contacto
    email = models.EmailField(verbose_name="Correo Electrónico")
    telefono = models.CharField(max_length=15, verbose_name="Teléfono")
    
    # Datos de domicilio (basados en Excel)
    calle = models.CharField(max_length=100, blank=True, null=True, verbose_name="Calle")
    numero_exterior = models.CharField(max_length=10, blank=True, null=True, verbose_name="Número Exterior")
    numero_interior = models.CharField(max_length=10, blank=True, null=True, verbose_name="Número Interior")
    colonia = models.CharField(max_length=100, blank=True, null=True, verbose_name="Colonia")
    municipio = models.CharField(max_length=100, blank=True, null=True, verbose_name="Municipio")
    estado = models.CharField(max_length=100, blank=True, null=True, verbose_name="Estado")
    codigo_postal = models.CharField(max_length=5, blank=True, null=True, verbose_name="Código Postal")
    zona_procedencia = models.CharField(
        max_length=100, 
        choices=[('Urbana', 'Urbana'), ('Rural', 'Rural')], 
        blank=True, 
        null=True, 
        verbose_name="Zona de Procedencia"
    )
    
    # Información académica básica
    carrera_solicitada = models.ForeignKey(
        Carrera, 
        on_delete=models.CASCADE, 
        related_name='inscripciones_simples',
        verbose_name="Carrera Solicitada"
    )
    modalidad = models.CharField(
        max_length=1, 
        choices=MODALIDAD_CHOICES, 
        default='A',
        verbose_name="Modalidad"
    )
    escuela_procedencia = models.CharField(
        max_length=200, 
        verbose_name="Escuela de Procedencia"
    )
    semestre_ingreso = models.IntegerField(default=1, verbose_name="Semestre de Ingreso")
    promedio_anterior = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        blank=True, 
        null=True, 
        verbose_name="Promedio Anterior"
    )
    
    # Información adicional
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    # Relación con alumno creado
    alumno_creado = models.ForeignKey(
        Alumno, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='inscripcion_simple_origen'
    )
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Inscripción Simple"
        verbose_name_plural = "Inscripciones Simples"
        ordering = ['-fecha_solicitud']
    
    def save(self, *args, **kwargs):
        if not self.folio:
            # Generar folio automático
            año = self.fecha_solicitud.year if self.fecha_solicitud else date.today().year
            ultimo_folio = InscripcionSimple.objects.filter(
                fecha_solicitud__year=año
            ).order_by('-folio').first()
            
            if ultimo_folio and ultimo_folio.folio:
                try:
                    numero = int(ultimo_folio.folio.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    numero = 1
            else:
                numero = 1
            
            self.folio = f"INS-{año}-{numero:04d}"
        
        # Convertir CURP a mayúsculas
        if self.curp:
            self.curp = self.curp.upper()
            
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validaciones personalizadas"""
        super().clean()
        
        # Validar formato de CURP
        if self.curp:
            import re
            curp_pattern = r'^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[0-9A-Z][0-9]$'
            if not re.match(curp_pattern, self.curp.upper()):
                raise ValidationError({'curp': 'El formato de CURP no es válido.'})
        
        # Validar que el teléfono tenga solo números
        if self.telefono:
            if not self.telefono.isdigit() or len(self.telefono) != 10:
                raise ValidationError({'telefono': 'El teléfono debe tener exactamente 10 dígitos.'})
    
    @property
    def nombre_completo(self):
        """Retorna el nombre completo del aspirante"""
        nombres = [self.nombre, self.apellido_paterno]
        if self.apellido_materno:
            nombres.append(self.apellido_materno)
        return ' '.join(nombres)
    
    @property
    def puede_crear_alumno(self):
        """Verifica si la inscripción puede crear un alumno"""
        return self.estado == 'Aprobada' and not self.alumno_creado
    
    def crear_alumno(self, periodo_escolar=None):
        """
        Crea un alumno basado en los datos de la inscripción
        Incluye todos los campos del Excel.
        """
        if not self.puede_crear_alumno:
            raise ValidationError("La inscripción debe estar aprobada y no tener un alumno asociado.")
        
        if not periodo_escolar:
            periodo_escolar = PeriodoEscolar.objects.filter(activo=True).first()
            if not periodo_escolar:
                raise ValidationError("No hay un período escolar activo.")
        
        # Generar matrícula con el formato especificado
        año = str(periodo_escolar.año)[-2:]  # Últimos 2 dígitos del año
        
        # Mapeo de claves de carrera según el formato especificado
        clave_carrera_map = {
            'INGENIERÍA EN ELECTROMECÁNICA': '01',
            'INGENIERÍA EN GESTIÓN EMPRESARIAL': '02', 
            'INGENIERÍA LOGÍSTICA': '03',
            'INGENIERÍA EN MATERIALES': '04',
            'INGENIERÍA QUÍMICA': '05'
        }
        
        # Obtener código de carrera
        carrera_nombre = self.carrera_solicitada.nombre.upper()
        clave_carrera = clave_carrera_map.get(carrera_nombre, '00')  # Default 00 si no se encuentra
        
        # Obtener el siguiente número consecutivo
        matricula_prefix = f"{año}{clave_carrera}"
        ultimo_alumno = Alumno.objects.filter(
            matricula__startswith=matricula_prefix
        ).order_by('-matricula').first()
        
        if ultimo_alumno and ultimo_alumno.matricula:
            try:
                numero = int(ultimo_alumno.matricula[-3:]) + 1
            except (ValueError, IndexError):
                numero = 1
        else:
            numero = 1
        
        matricula = f"{matricula_prefix}{numero:03d}"
        
        # Obtener créditos totales del plan de estudio
        plan_estudio = self.carrera_solicitada.plan_estudio
        if plan_estudio and plan_estudio.creditos > 0:
            # Usar créditos del plan de estudio
            creditos_totales_carrera = plan_estudio.creditos
        elif self.carrera_solicitada.creditos_totales > 0:
            # Si no hay plan o el plan no tiene créditos, usar el campo de la carrera
            creditos_totales_carrera = self.carrera_solicitada.creditos_totales
        else:
            # Como último recurso, calcular desde las materias
            creditos_totales_carrera = self.carrera_solicitada.calcular_creditos_totales()
        
        # Obtener plan de estudio correspondiente a la carrera (ya obtenido arriba)
        
        # Crear el alumno con todos los campos disponibles
        alumno = Alumno.objects.create(
            matricula=matricula,
            nombre=self.nombre,
            apellido_paterno=self.apellido_paterno,
            apellido_materno=self.apellido_materno,
            curp=self.curp,
            fecha_nacimiento=self.fecha_nacimiento,
            sexo=self.sexo,
            estado_civil=self.estado_civil,
            rfc=self.rfc,
            nss=self.nss,
            email=self.email,
            telefono=self.telefono,
            calle=self.calle,
            numero_exterior=self.numero_exterior,
            numero_interior=self.numero_interior,
            colonia=self.colonia,
            municipio=self.municipio,
            estado=self.estado,
            codigo_postal=self.codigo_postal,
            zona_procedencia=self.zona_procedencia,
            carrera=self.carrera_solicitada,
            modalidad=self.modalidad,
            semestre=self.semestre_ingreso,
            promedio=self.promedio_anterior or 0.0,
            creditos_totales=creditos_totales_carrera,
            plan_estudio=plan_estudio,
            inicio_semestre=periodo_escolar.fecha_inicio,
            fin_semestre=periodo_escolar.fecha_fin,
            inicio_vacaciones=periodo_escolar.inicio_vacaciones,
            fin_vacaciones=periodo_escolar.fin_vacaciones,
            estatus='Inscrito',
            fecha_ingreso=date.today(),
            activo=True
        )
        
        # Asociar el alumno con la inscripción
        self.alumno_creado = alumno
        self.save()
        
        return alumno
    
    def __str__(self):
        return f"{self.folio} - {self.nombre_completo}"