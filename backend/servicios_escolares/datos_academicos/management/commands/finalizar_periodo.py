from django.core.management.base import BaseCommand
from django.utils import timezone

from servicios_escolares.datos_academicos.models import Alumno, PeriodoEscolar


class Command(BaseCommand):
    help = 'Al finalizar periodos, transiciona alumnos a estatus "No inscrito" automáticamente.'

    def handle(self, *args, **options):
        hoy = timezone.now().date()
        periodos_finalizados = PeriodoEscolar.objects.filter(fecha_fin__lt=hoy)
        activos = PeriodoEscolar.objects.filter(activo=True).exists()

        if activos:
            self.stdout.write(self.style.WARNING('Existe un periodo activo. No se realizará la transición automática.'))
            return

        total_actualizados = Alumno.objects.exclude(estatus='No inscrito').update(estatus='No inscrito')
        self.stdout.write(self.style.SUCCESS(f'Alumnos actualizados a "No inscrito": {total_actualizados}'))