from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from .models import Alumno

class AlumnoLoginForm(forms.Form):
    """
    Formulario de login para alumnos.
    Autenticación con matrícula y contraseña (CURP por defecto).
    """
    matricula = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu matrícula',
            'autocomplete': 'username',
            'required': True
        }),
        label='Matrícula'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu contraseña',
            'autocomplete': 'current-password',
            'required': True
        }),
        label='Contraseña'
    )
    
    def clean(self):
        """Validar las credenciales del alumno"""
        cleaned_data = super().clean()
        matricula = cleaned_data.get('matricula')
        password = cleaned_data.get('password')
        
        if matricula and password:
            # Autenticar usando el backend personalizado
            user = authenticate(
                username=matricula,
                password=password
            )
            
            if user is None:
                raise ValidationError(
                    'Matrícula o contraseña incorrectos. '
                    'Verifica tus datos e intenta nuevamente.'
                )
            
            if not user.is_active:
                raise ValidationError('Esta cuenta está desactivada.')
            
            # Guardar el usuario autenticado
            cleaned_data['user'] = user
        
        return cleaned_data
    
    def get_user(self):
        """Obtiene el usuario autenticado"""
        return self.cleaned_data.get('user')


class AlumnoPasswordResetForm(forms.Form):
    """
    Formulario para solicitar restablecimiento de contraseña.
    """
    matricula = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu matrícula',
            'required': True
        }),
        label='Matrícula'
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu correo institucional',
            'required': True
        }),
        label='Correo Electrónico'
    )
    
    def clean(self):
        """Validar que la matrícula y email correspondan a un alumno"""
        cleaned_data = super().clean()
        matricula = cleaned_data.get('matricula')
        email = cleaned_data.get('email')
        
        if matricula and email:
            try:
                alumno = Alumno.objects.get(
                    matricula=matricula.upper(),
                    email=email.lower()
                )
                cleaned_data['alumno'] = alumno
            except Alumno.DoesNotExist:
                raise ValidationError(
                    'No se encontró un alumno con esa matrícula y correo electrónico.'
                )
        
        return cleaned_data
    
    def get_alumno(self):
        """Obtiene el alumno encontrado"""
        return self.cleaned_data.get('alumno')


class AlumnoPasswordChangeForm(forms.Form):
    """
    Formulario para cambiar la contraseña del alumno.
    """
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña actual',
            'required': True
        }),
        label='Contraseña Actual'
    )
    
    new_password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nueva contraseña (mínimo 8 caracteres)',
            'required': True
        }),
        label='Nueva Contraseña'
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirma tu nueva contraseña',
            'required': True
        }),
        label='Confirmar Nueva Contraseña'
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_current_password(self):
        """Validar la contraseña actual"""
        current_password = self.cleaned_data.get('current_password')
        
        if current_password:
            # Verificar la contraseña actual
            if not self.user.check_password(current_password):
                raise ValidationError('La contraseña actual es incorrecta.')
        
        return current_password
    
    def clean(self):
        """Validar que las nuevas contraseñas coincidan"""
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password:
            if new_password != confirm_password:
                raise ValidationError('Las nuevas contraseñas no coinciden.')
        
        return cleaned_data
    
    def save(self):
        """Guardar la nueva contraseña"""
        new_password = self.cleaned_data['new_password']
        self.user.set_password(new_password)
        self.user.save()
        return self.user