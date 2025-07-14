#!/usr/bin/env python3
"""
Script para verificar que los archivos media estén correctamente configurados
"""

import os
import django
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings_render')
django.setup()

def verificar_media():
    """Verificar configuración de archivos media"""
    
    print("🔍 Verificando configuración de archivos media")
    print("=" * 50)
    
    # Verificar configuración
    print(f"📁 MEDIA_ROOT: {settings.MEDIA_ROOT}")
    print(f"🌐 MEDIA_URL: {settings.MEDIA_URL}")
    print(f"📁 BASE_DIR: {settings.BASE_DIR}")
    
    # Verificar que el directorio existe
    if os.path.exists(settings.MEDIA_ROOT):
        print(f"✅ MEDIA_ROOT existe: {settings.MEDIA_ROOT}")
    else:
        print(f"❌ MEDIA_ROOT no existe: {settings.MEDIA_ROOT}")
        return False
    
    # Verificar archivos específicos
    archivos_test = [
        'herramientas_especiales/66099052.webp',
        '5s/revision/evidencias/IMG_0673.jpeg',
        'herramientas_especiales/1744.PNG'
    ]
    
    print("\n📋 Verificando archivos específicos:")
    for archivo in archivos_test:
        ruta_completa = os.path.join(settings.MEDIA_ROOT, archivo)
        if os.path.exists(ruta_completa):
            tamaño = os.path.getsize(ruta_completa)
            print(f"✅ {archivo}: {tamaño:,} bytes")
        else:
            print(f"❌ {archivo}: NO ENCONTRADO")
    
    # Contar archivos por categoría
    print("\n📊 Estadísticas de archivos:")
    categorias = {}
    
    for root, dirs, files in os.walk(settings.MEDIA_ROOT):
        categoria = root.replace(settings.MEDIA_ROOT, "").strip("/")
        if not categoria:
            categoria = "root"
        
        if categoria not in categorias:
            categorias[categoria] = 0
        
        categorias[categoria] += len(files)
    
    total_archivos = 0
    for categoria, count in categorias.items():
        if count > 0:
            print(f"   📁 {categoria}: {count} archivos")
            total_archivos += count
    
    print(f"   📊 Total: {total_archivos} archivos")
    
    # Verificar configuración de WhiteNoise
    print(f"\n⚙️  Configuración de WhiteNoise:")
    print(f"   WHITENOISE_ROOT: {getattr(settings, 'WHITENOISE_ROOT', 'No configurado')}")
    print(f"   WHITENOISE_USE_FINDERS: {getattr(settings, 'WHITENOISE_USE_FINDERS', 'No configurado')}")
    
    return True

def generar_urls_test():
    """Generar URLs de prueba para archivos media"""
    
    print("\n🌐 URLs de prueba para archivos media:")
    print("=" * 50)
    
    base_url = "https://pm-gestion.onrender.com"
    
    archivos_test = [
        'herramientas_especiales/66099052.webp',
        '5s/revision/evidencias/IMG_0673.jpeg',
        'herramientas_especiales/1744.PNG',
        'facturas/SKY_TOP_SRL_11138.pdf'
    ]
    
    for archivo in archivos_test:
        url = f"{base_url}{settings.MEDIA_URL}{archivo}"
        print(f"   🔗 {url}")
    
    print(f"\n💡 Para probar localmente, usa:")
    print(f"   http://localhost:8000{settings.MEDIA_URL}herramientas_especiales/66099052.webp")

if __name__ == '__main__':
    verificar_media()
    generar_urls_test() 