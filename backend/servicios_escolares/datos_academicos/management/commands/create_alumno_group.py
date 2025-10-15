from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from datos_academicos.models import Alumno, Calificacion, Tramite

class Command(BaseCommand):
    help = 'Crea el grupo Alumno y asigna permisos básicos'

    def handle(self, *args, **options):
        # Crear el grupo Alumno si no existe
        alumno_group, created = Group.objects.get_or_create(name='Alumno')
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Grupo "Alumno" creado exitosamente')
            )
        else:
            self.stdout.write(
                self.style.WARNING('El grupo "Alumno" ya existe')
            )

        # Obtener content types para los modelos relevantes
        alumno_ct = ContentType.objects.get_for_model(Alumno)
        calificacion_ct = ContentType.objects.get_for_model(Calificacion)
        tramite_ct = ContentType.objects.get_for_model(Tramite)

        # Permisos básicos para alumnos (solo lectura de sus propios datos)
        permissions_to_add = [
            # Permisos para ver sus propios datos de alumno
            Permission.objects.get(content_type=alumno_ct, codename='view_alumno'),
            # Permisos para ver sus propias calificaciones
            Permission.objects.get(content_type=calificacion_ct, codename='view_calificacion'),
            # Permisos para ver y crear trámites
            Permission.objects.get(content_type=tramite_ct, codename='view_tramite'),
            Permission.objects.get(content_type=tramite_ct, codename='add_tramite'),
        ]

        # Asignar permisos al grupo
        for permission in permissions_to_add:
            alumno_group.permissions.add(permission)
            self.stdout.write(f'Permiso "{permission.name}" agregado al grupo Alumno')

        self.stdout.write(
            self.style.SUCCESS('Configuración del grupo Alumno completada')
        )