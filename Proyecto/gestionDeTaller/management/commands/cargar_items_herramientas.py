from django.core.management.base import BaseCommand
from gestionDeTaller.models import HerramientaPersonal, ItemHerramientaPersonal


class Command(BaseCommand):
    help = 'Carga items de ejemplo para herramientas personales existentes'

    def handle(self, *args, **options):
        self.stdout.write('Cargando items de ejemplo para herramientas personales...')
        
        # Datos de items por categoría
        items_por_categoria = {
            'CAJA_HERRAMIENTAS': [
                {'nombre': 'Destornillador Phillips #1', 'cantidad': 1, 'descripcion': 'Destornillador Phillips de 4mm'},
                {'nombre': 'Destornillador Phillips #2', 'cantidad': 1, 'descripcion': 'Destornillador Phillips de 6mm'},
                {'nombre': 'Destornillador Plano 3mm', 'cantidad': 1, 'descripcion': 'Destornillador plano de 3mm'},
                {'nombre': 'Destornillador Plano 4mm', 'cantidad': 1, 'descripcion': 'Destornillador plano de 4mm'},
                {'nombre': 'Llave Allen 3mm', 'cantidad': 1, 'descripcion': 'Llave Allen hexagonal de 3mm'},
                {'nombre': 'Llave Allen 4mm', 'cantidad': 1, 'descripcion': 'Llave Allen hexagonal de 4mm'},
                {'nombre': 'Llave Allen 5mm', 'cantidad': 1, 'descripcion': 'Llave Allen hexagonal de 5mm'},
                {'nombre': 'Llave Allen 6mm', 'cantidad': 1, 'descripcion': 'Llave Allen hexagonal de 6mm'},
                {'nombre': 'Llave Allen 8mm', 'cantidad': 1, 'descripcion': 'Llave Allen hexagonal de 8mm'},
                {'nombre': 'Llave Allen 10mm', 'cantidad': 1, 'descripcion': 'Llave Allen hexagonal de 10mm'},
                {'nombre': 'Alicate Universal', 'cantidad': 1, 'descripcion': 'Alicate universal de 7 pulgadas'},
                {'nombre': 'Alicate de Corte', 'cantidad': 1, 'descripcion': 'Alicate de corte diagonal'},
                {'nombre': 'Martillo', 'cantidad': 1, 'descripcion': 'Martillo de 16 onzas'},
                {'nombre': 'Cinta Métrica', 'cantidad': 1, 'descripcion': 'Cinta métrica de 5 metros'},
                {'nombre': 'Nivel de Burbuja', 'cantidad': 1, 'descripcion': 'Nivel de burbuja de 30cm'},
                {'nombre': 'Escuadra', 'cantidad': 1, 'descripcion': 'Escuadra de 30cm'},
                {'nombre': 'Lápiz', 'cantidad': 2, 'descripcion': 'Lápiz HB'},
                {'nombre': 'Goma de Borrar', 'cantidad': 1, 'descripcion': 'Goma de borrar blanca'},
                {'nombre': 'Papel de Lija', 'cantidad': 3, 'descripcion': 'Papel de lija grano 120'},
                {'nombre': 'Cepillo de Alambre', 'cantidad': 1, 'descripcion': 'Cepillo de alambre pequeño'},
            ],
            'TESTER': [
                {'nombre': 'Multímetro Digital', 'cantidad': 1, 'descripcion': 'Multímetro digital principal'},
                {'nombre': 'Puntas de Prueba', 'cantidad': 1, 'descripcion': 'Puntas de prueba rojas y negras'},
                {'nombre': 'Batería 9V', 'cantidad': 1, 'descripcion': 'Batería de repuesto 9V'},
                {'nombre': 'Manual de Usuario', 'cantidad': 1, 'descripcion': 'Manual de usuario del multímetro'},
            ],
            'HERRAMIENTA_ADICIONAL': [
                {'nombre': 'Herramienta Principal', 'cantidad': 1, 'descripcion': 'Herramienta adicional principal'},
                {'nombre': 'Accesorios', 'cantidad': 1, 'descripcion': 'Accesorios de la herramienta'},
                {'nombre': 'Manual Técnico', 'cantidad': 1, 'descripcion': 'Manual técnico de la herramienta'},
            ],
            'EPP': [
                {'nombre': 'Casco de Seguridad', 'cantidad': 1, 'descripcion': 'Casco de seguridad certificado'},
                {'nombre': 'Gafas de Seguridad', 'cantidad': 1, 'descripcion': 'Gafas de seguridad transparentes'},
                {'nombre': 'Guantes de Trabajo', 'cantidad': 1, 'descripcion': 'Par de guantes de trabajo'},
                {'nombre': 'Botas de Seguridad', 'cantidad': 1, 'descripcion': 'Botas de seguridad con puntera'},
                {'nombre': 'Protección Auditiva', 'cantidad': 1, 'descripcion': 'Protectores auditivos'},
            ]
        }
        
        items_creados = 0
        herramientas_actualizadas = 0
        
        for categoria, items in items_por_categoria.items():
            herramientas = HerramientaPersonal.objects.filter(categoria=categoria)
            
            for herramienta in herramientas:
                # Verificar si ya tiene items
                if herramienta.items.exists():
                    self.stdout.write(f'  ⚠ Herramienta {herramienta.codigo} ya tiene items, saltando...')
                    continue
                
                for item_data in items:
                    try:
                        item, created = ItemHerramientaPersonal.objects.get_or_create(
                            herramienta=herramienta,
                            nombre=item_data['nombre'],
                            defaults={
                                'descripcion': item_data['descripcion'],
                                'cantidad': item_data['cantidad'],
                                'estado': 'PRESENTE'
                            }
                        )
                        
                        if created:
                            items_creados += 1
                            self.stdout.write(f'  ✓ Creado: {item.nombre} para {herramienta.codigo}')
                        else:
                            self.stdout.write(f'  ↻ Ya existe: {item.nombre} en {herramienta.codigo}')
                            
                    except Exception as e:
                        self.stdout.write(f'  ✗ Error creando {item_data["nombre"]} para {herramienta.codigo}: {str(e)}')
                
                herramientas_actualizadas += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Proceso completado. {items_creados} items creados en {herramientas_actualizadas} herramientas.'
            )
        )
        
        # Mostrar estadísticas finales
        self.stdout.write('\nEstadísticas finales:')
        for categoria in ['CAJA_HERRAMIENTAS', 'TESTER', 'HERRAMIENTA_ADICIONAL', 'EPP']:
            herramientas_count = HerramientaPersonal.objects.filter(categoria=categoria).count()
            items_count = ItemHerramientaPersonal.objects.filter(herramienta__categoria=categoria).count()
            self.stdout.write(f'  - {categoria}: {herramientas_count} herramientas, {items_count} items') 