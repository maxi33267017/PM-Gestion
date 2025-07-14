#!/usr/bin/env python3
"""
Script para hacer backup de todos los archivos media
Crea un archivo comprimido con todos los archivos
"""

import os
import sys
import tarfile
from datetime import datetime

def backup_media_files():
    """Crear backup comprimido de todos los archivos media"""
    
    # Crear nombre del archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"media_backup_{timestamp}.tar.gz"
    
    print("🚀 Iniciando backup de archivos media")
    print("=" * 50)
    
    # Verificar que el directorio media existe
    media_dir = "media"
    if not os.path.exists(media_dir):
        print(f"❌ El directorio {media_dir} no existe")
        return False
    
    # Contar archivos
    total_files = 0
    total_size = 0
    
    for root, dirs, files in os.walk(media_dir):
        total_files += len(files)
        for file in files:
            filepath = os.path.join(root, file)
            total_size += os.path.getsize(filepath)
    
    print(f"📊 Archivos encontrados: {total_files:,}")
    print(f"📊 Tamaño total: {total_size / (1024*1024):.2f} MB")
    print()
    
    # Crear archivo comprimido
    print(f"📦 Creando archivo: {backup_file}")
    
    try:
        with tarfile.open(backup_file, "w:gz") as tar:
            tar.add(media_dir, arcname="media")
        
        # Verificar que se creó correctamente
        if os.path.exists(backup_file):
            file_size = os.path.getsize(backup_file)
            print(f"✅ Backup creado exitosamente: {file_size / (1024*1024):.2f} MB")
            
            # Mostrar contenido del archivo
            print("\n📋 Contenido del backup:")
            with tarfile.open(backup_file, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.isfile():
                        print(f"   📄 {member.name}")
            
            print(f"\n🎉 Backup de media completado!")
            print(f"📁 Archivo: {backup_file}")
            print(f"📊 Tamaño: {file_size / (1024*1024):.2f} MB")
            
            return backup_file
            
    except Exception as e:
        print(f"❌ Error creando backup: {str(e)}")
        return False

def list_media_files():
    """Listar todos los archivos media por categoría"""
    
    print("📋 Listado de archivos media por categoría:")
    print("=" * 50)
    
    media_dir = "media"
    if not os.path.exists(media_dir):
        print(f"❌ El directorio {media_dir} no existe")
        return
    
    categories = {}
    
    for root, dirs, files in os.walk(media_dir):
        category = root.replace(media_dir, "").strip("/")
        if not category:
            category = "root"
        
        if category not in categories:
            categories[category] = []
        
        for file in files:
            filepath = os.path.join(root, file)
            file_size = os.path.getsize(filepath)
            categories[category].append({
                'name': file,
                'path': filepath,
                'size': file_size
            })
    
    total_files = 0
    total_size = 0
    
    for category, files in categories.items():
        if files:
            print(f"\n📁 {category}/")
            category_size = sum(f['size'] for f in files)
            print(f"   📊 {len(files)} archivos - {category_size / 1024:.1f} KB")
            
            for file_info in files[:5]:  # Mostrar solo los primeros 5
                print(f"      📄 {file_info['name']} ({file_info['size']} bytes)")
            
            if len(files) > 5:
                print(f"      ... y {len(files) - 5} archivos más")
            
            total_files += len(files)
            total_size += category_size
    
    print(f"\n📊 RESUMEN:")
    print(f"   Total archivos: {total_files:,}")
    print(f"   Tamaño total: {total_size / (1024*1024):.2f} MB")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Backup de archivos media')
    parser.add_argument('--list', action='store_true', help='Solo listar archivos')
    
    args = parser.parse_args()
    
    if args.list:
        list_media_files()
    else:
        backup_media_files() 