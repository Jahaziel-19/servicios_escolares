from django import forms
from .models import Tramite

class TramiteForm(forms.ModelForm):
    class Meta:
        model = Tramite
        fields = ['alumno', 'tipo', 'plantilla', 'observaciones']
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 3, 'class':'form-control'}),
        }
