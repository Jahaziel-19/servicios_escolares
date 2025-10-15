from django.db import models
from django.db.models import Avg
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from datetime import date, datetime
from decimal import Decimal, ROUND_DOWN

def año_actual():
    return datetime.datetime.now().year



class ChoicesNormalizationMixin(models.Model):
    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        for field in self._meta.get_fields():
            # Normalizar campos con choices
            if hasattr(field, 'choices') and field.choices and hasattr(self, field.name):
                valor = getattr(self, field.name)
                if valor is None:
                    continue
                valor_str = str(valor).strip().lower()
                for choice_val, _ in field.choices:
                    if choice_val.lower() == valor_str:
                        setattr(self, field.name, choice_val)
                        break

            # Truncar decimales en DecimalField
            if field.get_internal_type() == 'DecimalField' and hasattr(self, field.name):
                valor = getattr(self, field.name)
                if valor is not None:
                    decimales = field.decimal_places
                    try:
                        d = Decimal(str(valor))
                        d = d.quantize(Decimal(f'1.{"0"*decimales}'), rounding=ROUND_DOWN)
                        setattr(self, field.name, d)
                    except:
                        pass  


class PeriodoEscolar(models.Model):
    ciclo = models.CharField(max_length=50, blank=True, null=True)
    año = models.IntegerField(
        default=date.today().year,
        validators=[MinValueValidator(2004), MaxValueValidator(date.today().year + 10)]
    )
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    inicio_vacaciones = models.DateField(null=True, blank=True)
    fin_vacaciones = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=False, help_text="Solo puede haber un periodo activo que contenga la fecha actual.")

    class Meta:
        verbose_name = "Periodo Escolar"
        verbose_name_plural = "Periodos Escolares"

    def __str__(self):
        return f"{(self.ciclo or 'Periodo sin nombre').upper()} {self.año}"

    def clean(self):
        # Validaciones básicas
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio > self.fecha_fin:
            raise ValidationError("La fecha de inicio no puede ser posterior a la fecha de fin.")
        if self.inicio_vacaciones and self.fin_vacaciones and self.inicio_vacaciones > self.fin_vacaciones:
            raise ValidationError("El inicio de vacaciones no puede ser posterior al fin de vacaciones.")
        # Si se marca activo, debe contener la fecha actual
        if self.activo:
            hoy = date.today()
            if not (self.fecha_inicio and self.fecha_fin and self.fecha_inicio <= hoy <= self.fecha_fin):
                raise ValidationError("Un periodo marcado como activo debe contener la fecha actual.")

    def save(self, *args, **kwargs):
        # Validar antes de guardar
        self.full_clean()
        # Si se marca activo, desactivar otros activos
        if self.activo:
            PeriodoEscolar.objects.filter(activo=True).exclude(pk=self.pk).update(activo=False)
        super().save(*args, **kwargs)


class MateriaCarrera(models.Model):
    """Modelo intermedio para la relación Materia-Carrera con semestre específico"""
    materia = models.ForeignKey('Materia', on_delete=models.CASCADE)
    carrera = models.ForeignKey('Carrera', on_delete=models.CASCADE)
    semestre = models.IntegerField(null=True, blank=True, help_text="Semestre específico para esta carrera. Null para materias de especialidad y universales")
    
    class Meta:
        unique_together = ('materia', 'carrera')
        verbose_name = "Materia por Carrera"
        verbose_name_plural = "Materias por Carrera"
    
    def __str__(self):
        semestre_str = f"Sem. {self.semestre}" if self.semestre else "Sin semestre"
        return f"{self.materia.nombre} - {self.carrera.nombre} ({semestre_str})"


class Materia(ChoicesNormalizationMixin, models.Model):
    clave = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)    
    creditos = models.IntegerField()
    carreras = models.ManyToManyField('Carrera', through='MateriaCarrera', related_name='materias', blank=True)
    unidades = models.IntegerField(default=3, validators=[MinValueValidator(2), MaxValueValidator(8)])
    horas_teoria = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(6)])
    horas_practica = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(6)])
    tipo = models.CharField(max_length=20, choices=[
        ('Obligatoria', 'Obligatoria'),
        ('Especialidad', 'Especialidad'),
        ('Universal', 'Universal'),
        ('Actividad', 'Actividad')
    ], default='Obligatoria')
    cuenta_promedio = models.BooleanField(default=True, help_text="Si esta materia cuenta para el cálculo del promedio general")
    es_universal = models.BooleanField(default=False, help_text="Si es una materia universal (servicio social, residencia, etc.)")
        
    #plan_estudio = models.ForeignKey('PlanEstudio', on_delete=models.CASCADE, related_name='materias', default=None, null=True)
    #tipo = models.ForeignKey('TipoMateria', on_delete=models.CASCADE, related_name='materias', default=None, null=True)
    
    def get_semestre_para_carrera(self, carrera):
        """Obtiene el semestre específico para una carrera"""
        try:
            materia_carrera = MateriaCarrera.objects.get(materia=self, carrera=carrera)
            return materia_carrera.semestre
        except MateriaCarrera.DoesNotExist:
            return None
    
    def get_carreras_por_semestre(self):
        """Agrupa las carreras por semestre"""
        carreras_semestre = {}
        for mc in MateriaCarrera.objects.filter(materia=self).select_related('carrera'):
            semestre = mc.semestre or 'Sin semestre'
            if semestre not in carreras_semestre:
                carreras_semestre[semestre] = []
            carreras_semestre[semestre].append(mc.carrera)
        return carreras_semestre

    def __str__(self):
        return f"{self.nombre} ({self.clave})"

