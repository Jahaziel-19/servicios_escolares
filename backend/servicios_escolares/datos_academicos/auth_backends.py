from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate
from .models import Alumno
import logging

logger = logging.getLogger(__name__)

class AlumnoAuthBackend(BaseBackend):
    """
    Backend de autenticación personalizado para alumnos.
    Autenticación con matrícula y contraseña (CURP por defecto).
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Autentica un alumno usando matrícula y contraseña.
        - username: matrícula del alumno
        - password: contraseña (CURP por defecto)
        """
        try:
            if not username or not password:
                return None
            
            # Buscar alumno por matrícula
            try:
                alumno = Alumno.objects.get(matricula=username.upper())
            except Alumno.DoesNotExist:
                return None
            
            # Verificar contraseña (por defecto es el CURP)
            if password.upper() == alumno.curp.upper():
                return self._create_or_update_user(alumno)
            
            return None
            
        except Exception as e:
            logger.error(f"Error en autenticación: {e}")
            return None
    
    def _create_or_update_user(self, alumno):
        """Crea o actualiza el usuario de Django basado en el alumno"""
        try:
            # Usar la matrícula como username para el usuario de Django
            username = alumno.matricula
            
            # Intentar obtener el usuario existente
            try:
                user = User.objects.get(username=username)
                # Actualizar información del usuario
                user.email = alumno.email or ''
                user.first_name = alumno.nombre or ''
                user.last_name = f"{alumno.apellido_paterno or ''} {alumno.apellido_materno or ''}".strip()
                user.save()
            except User.DoesNotExist:
                # Crear nuevo usuario
                user = User.objects.create_user(
                    username=username,
                    email=alumno.email or '',
                    first_name=alumno.nombre or '',
                    last_name=f"{alumno.apellido_paterno or ''} {alumno.apellido_materno or ''}".strip(),
                    password=alumno.curp  # Establecer CURP como contraseña por defecto
                )
            
            # Asignar el grupo 'Alumno' al usuario si no lo tiene
            try:
                alumno_group = Group.objects.get(name='Alumno')
                if not user.groups.filter(name='Alumno').exists():
                    user.groups.add(alumno_group)
                    logger.info(f"Grupo 'Alumno' asignado al usuario {username}")
            except Group.DoesNotExist:
                logger.warning("El grupo 'Alumno' no existe. Ejecute el comando create_alumno_group")
            
            return user
            
        except Exception as e:
            logger.error(f"Error al crear/actualizar usuario: {e}")
            return None

    def get_user(self, user_id):
        """Obtiene un usuario por su ID"""
        try:
            user = User.objects.get(pk=user_id)
            # Verificar que el usuario tenga un alumno asociado
            try:
                Alumno.objects.get(matricula=user.username)
                return user
            except Alumno.DoesNotExist:
                return None
        except User.DoesNotExist:
            return None