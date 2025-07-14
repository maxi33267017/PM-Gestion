from django.core.management.base import BaseCommand
from django.db import transaction
import pandas as pd
from gestionDeTaller.models import HerramientaPersonal, ItemHerramientaPersonal
from recursosHumanos.models import Usuario
import os

class Command(BaseCommand):
    help = 'Importa items desde un archivo Excel a las cajas de herramientas existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='Proyecto/listado_93_piezas_completo.xlsx',
            help='Ruta al archivo Excel con los items'
        )
        parser.add_argument(
            '--distribute',
            action='store_true',
            help='Distribuir items entre las cajas de herramientas'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        distribute = options['distribute']
        
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'El archivo {file_path} no existe')
            )
            return
        
        try:
            # Leer el archivo Excel
            df = pd.read_excel(file_path)
            self.stdout.write(f'Archivo leído: {len(df)} items encontrados')
            
            # Verificar columnas requeridas
            required_columns = ['Descripción', 'Cantidad']
            if not all(col in df.columns for col in required_columns):
                self.stdout.write(
                    self.style.ERROR(f'El archivo debe contener las columnas: {required_columns}')
                )
                return
            
            # Obtener las cajas de herramientas existentes
            cajas = HerramientaPersonal.objects.all()
            if not cajas.exists():
                self.stdout.write(
                    self.style.ERROR('No hay cajas de herramientas en la base de datos')
                )
                return
            
            self.stdout.write(f'Cajas de herramientas encontradas: {cajas.count()}')
            
            # Contador de items creados
            total_items_creados = 0
            
            with transaction.atomic():
                if distribute:
                    # Distribuir items entre las cajas
                    self.stdout.write('Distribuyendo items entre las cajas...')
                    
                    for index, row in df.iterrows():
                        # Seleccionar caja de forma rotativa
                        caja = cajas[index % cajas.count()]
                        
                        # Crear el item
                        item = ItemHerramientaPersonal.objects.create(
                            herramienta=caja,
                            nombre=row['Descripción'],
                            descripcion=f"Item importado desde Excel - {row['Descripción']}",
                            cantidad=row['Cantidad'],
                            estado='BUENO',
                            observaciones='Importado automáticamente desde Excel'
                        )
                        total_items_creados += 1
                        
                        if (index + 1) % 10 == 0:
                            self.stdout.write(f'Procesados {index + 1} items...')
                
                else:
                    # Agregar todos los items a cada caja
                    self.stdout.write('Agregando todos los items a cada caja...')
                    
                    for caja in cajas:
                        tecnico = caja.asignacion_actual.tecnico if caja.asignacion_actual else None
                        tecnico_nombre = tecnico.get_full_name() if tecnico else 'Sin asignar'
                        self.stdout.write(f'Procesando caja: {caja.nombre} (Técnico: {tecnico_nombre})')
                        
                        for index, row in df.iterrows():
                            # Verificar si el item ya existe en esta caja
                            if not ItemHerramientaPersonal.objects.filter(
                                herramienta=caja,
                                nombre=row['Descripción']
                            ).exists():
                                item = ItemHerramientaPersonal.objects.create(
                                    herramienta=caja,
                                    nombre=row['Descripción'],
                                    descripcion=f"Item importado desde Excel - {row['Descripción']}",
                                    cantidad=row['Cantidad'],
                                    estado='BUENO',
                                    observaciones='Importado automáticamente desde Excel'
                                )
                                total_items_creados += 1
                        
                        self.stdout.write(f'  - Items agregados a {caja.nombre}: {len(df)}')
            
            # Mostrar resumen
            self.stdout.write(
                self.style.SUCCESS(
                    f'Importación completada exitosamente!\n'
                    f'Total de items creados: {total_items_creados}\n'
                    f'Items por caja: {total_items_creados // cajas.count() if distribute else len(df)}'
                )
            )
            
            # Mostrar estadísticas por caja
            self.stdout.write('\nEstadísticas por caja:')
            for caja in cajas:
                items_count = caja.items.count()
                self.stdout.write(f'  - {caja.nombre} ({caja.tecnico.nombre}): {items_count} items')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error durante la importación: {str(e)}')
            )
            raise 