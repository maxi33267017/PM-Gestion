#!/usr/bin/env python3
"""
Script simple para cargar datos usando Django loaddata
Usa la sintaxis correcta con rutas completas
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings_render')
django.setup()

def cargar_datos_loaddata_simple():
    """Cargar datos usando loaddata con rutas completas"""
    print("🚀 Cargando datos usando Django loaddata (sintaxis simple)")
    print("=" * 50)
    
    # Lista de archivos a cargar en orden
    archivos = [
        'fixtures/01_provincias.json',
        'fixtures/02_ciudades.json', 
        'fixtures/03_sucursales.json',
        'fixtures/04_usuarios.json'
    ]
    
    cargados = 0
    total = len(archivos)
    
    for archivo in archivos:
        print(f"📊 Cargando {archivo}...")
        try:
            # Usar execute_from_command_line para ejecutar loaddata
            execute_from_command_line(['manage.py', 'loaddata', archivo])
            print(f"✅ {archivo} cargado exitosamente")
            cargados += 1
        except Exception as e:
            print(f"❌ Error cargando {archivo}: {e}")
    
    print("=" * 50)
    print(f"🎉 Proceso completado: {cargados}/{total} archivos cargados")
    
    if cargados == total:
        print("✅ Todos los archivos se cargaron correctamente")
    else:
        print(f"⚠️  {total - cargados} archivos fallaron")

if __name__ == '__main__':
    cargar_datos_loaddata_simple() 