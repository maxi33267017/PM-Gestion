from django.core.management.base import BaseCommand
from gestionDeTaller.models import LogHerramienta


class Command(BaseCommand):
    help = 'Inspecciona los logs de herramientas para ver el estado del campo usuario'

    def handle(self, *args, **options):
        self.stdout.write('Inspeccionando logs de herramientas...')
        
        logs = LogHerramienta.objects.all().order_by('-fecha')
        
        if not logs.exists():
            self.stdout.write('No hay logs en el sistema')
            return
        
        self.stdout.write(f'Total de logs: {logs.count()}')
        
        for log in logs[:10]:  # Mostrar solo los últimos 10
            usuario_info = f"ID: {log.usuario.id}, Nombre: {log.usuario.get_full_name()}" if log.usuario else "None"
            self.stdout.write(
                f'Log {log.id}: {log.fecha} | Usuario: {usuario_info} | '
                f'Acción: {log.accion} | Herramienta: {log.herramienta.codigo}'
            )
        
        # Estadísticas
        logs_con_usuario = logs.filter(usuario__isnull=False).count()
        logs_sin_usuario = logs.filter(usuario__isnull=True).count()
        
        self.stdout.write(f'\nEstadísticas:')
        self.stdout.write(f'- Logs con usuario: {logs_con_usuario}')
        self.stdout.write(f'- Logs sin usuario: {logs_sin_usuario}')
        
        if logs_sin_usuario > 0:
            self.stdout.write(self.style.WARNING(f'¡Hay {logs_sin_usuario} logs sin usuario!'))
        else:
            self.stdout.write(self.style.SUCCESS('Todos los logs tienen usuario asignado')) 