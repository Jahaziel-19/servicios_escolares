from django import forms
from datos_academicos.models import PeriodoEscolar


class PeriodoEscolarForm(forms.ModelForm):
    class Meta:
        model = PeriodoEscolar
        fields = ['ciclo', 'año', 'fecha_inicio', 'fecha_fin', 'inicio_vacaciones', 'fin_vacaciones', 'activo']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
            'inicio_vacaciones': forms.DateInput(attrs={'type': 'date'}),
            'fin_vacaciones': forms.DateInput(attrs={'type': 'date'}),
        }