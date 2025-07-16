#!/usr/bin/env python3
"""
Script para verificar y configurar AWS S3
"""

import os
import django
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings_render')
django.setup()

def verificar_configuracion_s3():
    """Verificar la configuración de AWS S3"""
    
    print("🔍 Verificando configuración de AWS S3")
    print("=" * 50)
    
    # Verificar variables de entorno
    variables_requeridas = [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY', 
        'AWS_STORAGE_BUCKET_NAME'
    ]
    
    print("📋 Variables de entorno:")
    for variable in variables_requeridas:
        valor = os.environ.get(variable)
        if valor:
            print(f"   ✅ {variable}: {'*' * len(valor)}")
        else:
            print(f"   ❌ {variable}: NO DEFINIDA")
    
    # Verificar configuración de Django
    print(f"\n⚙️  Configuración de Django:")
    print(f"   USE_S3: {getattr(settings, 'USE_S3', False)}")
    print(f"   AWS_STORAGE_BUCKET_NAME: {getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'No configurado')}")
    print(f"   AWS_S3_REGION_NAME: {getattr(settings, 'AWS_S3_REGION_NAME', 'No configurado')}")
    print(f"   DEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', 'No configurado')}")
    
    # Verificar conexión a S3
    print(f"\n🌐 Verificando conexión a AWS S3...")
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
        )
        
        # Verificar que el bucket existe
        bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME')
        if bucket_name:
            try:
                s3_client.head_bucket(Bucket=bucket_name)
                print(f"   ✅ Bucket '{bucket_name}' existe y es accesible")
                
                # Listar algunos objetos para verificar permisos
                response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
                if 'Contents' in response:
                    print(f"   ✅ Bucket contiene {len(response['Contents'])} objetos")
                else:
                    print(f"   ℹ️  Bucket está vacío")
                    
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    print(f"   ❌ Bucket '{bucket_name}' no existe")
                elif error_code == '403':
                    print(f"   ❌ Sin permisos para acceder al bucket '{bucket_name}'")
                else:
                    print(f"   ❌ Error accediendo al bucket: {error_code}")
                    
        else:
            print(f"   ❌ AWS_STORAGE_BUCKET_NAME no está definido")
            
    except NoCredentialsError:
        print(f"   ❌ Credenciales de AWS no encontradas")
    except Exception as e:
        print(f"   ❌ Error de conexión: {str(e)}")
    
    return True

def crear_bucket_s3():
    """Crear bucket S3 si no existe"""
    
    print(f"\n🪣 Creando bucket S3...")
    
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
        )
        
        bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME')
        region = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
        
        if not bucket_name:
            print(f"   ❌ AWS_STORAGE_BUCKET_NAME no está definido")
            return False
        
        # Verificar si el bucket ya existe
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"   ℹ️  Bucket '{bucket_name}' ya existe")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # Bucket no existe, crearlo
                try:
                    if region == 'us-east-1':
                        s3_client.create_bucket(Bucket=bucket_name)
                    else:
                        s3_client.create_bucket(
                            Bucket=bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': region}
                        )
                    
                    print(f"   ✅ Bucket '{bucket_name}' creado exitosamente")
                    
                    # Configurar bucket para acceso público (solo para archivos media)
                    bucket_policy = {
                        'Version': '2012-10-17',
                        'Statement': [
                            {
                                'Sid': 'PublicReadGetObject',
                                'Effect': 'Allow',
                                'Principal': '*',
                                'Action': 's3:GetObject',
                                'Resource': f'arn:aws:s3:::{bucket_name}/media/*'
                            }
                        ]
                    }
                    
                    s3_client.put_bucket_policy(
                        Bucket=bucket_name,
                        Policy=json.dumps(bucket_policy)
                    )
                    
                    print(f"   ✅ Política de bucket configurada para acceso público a archivos media")
                    return True
                    
                except Exception as e:
                    print(f"   ❌ Error creando bucket: {str(e)}")
                    return False
            else:
                print(f"   ❌ Error verificando bucket: {str(e)}")
                return False
                
    except Exception as e:
        print(f"   ❌ Error general: {str(e)}")
        return False

def subir_archivo_prueba():
    """Subir un archivo de prueba a S3"""
    
    print(f"\n🧪 Subiendo archivo de prueba...")
    
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
        )
        
        bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME')
        
        # Crear archivo de prueba
        contenido_prueba = b"Este es un archivo de prueba para verificar la configuración de S3"
        
        # Subir archivo
        s3_client.put_object(
            Bucket=bucket_name,
            Key='media/test.txt',
            Body=contenido_prueba,
            ContentType='text/plain'
        )
        
        print(f"   ✅ Archivo de prueba subido exitosamente")
        
        # Verificar que se puede descargar
        response = s3_client.get_object(Bucket=bucket_name, Key='media/test.txt')
        contenido_descargado = response['Body'].read()
        
        if contenido_descargado == contenido_prueba:
            print(f"   ✅ Archivo de prueba se puede descargar correctamente")
            
            # Limpiar archivo de prueba
            s3_client.delete_object(Bucket=bucket_name, Key='media/test.txt')
            print(f"   ✅ Archivo de prueba eliminado")
            return True
        else:
            print(f"   ❌ Error: el contenido descargado no coincide")
            return False
            
    except Exception as e:
        print(f"   ❌ Error en prueba: {str(e)}")
        return False

if __name__ == "__main__":
    import json
    
    print("🚀 Configuración de AWS S3")
    print("=" * 50)
    
    # Verificar configuración
    verificar_configuracion_s3()
    
    # Crear bucket si es necesario
    crear_bucket_s3()
    
    # Probar subida de archivo
    subir_archivo_prueba()
    
    print(f"\n📋 Próximos pasos:")
    print(f"   1. Configurar variables de entorno en Render.com")
    print(f"   2. Ejecutar: python migrar_a_s3.py")
    print(f"   3. Probar subida de archivos desde la aplicación") 