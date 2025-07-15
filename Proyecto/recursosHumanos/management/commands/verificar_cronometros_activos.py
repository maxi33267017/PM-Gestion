from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q
from datetime import timedelta
from recursosHumanos.models import SesionCronometro, AlertaCronometro
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Verifica cronómetros activos por más de 2 horas y envía alertas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar sin enviar emails (solo mostrar qué se haría)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('Ejecutando en modo DRY-RUN (no se enviarán emails)')
            )
        
        # Buscar cronómetros activos por más de 2 horas
        tiempo_limite = timezone.now() - timedelta(hours=2)
        
        cronometros_activos = SesionCronometro.objects.filter(
            hora_inicio__lt=tiempo_limite,
            activa=True
        ).select_related('tecnico', 'actividad', 'servicio')
        
        self.stdout.write(f'Encontrados {cronometros_activos.count()} cronómetros activos por más de 2 horas')
        
        alertas_enviadas = 0
        
        for sesion in cronometros_activos:
            # Verificar si ya se envió una alerta reciente (últimas 2 horas)
            alerta_reciente = AlertaCronometro.objects.filter(
                sesion=sesion,
                fecha_creacion__gte=timezone.now() - timedelta(hours=2)
            ).first()
            
            if alerta_reciente:
                self.stdout.write(
                    f'  - Ya existe alerta reciente para {sesion.tecnico.nombre} '
                    f'(actividad: {sesion.actividad.nombre})'
                )
                continue
            
            # Calcular tiempo transcurrido
            tiempo_transcurrido = timezone.now() - sesion.hora_inicio
            horas = int(tiempo_transcurrido.total_seconds() // 3600)
            minutos = int((tiempo_transcurrido.total_seconds() % 3600) // 60)
            tiempo_str = f"{horas}h {minutos}m"
            
            self.stdout.write(
                f'  - Enviando alerta para {sesion.tecnico.nombre} '
                f'(actividad: {sesion.actividad.nombre}, tiempo: {tiempo_str})'
            )
            
            if not dry_run:
                try:
                    # Crear alerta usando el método del modelo
                    alerta = AlertaCronometro.crear_alerta_cronometro_activo(sesion)
                    
                    # Enviar el email
                    alerta.enviar_email()
                    
                    alertas_enviadas += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'    ✓ Alerta enviada exitosamente')
                    )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'    ✗ Error enviando alerta: {str(e)}')
                    )
                    logger.error(f'Error enviando alerta para sesion {sesion.id}: {str(e)}')
            else:
                alertas_enviadas += 1
                self.stdout.write(
                    self.style.SUCCESS(f'    ✓ Alerta simulada (DRY-RUN)')
                )
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'\nDRY-RUN completado: {alertas_enviadas} alertas simuladas')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nProceso completado: {alertas_enviadas} alertas enviadas')
            ) 