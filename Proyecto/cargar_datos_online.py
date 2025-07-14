#!/usr/bin/env python
"""
Script para cargar datos desde archivos de backup a la base de datos online
"""

import os
import sys
import django
import json
from datetime import datetime

# Configurar Django para producción (base de datos online)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings_render')
django.setup()

from django.core import serializers
from django.db import transaction
from recursosHumanos.models import Provincia, Ciudad, Sucursal, Usuario

def load_backup_data(backup_dir):
    """Cargar datos desde archivos de backup"""
    print("📂 Cargando datos desde:", backup_dir)
    
    # Verificar que el directorio existe
    if not os.path.exists(backup_dir):
        print(f"❌ Error: El directorio {backup_dir} no existe")
        return False
    
    try:
        with transaction.atomic():
            # 1. Cargar provincias
            print("\n🌍 Cargando PROVINCIAS...")
            with open(os.path.join(backup_dir, '01_provincias.json'), 'r', encoding='utf-8') as f:
                provincias_data = f.read()
            
            # Limpiar tabla de provincias
            Provincia.objects.all().delete()
            print("   - Tabla de provincias limpiada")
            
            # Cargar provincias
            provincias = serializers.deserialize('json', provincias_data)
            for provincia in provincias:
                provincia.save()
            print(f"   ✅ {Provincia.objects.count()} provincias cargadas")
            
            # 2. Cargar ciudades
            print("\n🏙️ Cargando CIUDADES...")
            with open(os.path.join(backup_dir, '02_ciudades.json'), 'r', encoding='utf-8') as f:
                ciudades_data = f.read()
            
            # Limpiar tabla de ciudades
            Ciudad.objects.all().delete()
            print("   - Tabla de ciudades limpiada")
            
            # Cargar ciudades
            ciudades = serializers.deserialize('json', ciudades_data)
            for ciudad in ciudades:
                ciudad.save()
            print(f"   ✅ {Ciudad.objects.count()} ciudades cargadas")
            
            # 3. Cargar sucursales
            print("\n🏢 Cargando SUCURSALES...")
            with open(os.path.join(backup_dir, '03_sucursales.json'), 'r', encoding='utf-8') as f:
                sucursales_data = f.read()
            
            # Limpiar tabla de sucursales
            Sucursal.objects.all().delete()
            print("   - Tabla de sucursales limpiada")
            
            # Cargar sucursales
            sucursales = serializers.deserialize('json', sucursales_data)
            for sucursal in sucursales:
                sucursal.save()
            print(f"   ✅ {Sucursal.objects.count()} sucursales cargadas")
            
            # 4. Cargar usuarios
            print("\n👥 Cargando USUARIOS...")
            with open(os.path.join(backup_dir, '04_usuarios.json'), 'r', encoding='utf-8') as f:
                usuarios_data = f.read()
            
            # Limpiar tabla de usuarios
            Usuario.objects.all().delete()
            print("   - Tabla de usuarios limpiada")
            
            # Cargar usuarios
            usuarios = serializers.deserialize('json', usuarios_data)
            for usuario in usuarios:
                usuario.save()
            print(f"   ✅ {Usuario.objects.count()} usuarios cargados")
            
            return True
            
    except Exception as e:
        print(f"❌ Error durante la migración: {str(e)}")
        return False

def verify_migration():
    """Verificar que la migración fue exitosa"""
    print("\n🔍 Verificando migración...")
    
    print(f"   - Provincias: {Provincia.objects.count()}")
    print(f"   - Ciudades: {Ciudad.objects.count()}")
    print(f"   - Sucursales: {Sucursal.objects.count()}")
    print(f"   - Usuarios: {Usuario.objects.count()}")
    
    # Mostrar algunos ejemplos
    print("\n📋 Ejemplos de datos migrados:")
    print("   Provincias:", [p.nombre for p in Provincia.objects.all()[:3]])
    print("   Ciudades:", [c.nombre for c in Ciudad.objects.all()[:3]])
    print("   Sucursales:", [s.nombre for s in Sucursal.objects.all()[:3]])
    print("   Usuarios:", [u.username for u in Usuario.objects.all()[:3]])

def main():
    """Función principal"""
    print("🚀 Iniciando carga de datos a base de datos online")
    print("=" * 50)
    
    # Buscar el directorio de backup con datos
    backup_dirs = [d for d in os.listdir('.') if d.startswith('backups_')]
    if not backup_dirs:
        print("❌ No se encontraron directorios de backup")
        return
    
    # Ordenar por fecha (más reciente primero)
    backup_dirs.sort(reverse=True)
    
    # Buscar el primer directorio que tenga datos
    backup_dir = None
    for dir_name in backup_dirs:
        provincias_file = os.path.join(dir_name, '01_provincias.json')
        if os.path.exists(provincias_file):
            with open(provincias_file, 'r') as f:
                content = f.read().strip()
                if content and content != '[]':
                    backup_dir = dir_name
                    break
    
    if not backup_dir:
        print("❌ No se encontraron directorios de backup con datos")
        return
    
    print(f"📁 Usando backup con datos: {backup_dir}")
    
    # Confirmar migración
    print("\n⚠️  ADVERTENCIA: Esta operación sobrescribirá los datos en la base de datos online")
    print("   Asegúrate de que la base de datos online esté vacía o que tengas un backup")
    
    # Ejecutar migración
    success = load_backup_data(backup_dir)
    
    if success:
        verify_migration()
        print("\n" + "=" * 50)
        print("🎉 Carga de datos completada exitosamente!")
        print("📋 Próximos pasos:")
        print("1. Verificar que los datos estén correctos en la web online")
        print("2. Probar el login con los usuarios cargados")
        print("3. Continuar con la carga del resto de datos")
    else:
        print("\n❌ La carga de datos falló. Revisa los errores arriba.")

if __name__ == '__main__':
    main() 