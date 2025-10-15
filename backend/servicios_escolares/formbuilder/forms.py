from django import forms
from .models import Formulario

class FormularioForm(forms.ModelForm):
    class Meta:
        model = Formulario
        fields = ['nombre', 'descripcion', 'estructura']
        widgets = {
            'estructura': forms.Textarea(attrs={'rows': 10}),
        }
