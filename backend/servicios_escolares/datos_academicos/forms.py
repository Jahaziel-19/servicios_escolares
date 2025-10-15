# datos_academicos/forms.py
from django import forms
from .models import Alumno, Tramite, Calificacion

class AlumnoForm(forms.ModelForm):
    class Meta:
        model = Alumno
        fields = [
            'matricula', 'nombre', 'apellido_paterno', 'apellido_materno',
            'carrera', 'semestre', 'modalidad', 'estatus',
            'curp', 'email', 'fecha_nacimiento', 'sexo',
            'estado_civil', 'telefono', 'rfc', 'nss', 'calle', 'numero_exterior',
            'numero_interior', 'colonia', 'municipio', 'estado', 'codigo_postal',
            'zona_procedencia' #'division_estudio'
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
        }
    def __init__(self, *args, **kwargs):
        super(AlumnoForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

class TramiteForm(forms.ModelForm):
    class Meta:
        model = Tramite
        fields = ['clave', 'nombre', 'descripcion', 'precio']
        widgets = {
            'clave': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Clave del trámite (máximo 10 caracteres)'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del trámite'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción del trámite (opcional)'
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Precio del trámite'
            }),
        }
        labels = {
            'clave': 'Clave',
            'nombre': 'Nombre',
            'descripcion': 'Descripción',
            'precio': 'Precio',
        }

class CalificacionForm(forms.ModelForm):
    # Campos de texto para búsqueda
    alumno_search = forms.CharField(
        required=False,
        label="Buscar alumno",
        widget=forms.TextInput(attrs={
            'class': 'form-control autocomplete-input',
            'placeholder': 'Escribe para buscar alumno...',
            'autocomplete': 'off'
        })
    )
    
    materia_search = forms.CharField(
        required=False,
        label="Buscar materia",
        widget=forms.TextInput(attrs={
            'class': 'form-control autocomplete-input',
            'placeholder': 'Escribe para buscar materia...',
            'autocomplete': 'off'
        })
    )
    
    # Campo para agregar materia no listada
    materia_nueva = forms.CharField(
        required=False,
        label="Agregar materia no listada",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de la materia no listada',
            'autocomplete': 'off'
        })
    )
    
    class Meta:
        model = Calificacion
        fields = ['alumno', 'materia', 'periodo_escolar', 'calificacion', 'creditos', 'acreditacion', 'observaciones']
        widgets = {
            'alumno': forms.HiddenInput(),
            'materia': forms.HiddenInput(),
            'periodo_escolar': forms.Select(attrs={'class': 'form-control select2'}),
            'calificacion': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'creditos': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'acreditacion': forms.Select(attrs={'class': 'form-control select2'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones adicionales (opcional)'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo alumnos activos
        self.fields['alumno'].queryset = Alumno.objects.filter(activo=True)
        
        # Si estamos editando, prellenamos los campos de búsqueda
        if self.instance and self.instance.pk:
            if self.instance.alumno:
                self.initial['alumno_search'] = f"{self.instance.alumno.nombre} {self.instance.alumno.apellido_paterno} ({self.instance.alumno.matricula})"
            if self.instance.materia:
                self.initial['materia_search'] = f"{self.instance.materia.nombre} ({self.instance.materia.clave})"