'''
class TipoMateria(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre
'''

class Tramite(models.Model):
    '''
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Aprobado', 'Aprobado'),
        ('Rechazado', 'Rechazado'),
        ('En Proceso', 'En Proceso'),
    ]

    tipo = models.CharField(max_length=100, help_text="Tipo de trámite, ej. Baja, Cambio de carrera, Revalidación")
    alumno = models.ForeignKey('Alumno', on_delete=models.CASCADE, related_name='tramites')
    fecha_solicitud = models.DateField(default=timezone.now)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_solicitud']
        verbose_name = 'Trámite Académico'
        verbose_name_plural = 'Trámites Académicos'

    def __str__(self):
        return f"{self.tipo} - {self.alumno.matricula} ({self.estado})"
    '''
    id = models.AutoField(primary_key=True)
    clave = models.CharField(max_length=10)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Trámite'
        verbose_name_plural = 'Trámites'
        ordering = ['-fecha_creacion']
        
    def __str__(self):
        return self.nombre

class PlanEstudio(models.Model):
    clave = models.CharField(max_length=20, unique=True, default=None)
    año = models.CharField(max_length=100, default=None)
    carrera = models.ForeignKey('Carrera', on_delete=models.CASCADE, related_name='planes_estudios', default=None, null=True)
    creditos = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(400)])
    #materias = models.ManyToManyField(Materia, related_name='planes_estudios', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Plan de Estudio'
        verbose_name_plural = 'Planes de Estudio'
        ordering = ['clave']

    def __str__(self):
        return f"{self.clave}"
    
class CarreraManager(models.Manager):
    def get_by_natural_key(self, clave):
        return self.get(clave=clave)


class Carrera(models.Model):
    clave = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    creditos_totales = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(500)], 
                                         help_text="Créditos totales requeridos para completar la carrera")
    objects = CarreraManager()
    plan_estudio = models.ForeignKey(PlanEstudio, on_delete=models.CASCADE, related_name='carreras', default=None, null=True)

    def natural_key(self):
        return (self.clave,)
    
    def calcular_creditos_totales(self):
        """
        Calcula automáticamente los créditos totales basado en las materias de la carrera.
        """
        from django.db.models import Sum
        
        total_creditos = self.materiacarrera_set.aggregate(
            total=Sum('materia__creditos')
        )['total']
        
        return total_creditos or 0

    def __str__(self):
        return f"{self.nombre} ({self.clave})"

class Grupo(ChoicesNormalizationMixin, models.Model):
    semestre = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(19)], help_text="Semestre del grupo")
    modalidad = models.CharField(max_length=1, choices=[
        ('A', 'A'),
        ('B', 'B'),
    ], default='A', help_text="Modalidad del grupo")
    #periodo_escolar = models.ForeignKey(PeriodoEscolar, on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name='grupos', default=None, null=True)
    #materias = models.ManyToManyField(Materia, related_name='grupos')
    class Meta:
        unique_together = ('carrera', 'semestre', 'modalidad')  # Restricción única compuesta

    def __str__(self):
        return f"{self.carrera.clave} {self.semestre} ° {self.modalidad}"    

