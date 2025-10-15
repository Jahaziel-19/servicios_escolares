from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from .models import SolicitudAdmision, PeriodoAdmision, FormularioAdmision
import json


class FormularioDinamicoAdmision(forms.Form):
    """
    Formulario dinámico que se genera basado en la estructura JSON
    del FormularioAdmision del período activo
    """
    
    def __init__(self, *args, **kwargs):
        self.periodo = kwargs.pop('periodo', None)
        self.solicitud = kwargs.pop('solicitud', None)
        super().__init__(*args, **kwargs)
        
        if self.periodo and self.periodo.formulario_base:
            self._generar_campos_dinamicos()
        
        # Si hay una solicitud existente, prellenar los campos
        if self.solicitud and self.solicitud.respuestas_json:
            self._prellenar_campos()
    
    def _generar_campos_dinamicos(self):
        """Genera los campos del formulario basado en la estructura JSON"""
        estructura = self.periodo.formulario_base
        
        if 'campos' not in estructura:
            return
        
        for campo in estructura['campos']:
            field_id = campo.get('id')
            field_type = campo.get('type')  # Cambiado de 'tipo' a 'type'
            field_label = campo.get('label')  # Cambiado de 'etiqueta' a 'label'
            field_required = campo.get('required', False)  # Cambiado de 'requerido' a 'required'
            field_help = campo.get('help', '')  # Cambiado de 'ayuda' a 'help'
            field_options = campo.get('options', [])  # Cambiado de 'opciones' a 'options'
            field_attrs = campo.get('attributes', {})  # Cambiado de 'atributos' a 'attributes'
            
            # Saltar secciones, solo procesar campos de entrada
            if field_type == 'section':
                continue
            
            # Crear el campo según su tipo
            django_field = self._crear_campo_django(
                field_type, field_label, field_required, 
                field_help, field_options, field_attrs
            )
            
            if django_field:
                self.fields[field_id] = django_field
    
    def _crear_campo_django(self, field_type, label, required, help_text, options, attrs):
        """Crea un campo de Django basado en el tipo especificado"""
        common_attrs = {
            'class': 'form-control',
            **attrs
        }
        
        field_kwargs = {
            'label': label,
            'required': required,
            'help_text': help_text,
        }
        
        if field_type == 'texto' or field_type == 'text':
            field_kwargs['widget'] = forms.TextInput(attrs=common_attrs)
            return forms.CharField(**field_kwargs)
        
        elif field_type == 'texto_largo':
            field_kwargs['widget'] = forms.Textarea(attrs={**common_attrs, 'rows': 4})
            return forms.CharField(**field_kwargs)
        
        elif field_type == 'email':
            field_kwargs['widget'] = forms.EmailInput(attrs=common_attrs)
            return forms.EmailField(**field_kwargs)
        
        elif field_type == 'telefono':
            field_kwargs['widget'] = forms.TextInput(attrs=common_attrs)
            field_kwargs['validators'] = [
                RegexValidator(
                    regex=r'^\d{10}$',
                    message='El teléfono debe tener 10 dígitos'
                )
            ]
            return forms.CharField(**field_kwargs)
        
        elif field_type == 'curp':
            field_kwargs['widget'] = forms.TextInput(attrs={
                **common_attrs,
                'maxlength': '18',
                'style': 'text-transform: uppercase;'
            })
            field_kwargs['validators'] = [
                RegexValidator(
                    regex=r'^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[0-9A-Z][0-9]$',
                    message='CURP debe tener el formato válido de 18 caracteres'
                )
            ]
            return forms.CharField(**field_kwargs)
        
        elif field_type == 'fecha':
            field_kwargs['widget'] = forms.DateInput(attrs={
                **common_attrs,
                'type': 'date'
            })
            return forms.DateField(**field_kwargs)
        
        elif field_type == 'numero':
            field_kwargs['widget'] = forms.NumberInput(attrs=common_attrs)
            return forms.IntegerField(**field_kwargs)
        
        elif field_type == 'decimal':
            field_kwargs['widget'] = forms.NumberInput(attrs={
                **common_attrs,
                'step': '0.01'
            })
            return forms.DecimalField(**field_kwargs)
        
        elif field_type == 'seleccion':
            choices = [(opt.get('valor', ''), opt.get('etiqueta', '')) for opt in options]
            choices.insert(0, ('', 'Seleccione una opción...'))
            field_kwargs['choices'] = choices
            field_kwargs['widget'] = forms.Select(attrs=common_attrs)
            return forms.ChoiceField(**field_kwargs)
        
        elif field_type == 'seleccion_multiple':
            choices = [(opt.get('valor', ''), opt.get('etiqueta', '')) for opt in options]
            field_kwargs['choices'] = choices
            field_kwargs['widget'] = forms.CheckboxSelectMultiple()
            return forms.MultipleChoiceField(**field_kwargs)
        
        elif field_type == 'radio':
            choices = [(opt.get('valor', ''), opt.get('etiqueta', '')) for opt in options]
            field_kwargs['choices'] = choices
            field_kwargs['widget'] = forms.RadioSelect()
            return forms.ChoiceField(**field_kwargs)
        
        elif field_type == 'checkbox':
            field_kwargs['widget'] = forms.CheckboxInput(attrs={'class': 'form-check-input'})
            return forms.BooleanField(**field_kwargs)
        
        elif field_type == 'archivo':
            field_kwargs['widget'] = forms.FileInput(attrs={
                **common_attrs,
                'accept': attrs.get('accept', '')
            })
            return forms.FileField(**field_kwargs)
        
        else:
            # Tipo no reconocido, crear campo de texto por defecto
            field_kwargs['widget'] = forms.TextInput(attrs=common_attrs)
            return forms.CharField(**field_kwargs)
    
    def _prellenar_campos(self):
        """Prellena los campos con datos de una solicitud existente"""
        for field_name in self.fields:
            if field_name in self.solicitud.respuestas_json:
                self.fields[field_name].initial = self.solicitud.respuestas_json[field_name]
    
    def clean(self):
        """Validaciones personalizadas del formulario"""
        cleaned_data = super().clean()
        
        # Validar CURP único para el período
        curp = cleaned_data.get('curp')
        if curp and self.periodo:
            existing_solicitud = SolicitudAdmision.objects.filter(
                curp=curp,
                periodo=self.periodo
            )
            
            # Si estamos editando, excluir la solicitud actual
            if self.solicitud:
                existing_solicitud = existing_solicitud.exclude(pk=self.solicitud.pk)
            
            if existing_solicitud.exists():
                raise ValidationError({
                    'curp': 'Ya existe una solicitud con este CURP para el período actual.'
                })
        
        return cleaned_data
    
    def get_respuestas_json(self):
        """Convierte los datos limpios del formulario a formato JSON"""
        if not self.is_valid():
            return {}
        
        respuestas = {}
        for field_name, value in self.cleaned_data.items():
            # Convertir valores especiales a formato serializable
            if hasattr(value, 'isoformat'):  # Fechas
                respuestas[field_name] = value.isoformat()
            elif isinstance(value, list):  # Selección múltiple
                respuestas[field_name] = value
            else:
                respuestas[field_name] = str(value) if value is not None else ''
        
        return respuestas


