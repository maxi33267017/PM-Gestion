#!/usr/bin/env python3
"""
Script para migrar archivos existentes a AWS S3
"""

import os
import django
import boto3
from django.core.files.base import ContentFile
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings_render')
django.setup()

def migrar_archivos_a_s3():
    """Migrar archivos existentes a AWS S3"""
    
    print("🚀 Migrando archivos a AWS S3")
    print("=" * 50)
    
    # Verificar configuración de S3
    if not getattr(settings, 'USE_S3', False):
        print("❌ AWS S3 no está configurado")
        print("   Configura las variables de entorno:")
        print("   - USE_S3=True")
        print("   - AWS_ACCESS_KEY_ID")
        print("   - AWS_SECRET_ACCESS_KEY")
        print("   - AWS_STORAGE_BUCKET_NAME")
        return False
    
    try:
        # Importar modelos
        from gestionDeTaller.models import (
            HerramientaEspecial, EvidenciaRevision5S, 
            EvidenciaPlanAccion5S, Evidencia, PreOrden
        )
        
        # Inicializar cliente S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        total_migrados = 0
        total_errores = 0
        
        # 1. Migrar herramientas especiales
        print("\n📋 Migrando herramientas especiales...")
        herramientas = HerramientaEspecial.objects.filter(foto__isnull=False).exclude(foto='')
        
        for herramienta in herramientas:
            try:
                if herramienta.foto and hasattr(herramienta.foto, 'read'):
                    # Leer el archivo
                    herramienta.foto.seek(0)
                    contenido = herramienta.foto.read()
                    
                    # Subir a S3
                    nombre_archivo = f"herramientas_especiales/{os.path.basename(herramienta.foto.name)}"
                    s3_client.put_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=nombre_archivo,
                        Body=contenido,
                        ContentType='image/jpeg'
                    )
                    
                    # Actualizar el campo en la base de datos
                    herramienta.foto = nombre_archivo
                    herramienta.save()
                    
                    total_migrados += 1
                    print(f"   ✅ {herramienta.nombre}: {nombre_archivo}")
                    
            except Exception as e:
                total_errores += 1
                print(f"   ❌ Error con {herramienta.nombre}: {str(e)}")
        
        # 2. Migrar evidencias de preórdenes
        print("\n📋 Migrando evidencias de preórdenes...")
        evidencias = Evidencia.objects.filter(imagen__isnull=False).exclude(imagen='')
        
        for evidencia in evidencias:
            try:
                if evidencia.imagen and hasattr(evidencia.imagen, 'read'):
                    # Leer el archivo
                    evidencia.imagen.seek(0)
                    contenido = evidencia.imagen.read()
                    
                    # Subir a S3
                    nombre_archivo = f"evidencias/{os.path.basename(evidencia.imagen.name)}"
                    s3_client.put_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=nombre_archivo,
                        Body=contenido,
                        ContentType='image/jpeg'
                    )
                    
                    # Actualizar el campo en la base de datos
                    evidencia.imagen = nombre_archivo
                    evidencia.save()
                    
                    total_migrados += 1
                    print(f"   ✅ Evidencia {evidencia.id}: {nombre_archivo}")
                    
            except Exception as e:
                total_errores += 1
                print(f"   ❌ Error con evidencia {evidencia.id}: {str(e)}")
        
        # 3. Migrar firmas de preórdenes
        print("\n📋 Migrando firmas de preórdenes...")
        preordenes = PreOrden.objects.filter(firma_cliente__isnull=False).exclude(firma_cliente='')
        
        for preorden in preordenes:
            try:
                if preorden.firma_cliente and hasattr(preorden.firma_cliente, 'read'):
                    # Leer el archivo
                    preorden.firma_cliente.seek(0)
                    contenido = preorden.firma_cliente.read()
                    
                    # Subir a S3
                    nombre_archivo = f"firmas_clientes/{os.path.basename(preorden.firma_cliente.name)}"
                    s3_client.put_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=nombre_archivo,
                        Body=contenido,
                        ContentType='image/png'
                    )
                    
                    # Actualizar el campo en la base de datos
                    preorden.firma_cliente = nombre_archivo
                    preorden.save()
                    
                    total_migrados += 1
                    print(f"   ✅ Preorden {preorden.numero}: {nombre_archivo}")
                    
            except Exception as e:
                total_errores += 1
                print(f"   ❌ Error con preorden {preorden.numero}: {str(e)}")
        
        # 4. Migrar evidencias de revisión 5S
        print("\n📋 Migrando evidencias de revisión 5S...")
        evidencias_5s = EvidenciaRevision5S.objects.filter(imagen__isnull=False).exclude(imagen='')
        
        for evidencia in evidencias_5s:
            try:
                if evidencia.imagen and hasattr(evidencia.imagen, 'read'):
                    # Leer el archivo
                    evidencia.imagen.seek(0)
                    contenido = evidencia.imagen.read()
                    
                    # Subir a S3
                    nombre_archivo = f"5s/revision/evidencias/{os.path.basename(evidencia.imagen.name)}"
                    s3_client.put_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=nombre_archivo,
                        Body=contenido,
                        ContentType='image/jpeg'
                    )
                    
                    # Actualizar el campo en la base de datos
                    evidencia.imagen = nombre_archivo
                    evidencia.save()
                    
                    total_migrados += 1
                    print(f"   ✅ Evidencia 5S {evidencia.id}: {nombre_archivo}")
                    
            except Exception as e:
                total_errores += 1
                print(f"   ❌ Error con evidencia 5S {evidencia.id}: {str(e)}")
        
        print(f"\n📊 Resumen de migración:")
        print(f"   ✅ Archivos migrados: {total_migrados}")
        print(f"   ❌ Errores: {total_errores}")
        
        if total_errores == 0:
            print(f"\n🎉 ¡Migración completada exitosamente!")
            return True
        else:
            print(f"\n⚠️  Migración completada con {total_errores} errores")
            return False
            
    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        return False

if __name__ == "__main__":
    migrar_archivos_a_s3() 