from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    help = "Añade un usuario a un grupo (crea el grupo si no existe). Opcionalmente marca el usuario como staff."

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True, help='Nombre de usuario a asignar al grupo')
        parser.add_argument('--group', default='ServiciosEscolares', help='Nombre del grupo (por defecto: ServiciosEscolares)')
        parser.add_argument('--staff', action='store_true', help='Marcar al usuario como staff')

    def handle(self, *args, **options):
        username = options['username']
        group_name = options['group']
        set_staff = options['staff']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"Usuario '{username}' no existe")

        group, created = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)

        if set_staff and not user.is_staff:
            user.is_staff = True
            user.save(update_fields=['is_staff'])

        result = f"Usuario '{username}' añadido al grupo '{group_name}'."
        if created:
            result += " Grupo creado."
        if set_staff:
            result += " Marcado como staff."

        self.stdout.write(self.style.SUCCESS(result))