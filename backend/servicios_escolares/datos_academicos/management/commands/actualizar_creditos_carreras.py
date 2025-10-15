from django.core.management.base import BaseCommand
from datos_academicos.models import Carrera


class Command(BaseCommand):
    help = 'Actualiza los créditos totales de todas las carreras basándose en sus materias'

    def add_arguments(self, parser):
        parser.add_argument(
            '--carrera',
            type=str,
            help='Clave de la carrera específica a actualizar (opcional)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué cambios se harían sin aplicarlos',
        )

    def handle(self, *args, **options):
        carrera_clave = options.get('carrera')
        dry_run = options.get('dry_run', False)
        
        if carrera_clave:
            try:
                carreras = [Carrera.objects.get(clave=carrera_clave)]
                self.stdout.write(f"Procesando carrera específica: {carrera_clave}")
            except Carrera.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"No se encontró la carrera con clave: {carrera_clave}")
                )
                return
        else:
            carreras = Carrera.objects.all()
            self.stdout.write(f"Procesando todas las carreras ({carreras.count()} encontradas)")

        actualizadas = 0
        sin_cambios = 0
        
        for carrera in carreras:
            creditos_calculados = carrera.calcular_creditos_totales()
            creditos_actuales = carrera.creditos_totales
            
            if creditos_calculados != creditos_actuales:
                if dry_run:
                    self.stdout.write(
                        f"[DRY RUN] {carrera.clave} - {carrera.nombre}: "
                        f"{creditos_actuales} → {creditos_calculados} créditos"
                    )
                else:
                    carrera.creditos_totales = creditos_calculados
                    carrera.save(update_fields=['creditos_totales'])
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ {carrera.clave} - {carrera.nombre}: "
                            f"{creditos_actuales} → {creditos_calculados} créditos"
                        )
                    )
                actualizadas += 1
            else:
                sin_cambios += 1
                if options.get('verbosity', 1) >= 2:
                    self.stdout.write(
                        f"- {carrera.clave} - {carrera.nombre}: "
                        f"{creditos_actuales} créditos (sin cambios)"
                    )

        # Resumen
        self.stdout.write("\n" + "="*50)
        if dry_run:
            self.stdout.write(self.style.WARNING("MODO DRY RUN - No se aplicaron cambios"))
        
        self.stdout.write(f"Carreras actualizadas: {actualizadas}")
        self.stdout.write(f"Carreras sin cambios: {sin_cambios}")
        self.stdout.write(f"Total procesadas: {actualizadas + sin_cambios}")
        
        if actualizadas > 0 and not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ Se actualizaron exitosamente {actualizadas} carreras"
                )
            )