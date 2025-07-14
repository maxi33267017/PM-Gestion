#!/usr/bin/env python3
"""
Script para cargar los backups por apps en la base de datos online
Usa Django loaddata con la sintaxis correcta
"""

import os
import sys
import django
import json
import glob
from datetime import datetime

# Configurar Django para usar settings de producción (PostgreSQL)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings_render')
django.setup()

from django.core.management import execute_from_command_line

def cargar_apps_online(backup_dir=None):
    """Cargar todos los datos del backup por apps en la base de datos online"""
    
    # Si no se especifica directorio, buscar el más reciente
    if not backup_dir:
        backup_dirs = glob.glob("backups_apps_*")
        if not backup_dirs:
            print("❌ No se encontraron directorios de backup por apps")
            print("💡 Ejecuta primero: python backup_por_apps.py")
            return False
        
        # Ordenar por fecha y tomar el más reciente
        backup_dirs.sort(reverse=True)
        backup_dir = backup_dirs[0]
    
    print(f"🚀 Cargando datos por apps desde: {backup_dir}")
    print("=" * 60)
    
    # Verificar que el directorio existe
    if not os.path.exists(backup_dir):
        print(f"❌ El directorio {backup_dir} no existe")
        return False
    
    # Buscar archivos JSON de backup (excluyendo el resumen)
    json_files = glob.glob(os.path.join(backup_dir, "*.json"))
    json_files = [f for f in json_files if not f.endswith('RESUMEN_BACKUP_APPS.json')]
    
    if not json_files:
        print(f"❌ No se encontraron archivos JSON en {backup_dir}")
        return False
    
    # Ordenar archivos por número (01_, 02_, etc.)
    json_files.sort()
    
    total_archivos = len(json_files)
    cargados = 0
    fallidos = 0
    errores = []
    
    print(f"📊 Total de archivos a cargar: {total_archivos}")
    print()
    
    for i, archivo in enumerate(json_files, 1):
        filename = os.path.basename(archivo)
        print(f"📊 Cargando {i:2d}/{total_archivos} - {filename}...")
        
        try:
            # Usar execute_from_command_line para ejecutar loaddata
            execute_from_command_line(['manage.py', 'loaddata', archivo])
            print(f"✅ {filename} cargado exitosamente")
            cargados += 1
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error cargando {filename}: {error_msg}")
            errores.append({
                'archivo': filename,
                'error': error_msg
            })
            fallidos += 1
    
    # Mostrar resumen final
    print()
    print("=" * 60)
    print("📋 RESUMEN DE CARGA POR APPS")
    print("=" * 60)
    print(f"📁 Directorio fuente: {backup_dir}")
    print(f"📊 Total de archivos: {total_archivos}")
    print(f"✅ Cargados exitosamente: {cargados}")
    print(f"❌ Fallidos: {fallidos}")
    
    if errores:
        print()
        print("❌ ARCHIVOS CON ERRORES:")
        for error in errores:
            print(f"   - {error['archivo']}: {error['error']}")
    
    print()
    if cargados == total_archivos:
        print("🎉 ¡TODOS los archivos se cargaron correctamente!")
    else:
        print(f"⚠️  {fallidos} archivos fallaron. Revisa los errores arriba.")
    
    return cargados == total_archivos

def cargar_app_especifica(backup_dir=None, app_name=None):
    """Cargar datos de una app específica"""
    
    if not backup_dir:
        backup_dirs = glob.glob("backups_apps_*")
        if not backup_dirs:
            print("❌ No se encontraron directorios de backup por apps")
            return False
        backup_dirs.sort(reverse=True)
        backup_dir = backup_dirs[0]
    
    if not app_name:
        print("❌ Debes especificar el nombre de la app")
        print("💡 Ejemplo: cargar_app_especifica(backup_dir, 'clientes')")
        return False
    
    print(f"🚀 Cargando datos de la app '{app_name}' desde: {backup_dir}")
    print("=" * 50)
    
    # Buscar archivo de la app específica
    pattern = os.path.join(backup_dir, f"*_{app_name}_completo.json")
    json_files = glob.glob(pattern)
    
    if not json_files:
        print(f"❌ No se encontró archivo para la app '{app_name}'")
        return False
    
    archivo = json_files[0]
    filename = os.path.basename(archivo)
    print(f"📊 Cargando {filename}...")
    
    try:
        execute_from_command_line(['manage.py', 'loaddata', archivo])
        print(f"✅ {filename} cargado exitosamente")
        return True
    except Exception as e:
        print(f"❌ Error cargando {filename}: {str(e)}")
        return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Cargar datos por apps en la base de datos online')
    parser.add_argument('--backup-dir', help='Directorio de backup específico')
    parser.add_argument('--app', help='Cargar solo una app específica')
    
    args = parser.parse_args()
    
    if args.app:
        # Cargar solo una app
        cargar_app_especifica(args.backup_dir, args.app)
    else:
        # Cargar todo
        cargar_apps_online(args.backup_dir) 