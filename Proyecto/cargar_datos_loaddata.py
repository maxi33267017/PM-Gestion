#!/usr/bin/env python
"""
Script para cargar datos usando Django loaddata
"""

import os
import subprocess
import sys

def load_data_with_loaddata():
    """Cargar datos usando Django loaddata"""
    print("🚀 Cargando datos usando Django loaddata")
    print("=" * 50)
    
    # Configurar variables de entorno
    os.environ['DJANGO_SETTINGS_MODULE'] = 'PatagoniaMaquinarias.settings_render'
    
    # Lista de archivos a cargar en orden
    files_to_load = [
        'backups_20250714_174234/01_provincias.json',
        'backups_20250714_174234/02_ciudades.json',
        'backups_20250714_174234/03_sucursales.json',
        'backups_20250714_174234/04_usuarios.json',
    ]
    
    success_count = 0
    
    for file_path in files_to_load:
        if not os.path.exists(file_path):
            print(f"❌ Archivo no encontrado: {file_path}")
            continue
            
        print(f"\n📊 Cargando {file_path}...")
        
        try:
            # Ejecutar loaddata
            result = subprocess.run([
                'python', 'manage.py', 'loaddata', file_path
            ], capture_output=True, text=True, cwd='/app/Proyecto')
            
            if result.returncode == 0:
                print(f"✅ {file_path} cargado exitosamente")
                print(f"   {result.stdout.strip()}")
                success_count += 1
            else:
                print(f"❌ Error cargando {file_path}")
                print(f"   Error: {result.stderr.strip()}")
                
        except Exception as e:
            print(f"❌ Excepción cargando {file_path}: {str(e)}")
    
    print("\n" + "=" * 50)
    print(f"🎉 Proceso completado: {success_count}/{len(files_to_load)} archivos cargados")
    
    if success_count == len(files_to_load):
        print("✅ Todos los archivos se cargaron correctamente")
    else:
        print("⚠️  Algunos archivos no se pudieron cargar")

if __name__ == '__main__':
    load_data_with_loaddata() 