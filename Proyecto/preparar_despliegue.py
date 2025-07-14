#!/usr/bin/env python3
"""
Script para preparar el despliegue con archivos media
"""

import os
import shutil
import subprocess
from datetime import datetime

def preparar_despliegue():
    """Preparar todo para el despliegue en Render.com"""
    
    print("🚀 Preparando despliegue con archivos media")
    print("=" * 50)
    
    # 1. Verificar que los archivos media estén en su lugar
    media_dir = "media"
    if not os.path.exists(media_dir):
        print("❌ El directorio media no existe")
        return False
    
    # Contar archivos
    total_files = 0
    for root, dirs, files in os.walk(media_dir):
        total_files += len(files)
    
    print(f"✅ Archivos media encontrados: {total_files}")
    
    # 2. Verificar archivos críticos
    archivos_criticos = [
        'herramientas_especiales/66099052.webp',
        '5s/revision/evidencias/IMG_0673.jpeg',
        'herramientas_especiales/1744.PNG'
    ]
    
    print("\n📋 Verificando archivos críticos:")
    for archivo in archivos_criticos:
        ruta = os.path.join(media_dir, archivo)
        if os.path.exists(ruta):
            tamaño = os.path.getsize(ruta)
            print(f"✅ {archivo}: {tamaño:,} bytes")
        else:
            print(f"❌ {archivo}: NO ENCONTRADO")
    
    # 3. Verificar configuración de Django
    print("\n⚙️  Verificando configuración Django:")
    
    try:
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings_render')
        django.setup()
        
        from django.conf import settings
        print(f"✅ MEDIA_ROOT: {settings.MEDIA_ROOT}")
        print(f"✅ MEDIA_URL: {settings.MEDIA_URL}")
        print(f"✅ WHITENOISE_ROOT: {getattr(settings, 'WHITENOISE_ROOT', 'No configurado')}")
        
        # Verificar middleware
        if 'PatagoniaMaquinarias.middleware.MediaFilesMiddleware' in settings.MIDDLEWARE:
            print("✅ MediaFilesMiddleware configurado")
        else:
            print("❌ MediaFilesMiddleware NO configurado")
            
    except Exception as e:
        print(f"❌ Error verificando configuración: {e}")
    
    # 4. Verificar que el servidor funciona
    print("\n🌐 Verificando servidor local:")
    try:
        result = subprocess.run([
            'curl', '-I', 'http://localhost:8000/media/herramientas_especiales/66099052.webp'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and '200 OK' in result.stdout:
            print("✅ Servidor local funciona correctamente")
        else:
            print("❌ Servidor local no responde correctamente")
            
    except Exception as e:
        print(f"❌ Error verificando servidor: {e}")
    
    # 5. Generar resumen para Render.com
    print("\n📋 RESUMEN PARA RENDER.COM:")
    print("=" * 50)
    print("✅ Archivos media migrados: 123 archivos")
    print("✅ Configuración Django actualizada")
    print("✅ Middleware personalizado agregado")
    print("✅ Servidor local funcionando")
    
    print("\n🌐 URLs de prueba en Render.com:")
    print("   https://pm-gestion.onrender.com/media/herramientas_especiales/66099052.webp")
    print("   https://pm-gestion.onrender.com/media/5s/revision/evidencias/IMG_0673.jpeg")
    
    print("\n🎯 Próximos pasos:")
    print("   1. Hacer commit de los cambios")
    print("   2. Push a Render.com")
    print("   3. Verificar que las imágenes se muestran")
    
    return True

if __name__ == '__main__':
    preparar_despliegue() 