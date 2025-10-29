from django import forms
from django.core.exceptions import ValidationError
from datetime import date, datetime
from .models_inscripcion import Inscripcion
from .models import Alumno, Carrera, PeriodoEscolar
import re


class InscripcionForm(forms.ModelForm):
    """
    Formulario para el proceso de inscripción de nuevos alumnos
    """
    
    class Meta:
        model = Inscripcion
        fields = [
            'periodo_escolar', 'tipo_inscripcion', 'nombre', 'apellido_paterno', 
            'apellido_materno', 'curp', 'fecha_nacimiento', 'sexo', 'estado_civil',
            'telefono', 'email', 'calle', 'numero_exterior', 'numero_interior',
            'colonia', 'municipio', 'estado', 'codigo_postal', 'zona_procedencia',
            'carrera_solicitada', 'modalidad', 'semestre_ingreso', 'escuela_procedencia',
            'promedio_bachillerato', 'año_egreso_bachillerato', 'acta_nacimiento',
            'certificado_bachillerato', 'curp_documento', 'fotografias', 
            'comprobante_domicilio', 'observaciones'
        ]
        
        widgets = {
            'periodo_escolar': forms.Select(attrs={'class': 'form-select'}),
            'tipo_inscripcion': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre(s)'}),
            'apellido_paterno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido Paterno'}),
            'apellido_materno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido Materno'}),
            'curp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CURP (18 caracteres)', 'maxlength': '18'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sexo': forms.Select(attrs={'class': 'form-select'}),
            'estado_civil': forms.Select(attrs={'class': 'form-select'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
            'calle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Calle'}),
            'numero_exterior': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Núm. Ext.'}),
            'numero_interior': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Núm. Int.'}),
            'colonia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Colonia'}),
            'municipio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Municipio'}),
            'estado': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Estado'}),
            'codigo_postal': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'C.P.', 'maxlength': '5'}),
            'zona_procedencia': forms.Select(attrs={'class': 'form-select'}),
            'carrera_solicitada': forms.Select(attrs={'class': 'form-select'}),
            'modalidad': forms.Select(attrs={'class': 'form-select'}),
            'semestre_ingreso': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '19'}),
            'escuela_procedencia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escuela de procedencia'}),
            'promedio_bachillerato': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'año_egreso_bachillerato': forms.NumberInput(attrs={'class': 'form-control', 'min': '1990', 'max': str(date.today().year)}),
            'acta_nacimiento': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'certificado_bachillerato': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'curp_documento': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fotografias': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'comprobante_domicilio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': '3', 'placeholder': 'Observaciones adicionales'}),
        }
        
        labels = {
            'periodo_escolar': 'Periodo Escolar',
            'tipo_inscripcion': 'Tipo de Inscripción',
            'nombre': 'Nombre(s)',
            'apellido_paterno': 'Apellido Paterno',
            'apellido_materno': 'Apellido Materno',
            'curp': 'CURP',
            'fecha_nacimiento': 'Fecha de Nacimiento',
            'sexo': 'Sexo',
            'estado_civil': 'Estado Civil',
            'telefono': 'Teléfono',
            'email': 'Correo Electrónico',
            'calle': 'Calle',
            'numero_exterior': 'Número Exterior',
            'numero_interior': 'Número Interior',
            'colonia': 'Colonia',
            'municipio': 'Municipio',
            'estado': 'Estado',
            'codigo_postal': 'Código Postal',
            'zona_procedencia': 'Zona de Procedencia',
            'carrera_solicitada': 'Carrera Solicitada',
            'modalidad': 'Modalidad',
            'semestre_ingreso': 'Semestre de Ingreso',
            'escuela_procedencia': 'Escuela de Procedencia',
            'promedio_bachillerato': 'Promedio de Bachillerato',
            'año_egreso_bachillerato': 'Año de Egreso del Bachillerato',
            'acta_nacimiento': 'Acta de Nacimiento',
            'certificado_bachillerato': 'Certificado de Bachillerato',
            'curp_documento': 'CURP (Documento)',
            'fotografias': 'Fotografías',
            'comprobante_domicilio': 'Comprobante de Domicilio',
            'observaciones': 'Observaciones',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limitar selección al período activo y con inscripciones habilitadas si existe
        periodo_activo_habilitado = PeriodoEscolar.objects.filter(activo=True, inscripcion_habilitada=True).first()
        if periodo_activo_habilitado:
            self.fields['periodo_escolar'].queryset = PeriodoEscolar.objects.filter(id=periodo_activo_habilitado.id)
            self.fields['periodo_escolar'].initial = periodo_activo_habilitado
        else:
            # Si no hay período activo habilitado, mostrar el activo (si existe) para informar
            periodo_activo = PeriodoEscolar.objects.filter(activo=True).first()
            if periodo_activo:
                self.fields['periodo_escolar'].queryset = PeriodoEscolar.objects.filter(id=periodo_activo.id)
                self.fields['periodo_escolar'].initial = periodo_activo
            else:
                # Sin período activo, permitir ver todos para contexto pero validaremos en clean()
                self.fields['periodo_escolar'].queryset = PeriodoEscolar.objects.all()

    def clean_curp(self):
        curp = self.cleaned_data.get('curp', '').upper()
        
        # Validar formato de CURP
        if not re.match(r'^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[0-9A-Z][0-9]$', curp):
            raise ValidationError('El formato de CURP no es válido.')
        
        # Verificar que no exista ya en Inscripcion o Alumno
        if Inscripcion.objects.filter(curp=curp).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError('Ya existe una inscripción con este CURP.')
            
        if Alumno.objects.filter(curp=curp).exists():
            raise ValidationError('Ya existe un alumno registrado con este CURP.')
        
        return curp
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        
        # Verificar que no exista ya en Inscripcion o Alumno
        if Inscripcion.objects.filter(email=email).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError('Ya existe una inscripción con este correo electrónico.')
            
        if Alumno.objects.filter(email=email).exists():
            raise ValidationError('Ya existe un alumno registrado con este correo electrónico.')
        
        return email
    
    def clean_codigo_postal(self):
        cp = self.cleaned_data.get('codigo_postal', '')
        
        if not re.match(r'^\d{5}$', cp):
            raise ValidationError('El código postal debe tener exactamente 5 dígitos.')
        
        return cp
    
    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '')
        
        # Remover espacios y caracteres especiales
        telefono_limpio = re.sub(r'[^\d]', '', telefono)
        
        if len(telefono_limpio) < 10:
            raise ValidationError('El teléfono debe tener al menos 10 dígitos.')
        
        return telefono_limpio
    
    def clean_fecha_nacimiento(self):
        fecha_nacimiento = self.cleaned_data.get('fecha_nacimiento')
        
        if fecha_nacimiento:
            # Verificar que la persona tenga al menos 15 años
            edad = (date.today() - fecha_nacimiento).days / 365.25
            if edad < 15:
                raise ValidationError('El aspirante debe tener al menos 15 años.')
            
            # Verificar que no sea una fecha futura
            if fecha_nacimiento > date.today():
                raise ValidationError('La fecha de nacimiento no puede ser futura.')
        
        return fecha_nacimiento
    
    def clean_promedio_bachillerato(self):
        promedio = self.cleaned_data.get('promedio_bachillerato')
        
        if promedio and (promedio < 6.0 or promedio > 10.0):
            raise ValidationError('El promedio debe estar entre 6.0 y 10.0.')
        
        return promedio

    def clean(self):
        cleaned_data = super().clean()
        periodo = cleaned_data.get('periodo_escolar')
        if not periodo:
            self.add_error('periodo_escolar', 'Debe seleccionar un período escolar.')
            return cleaned_data
        # Validar que el período esté activo y habilitado para inscripciones
        if not getattr(periodo, 'activo', False):
            self.add_error('periodo_escolar', 'Debes seleccionar el período escolar activo.')
        if not getattr(periodo, 'inscripcion_habilitada', True):
            self.add_error('periodo_escolar', 'Las inscripciones están deshabilitadas para este período.')
        return cleaned_data


# Eliminadas clases de Reinscripción (ReinscripcionForm) y búsqueda asociada (BusquedaAlumnoForm)