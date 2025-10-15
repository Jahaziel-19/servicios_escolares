from django import forms
from .models import Plantilla

class PlantillaForm(forms.ModelForm):
    class Meta:
        model = Plantilla
        fields = ['nombre', 'archivo']
