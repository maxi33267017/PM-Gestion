#!/usr/bin/env python
"""
Script para hacer backup de la base de datos local
Migración de datos a la web online
"""

import os
import sys
import django
import json
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings')
django.setup()

from django.core import serializers
from django.db import connection
from recursosHumanos.models import Provincia, Ciudad, Sucursal, Usuario

def create_backup_directory():
    """Crear directorio para los backups"""
    backup_dir = f"backups_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def backup_table(model_class, backup_dir, filename):
    """Hacer backup de una tabla específica"""
    try:
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
        return filepath, count
        
    except Exception as e:
        print(f"❌ Error en {filename}: {str(e)}")
        return None, 0

def backup_provincias(backup_dir):
    """Backup de provincias"""
    print("\n🌍 Haciendo backup de PROVINCIAS...")
    return backup_table(Provincia, backup_dir, '01_provincias.json')

def backup_ciudades(backup_dir):
    """Backup de ciudades"""
    print("\n🏙️ Haciendo backup de CIUDADES...")
    return backup_table(Ciudad, backup_dir, '02_ciudades.json')

def backup_sucursales(backup_dir):
    """Backup de sucursales"""
    print("\n🏢 Haciendo backup de SUCURSALES...")
    return backup_table(Sucursal, backup_dir, '03_sucursales.json')

def backup_usuarios(backup_dir):
    """Backup de usuarios"""
    print("\n👥 Haciendo backup de USUARIOS...")
    
    # Backup de usuarios personalizados (modelo principal)
    custom_users = Usuario.objects.all()
    custom_data = serializers.serialize('json', custom_users, indent=2)
    custom_filepath = os.path.join(backup_dir, '04_usuarios.json')
    with open(custom_filepath, 'w', encoding='utf-8') as f:
        f.write(custom_data)
    
    print(f"✅ 04_usuarios.json: {custom_users.count()} registros exportados")
    
    return custom_filepath

def create_summary(backup_dir, results):
    """Crear resumen del backup"""
    summary = {
        'fecha_backup': datetime.now().isoformat(),
        'directorio': backup_dir,
        'resumen': results
    }
    
    summary_file = os.path.join(backup_dir, 'RESUMEN_BACKUP.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n📋 Resumen guardado en: {summary_file}")

def main():
    """Función principal"""
    print("🚀 Iniciando backup de base de datos local")
    print("=" * 50)
    
    # Crear directorio de backup
    backup_dir = create_backup_directory()
    print(f"📁 Directorio de backup: {backup_dir}")
    
    results = {}
    
    # 1. Backup de provincias
    filepath, count = backup_provincias(backup_dir)
    results['provincias'] = {'archivo': filepath, 'registros': count}
    
    # 2. Backup de ciudades
    filepath, count = backup_ciudades(backup_dir)
    results['ciudades'] = {'archivo': filepath, 'registros': count}
    
    # 3. Backup de sucursales
    filepath, count = backup_sucursales(backup_dir)
    results['sucursales'] = {'archivo': filepath, 'registros': count}
    
    # 4. Backup de usuarios
    usuarios_file = backup_usuarios(backup_dir)
    results['usuarios'] = {
        'archivo': usuarios_file, 
        'registros': Usuario.objects.count()
    }
    
    # Crear resumen
    create_summary(backup_dir, results)
    
    print("\n" + "=" * 50)
    print("🎉 Backup completado exitosamente!")
    print(f"📁 Todos los archivos están en: {backup_dir}")
    print("\n📋 Próximos pasos:")
    print("1. Revisar los archivos JSON generados")
    print("2. Verificar que los datos sean correctos")
    print("3. Proceder con la migración a la base de datos online")

if __name__ == '__main__':
    main() 