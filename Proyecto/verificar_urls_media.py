#!/usr/bin/env python3
"""
Script para verificar URLs de archivos media en la base de datos
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings_render')
django.setup()

def verificar_urls_media():
    """Verificar URLs de archivos media en la base de datos"""
    
    print("🔍 Verificando URLs de archivos media en la base de datos")
    print("=" * 60)
    
    try:
        # Importar modelos que tienen archivos media
        from gestionDeTaller.models import Evidencia, HerramientaEspecial
        from recursosHumanos.models import HerramientaEspecial as HerramientaEspecialRH
        
        total_archivos = 0
        archivos_s3 = 0
        archivos_local = 0
        
        # 1. Evidencias de preórdenes
        print("\n📋 Evidencias de preórdenes:")
        evidencias = Evidencia.objects.all()
        for evidencia in evidencias:
            if evidencia.imagen:
                total_archivos += 1
                if 's3.amazonaws.com' in str(evidencia.imagen):
                    print(f"   ❌ S3: {evidencia.imagen}")
                    archivos_s3 += 1
                elif '/media/' in str(evidencia.imagen):
                    print(f"   ✅ Local: {evidencia.imagen}")
                    archivos_local += 1
                else:
                    print(f"   ⚠️  Otro: {evidencia.imagen}")
        
        # 2. Herramientas especiales (Gestión de Taller)
        print("\n📋 Herramientas especiales (Gestión de Taller):")
        herramientas = HerramientaEspecial.objects.all()
        for herramienta in herramientas:
            if herramienta.foto:
                total_archivos += 1
                if 's3.amazonaws.com' in str(herramienta.foto):
                    print(f"   ❌ S3: {herramienta.foto}")
                    archivos_s3 += 1
                elif '/media/' in str(herramienta.foto):
                    print(f"   ✅ Local: {herramienta.foto}")
                    archivos_local += 1
                else:
                    print(f"   ⚠️  Otro: {herramienta.foto}")
        
        # 3. Herramientas especiales (Recursos Humanos)
        print("\n📋 Herramientas especiales (Recursos Humanos):")
        herramientas_rh = HerramientaEspecialRH.objects.all()
        for herramienta in herramientas_rh:
            if herramienta.foto:
                total_archivos += 1
                if 's3.amazonaws.com' in str(herramienta.foto):
                    print(f"   ❌ S3: {herramienta.foto}")
                    archivos_s3 += 1
                elif '/media/' in str(herramienta.foto):
                    print(f"   ✅ Local: {herramienta.foto}")
                    archivos_local += 1
                else:
                    print(f"   ⚠️  Otro: {herramienta.foto}")
        

        
        # Resumen
        print("\n📊 RESUMEN:")
        print("=" * 30)
        print(f"   Total de archivos: {total_archivos}")
        print(f"   Archivos S3: {archivos_s3}")
        print(f"   Archivos locales: {archivos_local}")
        print(f"   Otros: {total_archivos - archivos_s3 - archivos_local}")
        
        if archivos_s3 > 0:
            print(f"\n⚠️  PROBLEMA DETECTADO:")
            print(f"   Hay {archivos_s3} archivos con URLs de S3")
            print(f"   Esto causará errores 'Access Denied' en producción")
            print(f"   ")
            print(f"💡 SOLUCIÓN:")
            print(f"   1. Configurar AWS S3 correctamente en Render.com")
            print(f"   2. O migrar los archivos a URLs locales")
        
        return archivos_s3 > 0
        
    except Exception as e:
        print(f"❌ Error verificando URLs: {e}")
        return False

if __name__ == "__main__":
    verificar_urls_media() 