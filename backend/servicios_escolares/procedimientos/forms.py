from django import forms
from .models import Tramite, Residencia
from datos_academicos.models import Alumno, PeriodoEscolar

class TramiteForm(forms.ModelForm):
    class Meta:
        model = Tramite
        fields = ['alumno', 'tipo', 'plantilla', 'observaciones']
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 3, 'class':'form-control'}),
        }


class ActaResidenciaForm(forms.Form):
    alumno = forms.ModelChoiceField(queryset=Alumno.objects.all(), widget=forms.Select(attrs={'class': 'form-select'}))
    periodo_escolar = forms.ModelChoiceField(queryset=PeriodoEscolar.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    empresa = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control'}))
    proyecto = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control'}))
    asesor_interno = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    asesor_externo = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    fecha_inicio = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    fecha_fin = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    horas_programadas = forms.IntegerField(required=False, min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    def inicializar_desde_residencia(self, residencia: Residencia):
        self.initial.update({
            'alumno': residencia.alumno,
            'periodo_escolar': residencia.periodo_escolar,
            'empresa': residencia.empresa,
            'proyecto': residencia.proyecto,
            'asesor_interno': residencia.asesor_interno,
            'asesor_externo': residencia.asesor_externo,
            'fecha_inicio': residencia.fecha_inicio,
            'fecha_fin': residencia.fecha_fin,
            'horas_programadas': residencia.horas_programadas,
        })


class ResidenciaForm(forms.ModelForm):
    class Meta:
        model = Residencia
        fields = [
            'alumno', 'periodo_escolar', 'empresa', 'proyecto',
            'asesor_interno', 'asesor_externo', 'fecha_inicio', 'fecha_fin',
            'horas_programadas', 'estado'
        ]
        widgets = {
            'alumno': forms.Select(attrs={'class': 'form-select'}),
            'periodo_escolar': forms.Select(attrs={'class': 'form-select'}),
            'empresa': forms.TextInput(attrs={'class': 'form-control'}),
            'proyecto': forms.TextInput(attrs={'class': 'form-control'}),
            'asesor_interno': forms.TextInput(attrs={'class': 'form-control'}),
            'asesor_externo': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'horas_programadas': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }
