from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from admision.models import PeriodoAdmision


class Command(BaseCommand):
    help = 'Configura datos iniciales para el proceso de admisión'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            default=datetime.now().year,
            help='Año del período de admisión (por defecto: año actual)'
        )

    def handle(self, *args, **options):
        year = options['year']
        
        # Crear período de admisión si no existe
        periodo_nombre = f"Admisión {year}"
        
        # Crear una instancia temporal para obtener el formulario base por defecto
        temp_periodo = PeriodoAdmision(nombre=periodo_nombre, año=year)
        formulario_base_default = temp_periodo.get_formulario_base_default()
        
        periodo, created = PeriodoAdmision.objects.get_or_create(
            nombre=periodo_nombre,
            año=year,
            defaults={
                'fecha_inicio': timezone.now(),
                'fecha_fin': timezone.now() + timedelta(days=90),  # 3 meses
                'activo': True,
                'descripcion': f'Proceso de admisión para el ciclo escolar {year}-{year+1}',
                'formulario_base': formulario_base_default,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Período de admisión "{periodo_nombre}" creado exitosamente')
            )
            self.stdout.write(f'  - Fecha inicio: {periodo.fecha_inicio.strftime("%d/%m/%Y %H:%M")}')
            self.stdout.write(f'  - Fecha fin: {periodo.fecha_fin.strftime("%d/%m/%Y %H:%M")}')
            self.stdout.write(f'  - Estado: {"Activo" if periodo.activo else "Inactivo"}')
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠ El período "{periodo_nombre}" ya existe')
            )
        
        # Verificar que tenga formulario base
        if not periodo.formulario_base or not periodo.formulario_base.get('campos'):
            periodo.formulario_base = periodo.get_formulario_base_default()
            periodo.save()
            self.stdout.write(
                self.style.SUCCESS('✓ Formulario base configurado automáticamente')
            )
        
        self.stdout.write(
            self.style.SUCCESS('\n🎓 Proceso de admisión configurado correctamente!')
        )
        self.stdout.write('Puedes acceder a:')
        self.stdout.write('  - Formulario público: /admision/')
        self.stdout.write('  - Panel administrativo: /admision/admin/')