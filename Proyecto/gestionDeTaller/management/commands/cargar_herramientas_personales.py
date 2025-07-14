from django.core.management.base import BaseCommand
from gestionDeTaller.models import HerramientaPersonal
from recursosHumanos.models import Usuario


class Command(BaseCommand):
    help = 'Carga datos iniciales de herramientas personales y EPP'

    def handle(self, *args, **options):
        self.stdout.write('Cargando herramientas personales y EPP...')
        
        # Obtener el primer usuario como creador por defecto
        try:
            usuario_default = Usuario.objects.first()
        except:
            self.stdout.write(self.style.ERROR('No hay usuarios en el sistema'))
            return
        
        # Datos de herramientas personales
        herramientas_data = [
            # Caja de Herramientas
            {
                'codigo': 'CT001',
                'nombre': 'Caja de Herramientas Completa - 93 piezas',
                'categoria': 'CAJA_HERRAMIENTAS',
                'marca': 'Stanley',
                'modelo': 'STMT73795',
                'descripcion': 'Caja de herramientas completa con 93 piezas para técnicos',
                'costo_reposicion': 150000.00,
                'vida_util_meses': 60,
                'activo': True
            },
            {
                'codigo': 'CT002',
                'nombre': 'Caja de Herramientas Completa - 93 piezas',
                'categoria': 'CAJA_HERRAMIENTAS',
                'marca': 'DeWalt',
                'modelo': 'DWST17806',
                'descripcion': 'Caja de herramientas completa con 93 piezas para técnicos',
                'costo_reposicion': 180000.00,
                'vida_util_meses': 60,
                'activo': True
            },
            
            # Testers/Multímetros
            {
                'codigo': 'TM001',
                'nombre': 'Multímetro Digital',
                'categoria': 'TESTER',
                'marca': 'Fluke',
                'modelo': '117',
                'descripcion': 'Multímetro digital profesional para mediciones eléctricas',
                'costo_reposicion': 250000.00,
                'vida_util_meses': 48,
                'activo': True
            },
            {
                'codigo': 'TM002',
                'nombre': 'Tester Digital',
                'categoria': 'TESTER',
                'marca': 'Klein Tools',
                'modelo': 'CL800',
                'descripcion': 'Tester digital para mediciones de corriente y voltaje',
                'costo_reposicion': 180000.00,
                'vida_util_meses': 48,
                'activo': True
            },
            
            # Herramientas Adicionales
            {
                'codigo': 'HA001',
                'nombre': 'Linterna LED Recargable',
                'categoria': 'HERRAMIENTA_ADICIONAL',
                'marca': 'Streamlight',
                'modelo': 'Strion LED',
                'descripcion': 'Linterna LED recargable de alta potencia',
                'costo_reposicion': 45000.00,
                'vida_util_meses': 36,
                'activo': True
            },
            {
                'codigo': 'HA002',
                'nombre': 'Cable USB Tipo C',
                'categoria': 'HERRAMIENTA_ADICIONAL',
                'marca': 'Anker',
                'modelo': 'PowerLine+',
                'descripcion': 'Cable USB Tipo C de alta velocidad',
                'costo_reposicion': 15000.00,
                'vida_util_meses': 24,
                'activo': True
            },
            {
                'codigo': 'HA003',
                'nombre': 'Cargador Portátil',
                'categoria': 'HERRAMIENTA_ADICIONAL',
                'marca': 'Anker',
                'modelo': 'PowerCore 10000',
                'descripcion': 'Batería portátil de 10000mAh',
                'costo_reposicion': 25000.00,
                'vida_util_meses': 36,
                'activo': True
            },
            
            # Elementos de Protección Personal (EPP)
            {
                'codigo': 'EPP001',
                'nombre': 'Casco de Seguridad',
                'categoria': 'EPP',
                'marca': '3M',
                'modelo': 'H-700',
                'descripcion': 'Casco de seguridad industrial clase E',
                'costo_reposicion': 35000.00,
                'vida_util_meses': 24,
                'activo': True
            },
            {
                'codigo': 'EPP002',
                'nombre': 'Gafas de Seguridad',
                'categoria': 'EPP',
                'marca': '3M',
                'modelo': 'SecureFit',
                'descripcion': 'Gafas de seguridad anti-rayas y anti-empañamiento',
                'costo_reposicion': 25000.00,
                'vida_util_meses': 18,
                'activo': True
            },
            {
                'codigo': 'EPP003',
                'nombre': 'Guantes de Trabajo',
                'categoria': 'EPP',
                'marca': 'Mechanix',
                'modelo': 'FastFit',
                'descripcion': 'Guantes de trabajo resistentes al desgaste',
                'costo_reposicion': 20000.00,
                'vida_util_meses': 12,
                'activo': True
            },
            {
                'codigo': 'EPP004',
                'nombre': 'Botas de Seguridad',
                'categoria': 'EPP',
                'marca': 'Timberland',
                'modelo': 'PRO Boondock',
                'descripcion': 'Botas de seguridad con puntera de acero',
                'costo_reposicion': 120000.00,
                'vida_util_meses': 24,
                'activo': True
            },
            {
                'codigo': 'EPP005',
                'nombre': 'Protección Auditiva',
                'categoria': 'EPP',
                'marca': '3M',
                'modelo': 'Ear Classic',
                'descripcion': 'Protectores auditivos desechables',
                'costo_reposicion': 5000.00,
                'vida_util_meses': 6,
                'activo': True
            },
            {
                'codigo': 'EPP006',
                'nombre': 'Protección Respiratoria',
                'categoria': 'EPP',
                'marca': '3M',
                'modelo': '8210',
                'descripcion': 'Respirador desechable N95',
                'costo_reposicion': 8000.00,
                'vida_util_meses': 3,
                'activo': True
            },
            {
                'codigo': 'EPP007',
                'nombre': 'Chaleco Reflectivo',
                'categoria': 'EPP',
                'marca': 'ANSI',
                'modelo': 'Class 2',
                'descripcion': 'Chaleco de alta visibilidad clase 2',
                'costo_reposicion': 30000.00,
                'vida_util_meses': 18,
                'activo': True
            },
            {
                'codigo': 'EPP008',
                'nombre': 'Protección para Cabeza',
                'categoria': 'EPP',
                'marca': '3M',
                'modelo': 'Bump Cap',
                'descripcion': 'Gorra de protección contra golpes',
                'costo_reposicion': 20000.00,
                'vida_util_meses': 24,
                'activo': True
            }
        ]
        
        herramientas_creadas = 0
        herramientas_actualizadas = 0
        
        for data in herramientas_data:
            herramienta, created = HerramientaPersonal.objects.get_or_create(
                codigo=data['codigo'],
                defaults={
                    'nombre': data['nombre'],
                    'categoria': data['categoria'],
                    'marca': data['marca'],
                    'modelo': data['modelo'],
                    'descripcion': data['descripcion'],
                    'costo_reposicion': data['costo_reposicion'],
                    'vida_util_meses': data['vida_util_meses'],
                    'activo': data['activo'],
                    'creado_por': usuario_default
                }
            )
            
            if created:
                herramientas_creadas += 1
                self.stdout.write(f'  ✓ Creada: {herramienta.codigo} - {herramienta.nombre}')
            else:
                # Actualizar datos existentes
                herramienta.nombre = data['nombre']
                herramienta.categoria = data['categoria']
                herramienta.marca = data['marca']
                herramienta.modelo = data['modelo']
                herramienta.descripcion = data['descripcion']
                herramienta.costo_reposicion = data['costo_reposicion']
                herramienta.vida_util_meses = data['vida_util_meses']
                herramienta.activo = data['activo']
                herramienta.save()
                herramientas_actualizadas += 1
                self.stdout.write(f'  ↻ Actualizada: {herramienta.codigo} - {herramienta.nombre}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Proceso completado. {herramientas_creadas} herramientas creadas, '
                f'{herramientas_actualizadas} actualizadas.'
            )
        )
        
        # Mostrar resumen por categoría
        self.stdout.write('\nResumen por categoría:')
        for categoria in ['CAJA_HERRAMIENTAS', 'TESTER', 'HERRAMIENTA_ADICIONAL', 'EPP']:
            count = HerramientaPersonal.objects.filter(categoria=categoria).count()
            self.stdout.write(f'  - {categoria}: {count} herramientas') 