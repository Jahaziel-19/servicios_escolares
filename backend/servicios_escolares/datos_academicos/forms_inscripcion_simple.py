from django import forms
from django.core.exceptions import ValidationError
from .models_inscripcion_simple import InscripcionSimple
from .models import Carrera, Alumno
import re


class InscripcionSimpleForm(forms.ModelForm):
    class Meta:
        model = InscripcionSimple
        fields = [
            'nombre', 'apellido_paterno', 'apellido_materno', 'curp',
            'fecha_nacimiento', 'sexo', 'estado_civil', 'rfc', 'nss',
            'email', 'telefono',
            'calle', 'numero_exterior', 'numero_interior', 'colonia', 
            'municipio', 'estado', 'codigo_postal', 'zona_procedencia',
            'carrera_solicitada', 'modalidad', 'escuela_procedencia',
            'semestre_ingreso', 'promedio_anterior'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese su nombre completo'
            }),
            'apellido_paterno': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese su apellido paterno'
            }),
            'apellido_materno': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese su apellido materno'
            }),
            'curp': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CURP de 18 caracteres',
                'maxlength': '18',
                'style': 'text-transform: uppercase;'
            }),
            'fecha_nacimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'sexo': forms.Select(attrs={
                'class': 'form-control'
            }),
            'estado_civil': forms.Select(attrs={
                'class': 'form-control'
            }),
            'rfc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'RFC (opcional)',
                'maxlength': '13',
                'style': 'text-transform: uppercase;'
            }),
            'nss': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'NSS (opcional)',
                'maxlength': '11'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de teléfono'
            }),
            'calle': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la calle'
            }),
            'numero_exterior': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número exterior'
            }),
            'numero_interior': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número interior (opcional)'
            }),
            'colonia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Colonia'
            }),
            'municipio': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Municipio'
            }),
            'estado': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Estado'
            }),
            'codigo_postal': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código postal',
                'maxlength': '5'
            }),
            'zona_procedencia': forms.Select(attrs={
                'class': 'form-control'
            }),
            'carrera_solicitada': forms.Select(attrs={
                'class': 'form-control'
            }),
            'modalidad': forms.Select(attrs={
                'class': 'form-control'
            }),
            'escuela_procedencia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la escuela de procedencia'
            }),
            'semestre_ingreso': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '12',
                'value': '1'
            }),
            'promedio_anterior': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '10',
                'step': '0.01',
                'placeholder': 'Promedio anterior (opcional)'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar queryset para carreras
        self.fields['carrera_solicitada'].queryset = Carrera.objects.all()
        self.fields['carrera_solicitada'].empty_label = "Seleccione una carrera"
        
        # Configurar campo de modalidad
        self.fields['modalidad'].empty_label = "Seleccione modalidad"
        
        # Marcar campos requeridos
        required_fields = ['nombre', 'apellido_paterno', 'curp', 'email', 'telefono', 
                          'carrera_solicitada', 'modalidad', 'escuela_procedencia']
        
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True
                # Agregar asterisco visual en el label
                if hasattr(self.fields[field_name], 'label'):
                    self.fields[field_name].label += ' *'
    
    def clean_curp(self):
        """Validar formato y unicidad de CURP"""
        curp = self.cleaned_data.get('curp', '').upper().strip()
        
        if not curp:
            raise ValidationError('El CURP es requerido.')
        
        # Validar formato
        curp_pattern = r'^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[0-9A-Z][0-9]$'
        if not re.match(curp_pattern, curp):
            raise ValidationError('El formato de CURP no es válido. Debe tener 18 caracteres.')
        
        # Verificar unicidad en InscripcionSimple
        if InscripcionSimple.objects.filter(curp=curp).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise ValidationError('Ya existe una inscripción con este CURP.')
        
        # Verificar que no exista en Alumno
        if Alumno.objects.filter(curp=curp).exists():
            raise ValidationError('Ya existe un alumno registrado con este CURP.')
        
        return curp
    
    def clean_email(self):
        """Validar unicidad de email"""
        email = self.cleaned_data.get('email', '').lower().strip()
        
        if not email:
            raise ValidationError('El correo electrónico es requerido.')
        
        # Verificar unicidad en InscripcionSimple
        if InscripcionSimple.objects.filter(email=email).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise ValidationError('Ya existe una inscripción con este correo electrónico.')
        
        # Verificar que no exista en Alumno
        if Alumno.objects.filter(email=email).exists():
            raise ValidationError('Ya existe un alumno registrado con este correo electrónico.')
        
        return email
    
    def clean_telefono(self):
        """Validar formato de teléfono"""
        telefono = self.cleaned_data.get('telefono', '').strip()
        
        if not telefono:
            raise ValidationError('El teléfono es requerido.')
        
        # Remover caracteres no numéricos
        telefono_limpio = re.sub(r'\D', '', telefono)
        
        if len(telefono_limpio) != 10:
            raise ValidationError('El teléfono debe tener exactamente 10 dígitos.')
        
        return telefono_limpio
    
    def clean_nombre(self):
        """Limpiar y validar nombre"""
        nombre = self.cleaned_data.get('nombre', '').strip().title()
        
        if not nombre:
            raise ValidationError('El nombre es requerido.')
        
        if len(nombre) < 2:
            raise ValidationError('El nombre debe tener al menos 2 caracteres.')
        
        # Validar que solo contenga letras y espacios
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre):
            raise ValidationError('El nombre solo puede contener letras y espacios.')
        
        return nombre
    
    def clean_apellido_paterno(self):
        """Limpiar y validar apellido paterno"""
        apellido = self.cleaned_data.get('apellido_paterno', '').strip().title()
        
        if not apellido:
            raise ValidationError('El apellido paterno es requerido.')
        
        if len(apellido) < 2:
            raise ValidationError('El apellido paterno debe tener al menos 2 caracteres.')
        
        # Validar que solo contenga letras y espacios
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', apellido):
            raise ValidationError('El apellido paterno solo puede contener letras y espacios.')
        
        return apellido
    
    def clean_apellido_materno(self):
        """Limpiar y validar apellido materno (opcional)"""
        apellido = self.cleaned_data.get('apellido_materno', '').strip().title()
        
        if apellido:
            if len(apellido) < 2:
                raise ValidationError('El apellido materno debe tener al menos 2 caracteres.')
            
            # Validar que solo contenga letras y espacios
            if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', apellido):
                raise ValidationError('El apellido materno solo puede contener letras y espacios.')
        
        return apellido if apellido else None
    
    def clean_escuela_procedencia(self):
        """Limpiar escuela de procedencia"""
        escuela = self.cleaned_data.get('escuela_procedencia', '').strip().title()
        
        if not escuela:
            raise ValidationError('La escuela de procedencia es requerida.')
        
        if len(escuela) < 5:
            raise ValidationError('El nombre de la escuela debe tener al menos 5 caracteres.')
        
        return escuela
    
    def save(self, commit=True):
        """Guardar inscripción con datos limpios"""
        inscripcion = super().save(commit=False)
        
        # Asegurar que CURP esté en mayúsculas
        if inscripcion.curp:
            inscripcion.curp = inscripcion.curp.upper()
        
        if commit:
            inscripcion.save()
        
        return inscripcion


class BusquedaInscripcionForm(forms.Form):
    """
    Formulario para búsqueda de inscripciones
    """
    folio = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Folio de inscripción'
        })
    )
    
    nombre = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre del aspirante'
        })
    )
    
    curp = forms.CharField(
        max_length=18,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-uppercase',
            'placeholder': 'CURP'
        })
    )
    
    carrera = forms.ModelChoiceField(
        queryset=Carrera.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Todas las carreras"
    )
    
    estado = forms.ChoiceField(
        choices=[('', 'Todos los estados')] + InscripcionSimple.ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def clean(self):
        """Validar que al menos un campo esté lleno"""
        cleaned_data = super().clean()
        
        campos_busqueda = ['folio', 'nombre', 'curp', 'carrera', 'estado']
        if not any(cleaned_data.get(campo) for campo in campos_busqueda):
            raise ValidationError('Debe especificar al menos un criterio de búsqueda.')
        
        return cleaned_data