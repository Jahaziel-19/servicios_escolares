from django import forms

class UploadExcelForm(forms.Form):
    archivo = forms.FileField(
        label='Archivo Excel',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'placeholder': 'Selecciona tu archivo .xlsx'
        })
    )
    hoja = forms.CharField(
        label='Nombre de la hoja',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ejemplo: Hoja1'
        })
    )
    rango = forms.CharField(
        label='Rango de celdas',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ejemplo: A1:D10'
        })
    )

class MapeoCamposForm(forms.Form):
    """
    Formulario dinámico para asignar columnas Excel a campos modelo.
    """
    def __init__(self, campos_modelo, columnas_excel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        opciones = [('', '---')] + [(col, col) for col in columnas_excel]
        for campo in campos_modelo:
            self.fields[campo] = forms.ChoiceField(choices=opciones, required=False, label=f"Asignar columna para '{campo}'")