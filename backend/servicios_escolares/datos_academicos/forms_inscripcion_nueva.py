from django import forms
from django.forms import ClearableFileInput, modelformset_factory
from .models_inscripcion_nueva import InscripcionNueva, PagoInscripcionConcepto
from .models import PeriodoEscolar

class MultipleFileInput(ClearableFileInput):
    allow_multiple_selected = True


class Paso1AspiranteForm(forms.ModelForm):
    class Meta:
        model = InscripcionNueva
        fields = [
            'nombre', 'apellido_paterno', 'apellido_materno',
            'curp', 'email', 'telefono', 'fecha_nacimiento'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido_paterno': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido_materno': forms.TextInput(attrs={'class': 'form-control'}),
            'curp': forms.TextInput(attrs={'class': 'form-control text-uppercase', 'maxlength': '18'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class Paso2ProgramaForm(forms.ModelForm):
    class Meta:
        model = InscripcionNueva
        fields = ['carrera_solicitada', 'modalidad', 'periodo_escolar']
        widgets = {
            'carrera_solicitada': forms.Select(attrs={'class': 'form-select'}),
            'modalidad': forms.Select(attrs={'class': 'form-select'}),
            'periodo_escolar': forms.Select(attrs={'class': 'form-select'}),
        }

    modalidad = forms.ChoiceField(
        choices=[('Escolarizado', 'Escolarizado'), ('Sabatino', 'Sabatino')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Obligatorios aunque el modelo permita blank
        self.fields['carrera_solicitada'].required = True
        self.fields['modalidad'].required = True
        self.fields['periodo_escolar'].required = True

        # Mostrar solo el período escolar activo
        periodo_activo = PeriodoEscolar.objects.filter(activo=True).first()
        if periodo_activo:
            self.fields['periodo_escolar'].queryset = PeriodoEscolar.objects.filter(id=periodo_activo.id)
            self.fields['periodo_escolar'].initial = periodo_activo
        else:
            # Si no hay activo, mostrar vacío para obligar a administración a activarlo
            self.fields['periodo_escolar'].queryset = PeriodoEscolar.objects.none()

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('carrera_solicitada'):
            self.add_error('carrera_solicitada', 'Seleccione una carrera.')
        if not cleaned.get('modalidad'):
            self.add_error('modalidad', 'Seleccione una modalidad.')
        if not cleaned.get('periodo_escolar'):
            self.add_error('periodo_escolar', 'Seleccione el período escolar.')
        return cleaned


class Paso3DocumentosForm(forms.Form):
    # Form sin campos obligatorios; los inputs se manejan por tipo de documento en la plantilla
    pass


class Paso4PagoForm(forms.ModelForm):
    class Meta:
        model = InscripcionNueva
        fields = ['monto', 'comprobante_pago']
        widgets = {
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'comprobante_pago': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
        }


# Formulario por concepto de pago (para interfaz amigable)
class PagoConceptoForm(forms.ModelForm):
    class Meta:
        model = PagoInscripcionConcepto
        fields = ['estado', 'monto', 'comprobante', 'notas']
        widgets = {
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'comprobante': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'notas': forms.TextInput(attrs={'class': 'form-control'}),
        }

PagoConceptoFormSet = modelformset_factory(
    PagoInscripcionConcepto,
    form=PagoConceptoForm,
    extra=0,
)