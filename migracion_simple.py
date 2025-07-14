#!/usr/bin/env python
"""
Script simple para migrar datos a la base de datos online
Ejecutar desde tu máquina local
"""

import os
import sys
import django
import json
from datetime import datetime

# Configurar Django para desarrollo (MySQL local)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings')
django.setup()

from django.core import serializers

# Importar solo los modelos básicos para evitar errores
from recursosHumanos.models import Provincia, Ciudad, Sucursal, Usuario
from clientes.models import Cliente, ContactoCliente, Equipo, ModeloEquipo, ModeloMotor, TipoEquipo
from gestionDeTaller.models import Servicio, PreOrden, Repuesto

def backup_essential_data():
    """Backup de datos esenciales"""
    print("🚀 Iniciando backup de datos esenciales")
    print("=" * 50)
    
    # Crear directorio de backup
    backup_dir = f"backup_esencial_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    print(f"📁 Directorio: {backup_dir}")
    
    # Lista de modelos a respaldar
    models_to_backup = [
        (Provincia, '01_provincias.json', 'Provincias'),
        (Ciudad, '02_ciudades.json', 'Ciudades'),
        (Sucursal, '03_sucursales.json', 'Sucursales'),
        (Usuario, '04_usuarios.json', 'Usuarios'),
        (Cliente, '05_clientes.json', 'Clientes'),
        (ContactoCliente, '06_contactos_clientes.json', 'Contactos Clientes'),
        (Equipo, '07_equipos.json', 'Equipos'),
        (ModeloEquipo, '08_modelos_equipos.json', 'Modelos Equipos'),
        (ModeloMotor, '09_modelos_motores.json', 'Modelos Motores'),
        (TipoEquipo, '10_tipos_equipos.json', 'Tipos Equipos'),
        (Servicio, '11_servicios.json', 'Servicios'),
        (PreOrden, '12_pre_ordenes.json', 'Pre-órdenes'),
        (Repuesto, '13_repuestos.json', 'Repuestos'),
    ]
    
    results = {}
    
    for model_class, filename, description in models_to_backup:
        try:
            print(f"\n📊 Haciendo backup de {description}...")
            
            # Obtener todos los registros
            objects = model_class.objects.all()
            
            # Serializar a JSON
            data = serializers.serialize('json', objects, indent=2)
            
            # Guardar en archivo
            filepath = os.path.join(backup_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(data)
            
            count = objects.count()
            print(f"✅ {filename}: {count} registros exportados")
            results[description] = {'archivo': filepath, 'registros': count}
            
        except Exception as e:
            print(f"❌ Error en {description}: {str(e)}")
            results[description] = {'archivo': None, 'registros': 0}
    
    # Crear resumen
    summary = {
        'fecha_backup': datetime.now().isoformat(),
        'directorio': backup_dir,
        'resumen': results
    }
    
    summary_file = os.path.join(backup_dir, 'RESUMEN_BACKUP_ESENCIAL.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n📋 Resumen guardado en: {summary_file}")
    
    # Estadísticas finales
    total_tables = len([v for v in results.values() if v['archivo'] is not None])
    total_records = sum([v['registros'] for v in results.values()])
    
    print("\n" + "=" * 50)
    print("🎉 Backup esencial completado!")
    print(f"📊 Tablas exportadas: {total_tables}")
    print(f"📊 Registros totales: {total_records}")
    print(f"📁 Directorio: {backup_dir}")
    
    print("\n📋 Próximos pasos:")
    print("1. Subir el directorio de backup al servidor")
    print("2. Ejecutar el script de carga en Render.com")
    print("3. Verificar que los datos se cargaron correctamente")

if __name__ == '__main__':
    backup_essential_data() 