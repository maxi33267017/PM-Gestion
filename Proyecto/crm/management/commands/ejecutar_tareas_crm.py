from django.core.management.base import BaseCommand
from crm.views import ejecutar_tareas_pendientes


class Command(BaseCommand):
    help = 'Ejecuta las tareas programadas del CRM (emails de recordatorio, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada',
        )

    def handle(self, *args, **options):
        verbose = options['verbose']
        
        if verbose:
            self.stdout.write('🔍 Iniciando ejecución de tareas programadas...')
        
        # Ejecutar tareas pendientes
        tareas_ejecutadas = ejecutar_tareas_pendientes()
        
        if verbose:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Se ejecutaron {tareas_ejecutadas} tareas programadas')
            )
        else:
            self.stdout.write(f'{tareas_ejecutadas}')