class Alumno(ChoicesNormalizationMixin, models.Model):
    # Datos académicos
    matricula = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=50, default='', blank=True, null=True)
    apellido_materno = models.CharField(max_length=50, default='', blank=True, null=True)
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, related_name='alumnos')
    semestre = models.IntegerField(default=1)
    inicio_semestre = models.DateField(default=date.today, null=True, blank=True)
    fin_semestre = models.DateField(default=None, null=True, blank=True)
    inicio_vacaciones = models.DateField(default=None, null=True, blank=True)
    fin_vacaciones = models.DateField(default=None, null=True, blank=True)
    promedio = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    creditos_aprobados = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(400)])
    creditos_totales = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(400)])
    modalidad = models.CharField(max_length=20, choices=[('A', 'A (Presencial)'), ('B', 'B (Sabatino)')], default='A') # Cambiar a "Escolarizado"
    plan_estudio = models.ForeignKey(PlanEstudio, on_delete=models.CASCADE, related_name='alumnos', default=None, null=True)
    #grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name='alumnos', blank=True, null=True)
    fecha_ingreso = models.DateField(default=date.today, null=True, blank=True)
    estatus = models.CharField(max_length=20, choices=[
        ('Inscrito', 'Inscrito'), 
        ('No Inscrito', 'No Inscrito'),
        ('Egresado', 'Egresado'),
        ('Titulado', 'Titulado'),
        ('Baja definitiva', 'Baja definitiva'), 
        ('Baja temporal', 'Baja temporal')], 
        default='Inscrito')
    
    division_estudio = models.CharField(max_length=50, choices=[
        ('Nuevo Ingreso', 'Nuevo Ingreso'),
        ('Reingreso', 'Reingreso'),
        ('Convalidación', 'Convalidación'),
        ('Traslado', 'Traslado'),
        ('Equivalencia', 'Equivalencia')
    ], default='Nuevo Ingreso')
    activo = models.BooleanField(default=True)
    # Datos personales
    curp = models.CharField(max_length=18, unique=True, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    sexo = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Femenino')], blank=True, null=True)
    estado_civil = models.CharField(max_length=20, choices=[('Soltero', 'Soltero'), ('Casado', 'Casado'), ('Divorciado', 'Divorciado'), ('Viudo', 'Viudo')], blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    rfc = models.CharField(max_length=13, unique=True, blank=True, null=True)
    nss = models.CharField(unique=True, blank=True, null=True)
    # Datos de domicilio
    calle = models.CharField(max_length=100, blank=True, null=True)
    numero_exterior = models.CharField(max_length=10, blank=True, null=True)
    numero_interior = models.CharField(max_length=10, blank=True, null=True)
    colonia = models.CharField(max_length=100, blank=True, null=True)
    municipio = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=100, blank=True, null=True)
    codigo_postal = models.CharField(max_length=5, blank=True, null=True)
    zona_procedencia = models.CharField(max_length=100, choices=[('Urbana', 'Urbana'), ('Rural', 'Rural')], null=True)
    
    def calcular_promedio(self, periodo_escolar=None, incluir_todas=False):
        """
        Calcula el promedio del alumno basado en las materias que ha cursado.
        
        Args:
            periodo_escolar: Si se especifica, calcula solo para ese periodo
            incluir_todas: Si es True, incluye todas las materias. Si es False, solo las que cuentan para promedio
        """
        qs = self.calificaciones.all()
        if periodo_escolar:
            qs = qs.filter(periodo_escolar=periodo_escolar)
        
        if not incluir_todas:
            # Solo incluir materias que cuentan para el promedio
            qs = qs.filter(materia__cuenta_promedio=True)
        
        # Solo considerar materias de la carrera del alumno
        qs = qs.filter(materia__materiacarrera__carrera=self.carrera)
        
        promedio = qs.aggregate(promedio=Avg('calificacion'))['promedio']
        return float(promedio) if promedio else 0.0
    
    def calcular_creditos_aprobados(self, calificacion_minima=6.0):
        """
        Calcula los créditos aprobados del alumno.
        
        Args:
            calificacion_minima: Calificación mínima para considerar una materia como aprobada (default: 6.0)
        """
        from django.db.models import Sum
        
        # Obtener créditos de materias aprobadas de la carrera del alumno
        creditos_aprobados = self.calificaciones.filter(
            calificacion__gte=calificacion_minima,
            materia__materiacarrera__carrera=self.carrera
        ).aggregate(
            total_creditos=Sum('materia__creditos')
        )['total_creditos']
        
        return creditos_aprobados or 0
    
    def actualizar_datos_academicos(self):
        """
        Actualiza el promedio y créditos aprobados del alumno.
        También actualiza los créditos totales basado en la carrera.
        """
        self.promedio = self.calcular_promedio()
        self.creditos_aprobados = self.calcular_creditos_aprobados()
        # Actualizar créditos totales desde la carrera
        if self.carrera and self.carrera.creditos_totales > 0:
            self.creditos_totales = self.carrera.creditos_totales
        self.save(update_fields=['promedio', 'creditos_aprobados', 'creditos_totales'])
    
    def __str__(self):
        return f"{self.nombre} {self.apellido_paterno} ({self.matricula})"

class Docente(models.Model):
    nombre = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=50)
    apellido_materno = models.CharField(max_length=50, blank=True, null=True)
    titulo = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    materias = models.ManyToManyField(Materia, related_name='docentes')

    def __str__(self):
        return f"{self.nombre} {self.apellido_paterno}"
    
class Calificacion(ChoicesNormalizationMixin, models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name='calificaciones')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='calificaciones')
    periodo_escolar = models.ForeignKey(PeriodoEscolar, on_delete=models.CASCADE, related_name='calificaciones', default=None, null=True)
    calificacion = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    creditos = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(10)])
    acreditacion = models.CharField(choices=[('Ordinario', 'Ordinario'), 
                                             ('Convalidación', 'Convalidación'),
                                             ('Equivalencia', 'Equivalencia'),
                                             ('Traslado', 'Traslado'),
                                             ('Extraordinario', 'Extraordinario'),
                                             ], max_length=20, default='Ordinario')
    fecha_registro = models.DateField(auto_now_add=True)
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('alumno', 'materia', 'periodo_escolar')
        ordering = ['alumno', 'materia', 'periodo_escolar']

    def __str__(self):
        return f"{self.alumno} - {self.materia} ({self.periodo_escolar}): {self.calificacion}"
