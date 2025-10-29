from django import forms
from datos_academicos.models import PeriodoEscolar


class PeriodoEscolarForm(forms.ModelForm):
    class Meta:
        model = PeriodoEscolar
        fields = ['ciclo', 'año', 'fecha_inicio', 'fecha_fin', 'inicio_vacaciones', 'fin_vacaciones', 'activo']
        widgets = {
            'ciclo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. ENE-JUN'}),
            'año': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 2025'}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'inicio_vacaciones': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fin_vacaciones': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }