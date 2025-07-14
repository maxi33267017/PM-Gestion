#!/usr/bin/env python
"""
Script para cargar datos esenciales desde archivos de backup a la base de datos online
Ejecutar en el servidor de Render.com
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

# Importar modelos
from recursosHumanos.models import Provincia, Ciudad, Sucursal, Usuario
from clientes.models import Cliente, ContactoCliente, Equipo, ModeloEquipo, ModeloMotor, TipoEquipo
from gestionDeTaller.models import Servicio, PreOrden, Repuesto

def load_essential_data(backup_dir):
    """Cargar datos esenciales desde archivos de backup"""
    print("📂 Cargando datos desde:", backup_dir)
    
    # Verificar que el directorio existe
    if not os.path.exists(backup_dir):
        print(f"❌ Error: El directorio {backup_dir} no existe")
        return False
    
    # Lista de modelos a cargar
    models_to_load = [
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
    
    try:
        with transaction.atomic():
            for model_class, filename, description in models_to_load:
                filepath = os.path.join(backup_dir, filename)
                
                if not os.path.exists(filepath):
                    print(f"⚠️  Archivo no encontrado: {filename}")
                    continue
                
                print(f"\n📊 Cargando {description}...")
                
                # Verificar que el archivo no esté vacío
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content or content == '[]':
                        print(f"   ⚠️  Archivo vacío: {filename}")
                        continue
                
                # Limpiar tabla
                model_class.objects.all().delete()
                print(f"   - Tabla de {description.lower()} limpiada")
                
                # Cargar datos
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = f.read()
                
                objects = serializers.deserialize('json', data)
                for obj in objects:
                    obj.save()
                
                count = model_class.objects.count()
                print(f"   ✅ {count} {description.lower()} cargados")
            
            return True
            
    except Exception as e:
        print(f"❌ Error durante la carga: {str(e)}")
        return False

def verify_migration():
    """Verificar que la migración fue exitosa"""
    print("\n🔍 Verificando migración...")
    
    models_to_check = [
        (Provincia, 'Provincias'),
        (Ciudad, 'Ciudades'),
        (Sucursal, 'Sucursales'),
        (Usuario, 'Usuarios'),
        (Cliente, 'Clientes'),
        (ContactoCliente, 'Contactos Clientes'),
        (Equipo, 'Equipos'),
        (ModeloEquipo, 'Modelos Equipos'),
        (ModeloMotor, 'Modelos Motores'),
        (TipoEquipo, 'Tipos Equipos'),
        (Servicio, 'Servicios'),
        (PreOrden, 'Pre-órdenes'),
        (Repuesto, 'Repuestos'),
    ]
    
    for model_class, description in models_to_check:
        count = model_class.objects.count()
        print(f"   - {description}: {count}")

def main():
    """Función principal"""
    print("🚀 Iniciando carga de datos esenciales a base de datos online")
    print("=" * 60)
    
    # Buscar el directorio de backup más reciente
    backup_dirs = [d for d in os.listdir('.') if d.startswith('backup_esencial_')]
    if not backup_dirs:
        print("❌ No se encontraron directorios de backup esencial")
        print("💡 Asegúrate de haber subido los archivos de backup al servidor")
        return
    
    # Ordenar por fecha (más reciente primero)
    backup_dirs.sort(reverse=True)
    latest_backup = backup_dirs[0]
    
    print(f"📁 Usando backup: {latest_backup}")
    
    # Confirmar migración
    print("\n⚠️  ADVERTENCIA: Esta operación sobrescribirá los datos en la base de datos online")
    print("   Asegúrate de que la base de datos online esté vacía o que tengas un backup")
    
    # Ejecutar migración
    success = load_essential_data(latest_backup)
    
    if success:
        verify_migration()
        print("\n" + "=" * 60)
        print("🎉 Carga de datos esenciales completada exitosamente!")
        print("📋 Próximos pasos:")
        print("1. Verificar que los datos estén correctos en la web online")
        print("2. Probar el login con los usuarios cargados")
        print("3. Verificar que las funcionalidades principales funcionen")
    else:
        print("\n❌ La carga de datos falló. Revisa los errores arriba.")

if __name__ == '__main__':
    main() 