class SolicitudAdmisionForm(forms.ModelForm):
    """Formulario base para la solicitud de admisión"""
    
    class Meta:
        model = SolicitudAdmision
        fields = ['curp', 'email']
        widgets = {
            'curp': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '18',
                'style': 'text-transform: uppercase;',
                'placeholder': 'CURP de 18 caracteres'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.periodo = kwargs.pop('periodo', None)
        super().__init__(*args, **kwargs)
    
    def clean_curp(self):
        curp = self.cleaned_data.get('curp', '').upper()
        
        if self.periodo:
            existing = SolicitudAdmision.objects.filter(
                curp=curp,
                periodo=self.periodo
            )
            
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('Ya existe una solicitud con este CURP para el período actual.')
        
        return curp


class FormularioAdmisionAdminForm(forms.ModelForm):
    """Formulario para administrar la estructura JSON del formulario"""
    
    estructura_json_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 20,
            'class': 'form-control',
            'style': 'font-family: monospace;'
        }),
        help_text='Estructura del formulario en formato JSON'
    )
    
    class Meta:
        model = FormularioAdmision
        fields = ['periodo', 'nombre', 'version', 'estructura_json_text']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si hay una instancia, convertir JSON a texto
        if self.instance.pk and self.instance.estructura_json:
            self.fields['estructura_json_text'].initial = json.dumps(
                self.instance.estructura_json, 
                indent=2, 
                ensure_ascii=False
            )
    
    def clean_estructura_json_text(self):
        """Validar que el texto sea JSON válido"""
        text = self.cleaned_data.get('estructura_json_text', '')
        
        try:
            json_data = json.loads(text)
            return json_data
        except json.JSONDecodeError as e:
            raise ValidationError(f'JSON inválido: {str(e)}')
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.estructura_json = self.cleaned_data['estructura_json_text']
        
        if commit:
            instance.save()
        
        return instance