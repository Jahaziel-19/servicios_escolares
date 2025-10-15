from django import forms
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from datetime import date, datetime
from .models import SolicitudAdmision, PeriodoAdmision
import re


class ConsultaSolicitudForm(forms.Form):
    """
    Formulario para consultar el estado de una solicitud
    """
    TIPO_BUSQUEDA_CHOICES = [
        ('folio', 'Folio'),
        ('curp', 'CURP'),
    ]
    
    tipo_busqueda = forms.ChoiceField(
        choices=TIPO_BUSQUEDA_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'tipo_busqueda'
        }),
        label='Buscar por'
    )
    
    valor_busqueda = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'valor_busqueda',
            'placeholder': 'Ingresa tu folio o CURP'
        }),
        label='Valor de búsqueda'
    )
    
    def clean_valor_busqueda(self):
        valor = self.cleaned_data.get('valor_busqueda', '').strip().upper()
        tipo = self.cleaned_data.get('tipo_busqueda')
        
        if not valor:
            raise ValidationError('Este campo es requerido.')
        
        if tipo == 'curp' and len(valor) != 18:
            raise ValidationError('El CURP debe tener exactamente 18 caracteres.')
        
        return valor


class RegistroAspiranteForm(forms.Form):
    """
    Formulario completo para registro de aspirantes basado en el documento de referencia
    """
    
    # ========== DATOS PERSONALES ==========
    nombre = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Ingresa tu nombre completo',
            'autocomplete': 'given-name'
        }),
        label='Nombre(s)',
        help_text='Escribe tu nombre tal como aparece en tu identificación oficial'
    )
    
    apellido_paterno = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Apellido paterno',
            'autocomplete': 'family-name'
        }),
        label='Apellido Paterno'
    )
    
    apellido_materno = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Apellido materno (opcional)',
            'autocomplete': 'family-name'
        }),
        label='Apellido Materno'
    )
    
    SEXO_CHOICES = [
        ('', 'Selecciona tu sexo'),
        ('M', 'Masculino'),
        ('F', 'Femenino')
    ]
    
    sexo = forms.ChoiceField(
        choices=SEXO_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg'
        }),
        label='Sexo'
    )
    
    curp = forms.CharField(
        max_length=18,
        validators=[RegexValidator(
            regex=r'^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[0-9A-Z][0-9]$',
            message='CURP debe tener el formato válido de 18 caracteres'
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'CURP de 18 caracteres',
            'style': 'text-transform: uppercase;',
            'maxlength': '18',
            'autocomplete': 'off'
        }),
        label='CURP',
        help_text='Clave Única de Registro de Población (18 caracteres)'
    )

    fecha_nacimiento = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control form-control-lg',
            'type': 'date',
            'max': date.today().strftime('%Y-%m-%d')
        }),
        label='Fecha de Nacimiento'
    )
    
    numero_seguridad_social = forms.CharField(
        max_length=11,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '12345678901',
            'maxlength': '11'
        }),
        label='Número de Seguridad Social',
        help_text='Opcional: 11 dígitos del IMSS'
    )
    
    ESTADO_CIVIL_CHOICES = [
        ('', 'Selecciona tu estado civil'),
        ('soltero', 'Soltero(a)'),
        ('casado', 'Casado(a)'),
        ('union_libre', 'Unión Libre'),
        ('divorciado', 'Divorciado(a)'),
        ('viudo', 'Viudo(a)')
    ]
    
    estado_civil = forms.ChoiceField(
        choices=ESTADO_CIVIL_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg'
        }),
        label='Estado Civil'
    )

    # ========== DATOS DE CONTACTO ==========
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'correo@ejemplo.com',
            'autocomplete': 'email'
        }),
        label='Correo Electrónico',
        help_text='Recibirás notificaciones importantes en este correo'
    )

    telefono = forms.CharField(
        max_length=10,
        validators=[RegexValidator(
            regex=r'^[0-9]{10}$',
            message='El teléfono debe tener exactamente 10 dígitos'
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '5512345678',
            'maxlength': '10',
            'autocomplete': 'tel'
        }),
        label='Número de teléfono',
        help_text='10 dígitos sin espacios ni guiones'
    )
    
    # ========== DIRECCIÓN ==========
    direccion = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Calle, número, colonia',
            'autocomplete': 'street-address'
        }),
        label='Dirección',
        help_text='Calle, número exterior e interior'
    )
    
    codigo_postal = forms.CharField(
        max_length=5,
        validators=[RegexValidator(
            regex=r'^[0-9]{5}$',
            message='El código postal debe tener exactamente 5 dígitos'
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '90000',
            'maxlength': '5',
            'autocomplete': 'postal-code'
        }),
        label='Código postal'
    )
    
    colonia_comunidad = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Colonia o comunidad',
            'autocomplete': 'address-level3'
        }),
        label='Colonia / Comunidad'
    )
    
    ZONA_PROCEDENCIA_CHOICES = [
        ('', 'Selecciona zona de procedencia'),
        ('urbana', 'Urbana'),
        ('rural', 'Rural')
    ]
    
    zona_procedencia = forms.ChoiceField(
        choices=ZONA_PROCEDENCIA_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg'
        }),
        label='Zona de procedencia'
    )

    municipio = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Municipio o delegación',
            'autocomplete': 'address-level2'
        }),
        label='Municipio'
    )

    estado = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Estado de residencia',
            'autocomplete': 'address-level1'
        }),
        label='Estado'
    )
    
    # ========== INFORMACIÓN ACADÉMICA ==========
    CARRERAS_CHOICES = [
        ('', 'Selecciona la carrera de tu interés'),
        ('sistemas', 'Ingeniería en Sistemas Computacionales'),
        ('industrial', 'Ingeniería Industrial'),
        ('electromecanica', 'Ingeniería Electromecánica'),
        ('gestion', 'Ingeniería en Gestión Empresarial'),
        ('logistica', 'Ingeniería en Logística'),
        ('materiales', 'Ingeniería en Materiales')
    ]

    carrera_primera_opcion = forms.ChoiceField(
        choices=CARRERAS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg'
        }),
        label='Ingeniería que desea cursar (PRIMERA OPCIÓN)',
        help_text='Selecciona tu primera opción de carrera'
    )
    
    carrera_segunda_opcion = forms.ChoiceField(
        choices=CARRERAS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg'
        }),
        label='Ingeniería que desea cursar (SEGUNDA OPCIÓN)',
        help_text='Opcional: Selecciona una segunda opción'
    )

    MODALIDAD_CHOICES = [
        ('', 'Selecciona modalidad'),
        ('presencial', 'Presencial (Lunes a Viernes)'),
        ('sabatino', 'Sabatino (Sábados)')
    ]

    modalidad = forms.ChoiceField(
        choices=MODALIDAD_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg'
        }),
        label='Modalidad'
    )
    
    # ========== INFORMACIÓN LABORAL ==========
    TRABAJA_CHOICES = [
        ('', 'Selecciona una opción'),
        ('si', 'Sí'),
        ('no', 'No')
    ]
    
    trabaja = forms.ChoiceField(
        choices=TRABAJA_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg'
        }),
        label='¿Trabajas?'
    )
    
    TRABAJADOR_SEGURIDAD_CHOICES = [
        ('', 'Selecciona una opción'),
        ('si', 'Sí'),
        ('no', 'No')
    ]
    
    trabajador_seguridad_ciudadana = forms.ChoiceField(
        choices=TRABAJADOR_SEGURIDAD_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg'
        }),
        label='¿ERES TRABAJADOR DE LA SECRETARÍA DE SEGURIDAD CIUDADANA DEL ESTADO DE TLAXCALA?'
    )
    
    nombre_empresa = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Nombre de la empresa o institución'
        }),
        label='Mencione el nombre de la empresa o institución donde trabaja'
    )
    
    direccion_empresa = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Dirección completa del trabajo'
        }),
        label='Dirección de la empresa o institución donde labora'
    )
    
    telefono_trabajo = forms.CharField(
        max_length=10,
        required=False,
        validators=[RegexValidator(
            regex=r'^[0-9]{10}$',
            message='El teléfono debe tener exactamente 10 dígitos'
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '5512345678',
            'maxlength': '10'
        }),
        label='Teléfono de su trabajo'
    )
    
    puesto_trabajo = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Puesto que desempeña'
        }),
        label='Nombre del puesto que desempeña'
    )
    
    horario_trabajo = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Ej: Lunes a Viernes 8:00-17:00'
        }),
        label='Días y horario de trabajo'
    )
    
    # ========== INFORMACIÓN ACADÉMICA PREVIA ==========
    preparatoria_nombre = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Nombre completo de tu escuela de bachillerato'
        }),
        label='Preparatoria donde cursó',
        help_text='Escribe el nombre completo de la institución donde cursaste el bachillerato'
    )
    
    TIPO_PREPARATORIA_CHOICES = [
        ('', 'Selecciona el tipo'),
        ('publica', 'Pública'),
        ('privada', 'Privada'),
        ('tecnica', 'Técnica'),
        ('bachillerato_general', 'Bachillerato General'),
        ('bachillerato_tecnologico', 'Bachillerato Tecnológico')
    ]
    
    tipo_preparatoria = forms.ChoiceField(
        choices=TIPO_PREPARATORIA_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg'
        }),
        label='Tipo de preparatoria o bachillerato'
    )
    
    municipio_preparatoria = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Municipio donde se ubica'
        }),
        label='Municipio donde se ubica la preparatoria'
    )
    
    estado_preparatoria = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Estado donde se ubica'
        }),
        label='Estado donde se ubica la preparatoria'
    )

    promedio_general = forms.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(6.0), MaxValueValidator(10.0)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '8.5',
            'step': '0.01',
            'min': '6.0',
            'max': '10.0'
        }),
        label='Promedio general',
        help_text='Promedio general de bachillerato (6.0 - 10.0)'
    )

    año_egreso = forms.IntegerField(
        validators=[MinValueValidator(2010), MaxValueValidator(date.today().year + 1)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': str(date.today().year),
            'min': '2010',
            'max': str(date.today().year + 1)
        }),
        label='Año de egreso',
        help_text='Año en que terminaste o terminarás el bachillerato'
    )
    
    # ========== INFORMACIÓN DE SALUD ==========
    DISCAPACIDAD_CHOICES = [
        ('', 'Selecciona una opción'),
        ('si', 'Sí'),
        ('no', 'No')
    ]
    
    tiene_discapacidad = forms.ChoiceField(
        choices=DISCAPACIDAD_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg'
        }),
        label='¿Tienes alguna discapacidad?'
    )
    
    cual_discapacidad = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Especifica cuál'
        }),
        label='¿Cuál?'
    )
    
    LENGUA_INDIGENA_CHOICES = [
        ('', 'Selecciona una opción'),
        ('si', 'Sí'),
        ('no', 'No')
    ]
    
    habla_lengua_indigena = forms.ChoiceField(
        choices=LENGUA_INDIGENA_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg'
        }),
        label='¿Habla alguna lengua indígena?'
    )
    
    cual_lengua_indigena = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Especifica cuál'
        }),
        label='¿Cuál?'
    )
    
    ALERGICO_MEDICAMENTO_CHOICES = [
        ('', 'Selecciona una opción'),
        ('si', 'Sí'),
        ('no', 'No')
    ]
    
    alergico_medicamento = forms.ChoiceField(
        choices=ALERGICO_MEDICAMENTO_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg'
        }),
        label='¿Es alérgico a algún medicamento?'
    )
    
    cual_medicamento = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Especifica cuál medicamento'
        }),
        label='¿Cuál?'
    )
    
    # ========== INFORMACIÓN DEL PADRE/TUTOR ==========
    nombre_padre_tutor = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Nombre del padre o tutor'
        }),
        label='Nombre del padre / tutor'
    )
    
    apellido_paterno_padre = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Primer apellido'
        }),
        label='Primer apellido del padre / tutor'
    )
    
    apellido_materno_padre = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Segundo apellido'
        }),
        label='Segundo apellido del padre / tutor'
    )
    
    telefono_padre_tutor = forms.CharField(
        max_length=10,
        validators=[RegexValidator(
            regex=r'^[0-9]{10}$',
            message='El teléfono debe tener exactamente 10 dígitos'
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '5512345678',
            'maxlength': '10'
        }),
        label='Número Telefónico del padre / tutor'
    )
    
    direccion_padre_tutor = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Dirección completa'
        }),
        label='Dirección del padre / tutor'
    )
    
    codigo_postal_padre = forms.CharField(
        max_length=5,
        validators=[RegexValidator(
            regex=r'^[0-9]{5}$',
            message='El código postal debe tener exactamente 5 dígitos'
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '90000',
            'maxlength': '5'
        }),
        label='Código postal'
    )
    
    colonia_comunidad_padre = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Colonia o comunidad'
        }),
        label='Colonia / Comunidad'
    )
    
    municipio_padre = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Municipio'
        }),
        label='Municipio'
    )
    
    estado_padre = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Estado'
        }),
        label='Estado'
    )
    
    # ========== CONTACTOS DE EMERGENCIA ==========
    nombre_emergencia = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Nombre completo'
        }),
        label='Nombre de la persona en caso de una emergencia'
    )
    
    parentesco_emergencia = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Ej: Madre, Padre, Hermano, etc.'
        }),
        label='Parentesco'
    )
    
    telefono_emergencia = forms.CharField(
        max_length=10,
        validators=[RegexValidator(
            regex=r'^[0-9]{10}$',
            message='El teléfono debe tener exactamente 10 dígitos'
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '5512345678',
            'maxlength': '10'
        }),
        label='Número de teléfono'
    )
    
    # ========== PERSONAS AUTORIZADAS PARA CONSULTAR EXPEDIENTE ==========
    primera_persona_expediente = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Nombre completo'
        }),
        label='Primer persona que puede consultar tu expediente'
    )
    
    parentesco_primera_persona = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Parentesco'
        }),
        label='Parentesco'
    )
    
    segunda_persona_expediente = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Nombre completo (opcional)'
        }),
        label='Segunda persona que puede consultar tu expediente'
    )
    
    parentesco_segunda_persona = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Parentesco (opcional)'
        }),
        label='Parentesco'
    )

    # ========== INFORMACIÓN ADICIONAL ==========
    como_conociste = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Redes sociales, amigos, familia, etc.'
        }),
        label='¿Por qué medio te convenciste para estudiar en el ITSTlaxco?',
        help_text='Esta información nos ayuda a mejorar nuestros canales de comunicación'
    )

    comentarios_adicionales = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Comparte cualquier información adicional que consideres relevante...'
        }),
        label='Comentarios Adicionales',
        help_text='Opcional: Comparte cualquier información que consideres importante'
    )

    # ========== TÉRMINOS Y CONDICIONES ==========
    acepta_terminos = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input form-check-input-lg'
        }),
        label='Acepto los términos y condiciones',
        help_text='Debes aceptar los términos y condiciones para continuar'
    )

    acepta_comunicaciones = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Acepto recibir comunicaciones sobre el proceso de admisión',
        help_text='Opcional: Recibirás actualizaciones sobre tu solicitud y eventos de la institución'
    )

    def __init__(self, *args, **kwargs):
        # Extraer el parámetro periodo antes de llamar al super()
        self.periodo = kwargs.pop('periodo', None)
        super().__init__(*args, **kwargs)
        
        # Si no se pasó un período, obtener el activo
        if not self.periodo:
            self.periodo = PeriodoAdmision.objects.filter(activo=True).first()
        
        # Configurar campos dinámicos si es necesario
        if self.periodo and self.periodo.formulario_base:
            # Aquí se pueden personalizar campos basados en el período activo
            pass

    def clean_curp(self):
        curp = self.cleaned_data.get('curp', '').strip().upper()
        
        if not curp:
            raise ValidationError('El CURP es requerido.')
        
        if len(curp) != 18:
            raise ValidationError('El CURP debe tener exactamente 18 caracteres.')
        
        # Verificar si ya existe una solicitud con este CURP en el período activo
        if self.periodo:
            if SolicitudAdmision.objects.filter(curp=curp, periodo=self.periodo).exists():
                raise ValidationError('Ya existe una solicitud registrada con este CURP para el período actual.')
        
        return curp

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        
        if not email:
            raise ValidationError('El correo electrónico es requerido.')
        
        # Verificar si ya existe una solicitud con este email en el período activo
        if self.periodo:
            if SolicitudAdmision.objects.filter(email=email, periodo=self.periodo).exists():
                raise ValidationError('Ya existe una solicitud registrada con este correo electrónico para el período actual.')
        
        return email

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get('fecha_nacimiento')
        
        if not fecha:
            raise ValidationError('La fecha de nacimiento es requerida.')
        
        # Verificar que la persona tenga al menos 15 años
        hoy = date.today()
        edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
        
        if edad < 15:
            raise ValidationError('Debes tener al menos 15 años para registrarte.')
        
        if edad > 100:
            raise ValidationError('Por favor verifica la fecha de nacimiento.')
        
        return fecha

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').strip()
        
        if telefono and not re.match(r'^[0-9]{10}$', telefono):
            raise ValidationError('El teléfono debe tener exactamente 10 dígitos.')
        
        return telefono

    def clean(self):
        cleaned_data = super().clean()
        
        # Validaciones condicionales
        trabaja = cleaned_data.get('trabaja')
        if trabaja == 'si':
            if not cleaned_data.get('nombre_empresa'):
                self.add_error('nombre_empresa', 'Este campo es requerido si trabajas.')
            if not cleaned_data.get('puesto_trabajo'):
                self.add_error('puesto_trabajo', 'Este campo es requerido si trabajas.')
        
        tiene_discapacidad = cleaned_data.get('tiene_discapacidad')
        if tiene_discapacidad == 'si' and not cleaned_data.get('cual_discapacidad'):
            self.add_error('cual_discapacidad', 'Especifica qué tipo de discapacidad tienes.')
        
        habla_lengua = cleaned_data.get('habla_lengua_indigena')
        if habla_lengua == 'si' and not cleaned_data.get('cual_lengua_indigena'):
            self.add_error('cual_lengua_indigena', 'Especifica qué lengua indígena hablas.')
        
        alergico = cleaned_data.get('alergico_medicamento')
        if alergico == 'si' and not cleaned_data.get('cual_medicamento'):
            self.add_error('cual_medicamento', 'Especifica a qué medicamento eres alérgico.')
        
        return cleaned_data

    def get_respuestas_json(self):
        """
        Convierte los datos del formulario a formato JSON para almacenar en la base de datos
        """
        return {
            # Datos personales
            'nombre': self.cleaned_data.get('nombre', ''),
            'apellido_paterno': self.cleaned_data.get('apellido_paterno', ''),
            'apellido_materno': self.cleaned_data.get('apellido_materno', ''),
            'sexo': self.cleaned_data.get('sexo', ''),
            'curp': self.cleaned_data.get('curp', ''),
            'fecha_nacimiento': self.cleaned_data.get('fecha_nacimiento', '').isoformat() if self.cleaned_data.get('fecha_nacimiento') else '',
            'numero_seguridad_social': self.cleaned_data.get('numero_seguridad_social', ''),
            'estado_civil': self.cleaned_data.get('estado_civil', ''),
            
            # Contacto
            'email': self.cleaned_data.get('email', ''),
            'telefono': self.cleaned_data.get('telefono', ''),
            
            # Dirección
            'direccion': self.cleaned_data.get('direccion', ''),
            'codigo_postal': self.cleaned_data.get('codigo_postal', ''),
            'colonia_comunidad': self.cleaned_data.get('colonia_comunidad', ''),
            'zona_procedencia': self.cleaned_data.get('zona_procedencia', ''),
            'municipio': self.cleaned_data.get('municipio', ''),
            'estado': self.cleaned_data.get('estado', ''),
            
            # Información académica
            'carrera_primera_opcion': self.cleaned_data.get('carrera_primera_opcion', ''),
            'carrera_segunda_opcion': self.cleaned_data.get('carrera_segunda_opcion', ''),
            'modalidad': self.cleaned_data.get('modalidad', ''),
            
            # Información laboral
            'trabaja': self.cleaned_data.get('trabaja', ''),
            'trabajador_seguridad_ciudadana': self.cleaned_data.get('trabajador_seguridad_ciudadana', ''),
            'nombre_empresa': self.cleaned_data.get('nombre_empresa', ''),
            'direccion_empresa': self.cleaned_data.get('direccion_empresa', ''),
            'telefono_trabajo': self.cleaned_data.get('telefono_trabajo', ''),
            'puesto_trabajo': self.cleaned_data.get('puesto_trabajo', ''),
            'horario_trabajo': self.cleaned_data.get('horario_trabajo', ''),
            
            # Información académica previa
            'preparatoria_nombre': self.cleaned_data.get('preparatoria_nombre', ''),
            'tipo_preparatoria': self.cleaned_data.get('tipo_preparatoria', ''),
            'municipio_preparatoria': self.cleaned_data.get('municipio_preparatoria', ''),
            'estado_preparatoria': self.cleaned_data.get('estado_preparatoria', ''),
            'promedio_general': str(self.cleaned_data.get('promedio_general', '')),
            'año_egreso': self.cleaned_data.get('año_egreso', ''),
            
            # Información de salud
            'tiene_discapacidad': self.cleaned_data.get('tiene_discapacidad', ''),
            'cual_discapacidad': self.cleaned_data.get('cual_discapacidad', ''),
            'habla_lengua_indigena': self.cleaned_data.get('habla_lengua_indigena', ''),
            'cual_lengua_indigena': self.cleaned_data.get('cual_lengua_indigena', ''),
            'alergico_medicamento': self.cleaned_data.get('alergico_medicamento', ''),
            'cual_medicamento': self.cleaned_data.get('cual_medicamento', ''),
            
            # Información del padre/tutor
            'nombre_padre_tutor': self.cleaned_data.get('nombre_padre_tutor', ''),
            'apellido_paterno_padre': self.cleaned_data.get('apellido_paterno_padre', ''),
            'apellido_materno_padre': self.cleaned_data.get('apellido_materno_padre', ''),
            'telefono_padre_tutor': self.cleaned_data.get('telefono_padre_tutor', ''),
            'direccion_padre_tutor': self.cleaned_data.get('direccion_padre_tutor', ''),
            'codigo_postal_padre': self.cleaned_data.get('codigo_postal_padre', ''),
            'colonia_comunidad_padre': self.cleaned_data.get('colonia_comunidad_padre', ''),
            'municipio_padre': self.cleaned_data.get('municipio_padre', ''),
            'estado_padre': self.cleaned_data.get('estado_padre', ''),
            
            # Contactos de emergencia
            'nombre_emergencia': self.cleaned_data.get('nombre_emergencia', ''),
            'parentesco_emergencia': self.cleaned_data.get('parentesco_emergencia', ''),
            'telefono_emergencia': self.cleaned_data.get('telefono_emergencia', ''),
            
            # Personas autorizadas
            'primera_persona_expediente': self.cleaned_data.get('primera_persona_expediente', ''),
            'parentesco_primera_persona': self.cleaned_data.get('parentesco_primera_persona', ''),
            'segunda_persona_expediente': self.cleaned_data.get('segunda_persona_expediente', ''),
            'parentesco_segunda_persona': self.cleaned_data.get('parentesco_segunda_persona', ''),
            
            # Información adicional
            'como_conociste': self.cleaned_data.get('como_conociste', ''),
            'comentarios_adicionales': self.cleaned_data.get('comentarios_adicionales', ''),
            'acepta_terminos': self.cleaned_data.get('acepta_terminos', False),
            'acepta_comunicaciones': self.cleaned_data.get('acepta_comunicaciones', False),
        }