from django.core.management.base import BaseCommand
from gestionDeTaller.models import LogHerramienta, ReservaHerramienta
from recursosHumanos.models import Usuario


class Command(BaseCommand):
    help = 'Corrige los logs de herramientas que tienen usuario=None'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando corrección de logs...')
        
        # Obtener logs con usuario=None
        logs_sin_usuario = LogHerramienta.objects.filter(usuario__isnull=True)
        self.stdout.write(f'Encontrados {logs_sin_usuario.count()} logs sin usuario')
        
        # Obtener el primer usuario disponible como fallback
        try:
            usuario_default = Usuario.objects.first()
            if not usuario_default:
                self.stdout.write(self.style.ERROR('No hay usuarios en el sistema'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al obtener usuario por defecto: {e}'))
            return
        
        logs_corregidos = 0
        
        for log in logs_sin_usuario:
            try:
                # Intentar obtener el usuario de la reserva asociada
                if log.reserva and log.reserva.usuario:
                    log.usuario = log.reserva.usuario
                    self.stdout.write(f'Log {log.id}: Usuario obtenido de reserva {log.reserva.id}')
                else:
                    # Usar usuario por defecto
                    log.usuario = usuario_default
                    self.stdout.write(f'Log {log.id}: Usando usuario por defecto')
                
                log.save()
                logs_corregidos += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error al corregir log {log.id}: {e}'))
        
        self.stdout.write(
            self.style.SUCCESS(f'Proceso completado. {logs_corregidos} logs corregidos.')
        )
        
        # Verificar logs restantes
        logs_restantes = LogHerramienta.objects.filter(usuario__isnull=True).count()
        if logs_restantes > 0:
            self.stdout.write(
                self.style.WARNING(f'Aún quedan {logs_restantes} logs sin usuario')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Todos los logs tienen usuario asignado')
            ) 