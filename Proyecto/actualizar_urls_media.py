#!/usr/bin/env python3
"""
Script para actualizar URLs de archivos media en la base de datos
Cambia las URLs de /media/ a /static/ para que funcionen con WhiteNoise
"""

import os
import django
import re

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings_render')
django.setup()

from django.db import connection

def actualizar_urls_media():
    """Actualizar URLs de archivos media en la base de datos"""
    
    print("🔄 Actualizando URLs de archivos media en la base de datos")
    print("=" * 60)
    
    # Lista de tablas que pueden contener URLs de archivos media
    tablas_con_media = [
        'gestionDeTaller_herramientaespecial',
        'gestionDeTaller_evidenciarevision5s',
        'gestionDeTaller_evidenciaplanaccion5s',
        'gestionDeTaller_evidencia',
        'recursosHumanos_herramientaespecial',
        'recursosHumanos_prestamoherramienta'
    ]
    
    total_actualizados = 0
    
    with connection.cursor() as cursor:
        for tabla in tablas_con_media:
            print(f"\n📋 Verificando tabla: {tabla}")
            
            # Obtener columnas de la tabla
            cursor.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{tabla}'
                AND data_type IN ('character varying', 'text')
            """)
            
            columnas = cursor.fetchall()
            
            for columna, tipo in columnas:
                # Buscar registros que contengan URLs de media
                cursor.execute(f"""
                    SELECT id, {columna}
                    FROM {tabla}
                    WHERE {columna} LIKE '%/media/%'
                """)
                
                registros = cursor.fetchall()
                
                if registros:
                    print(f"   📄 Columna {columna}: {len(registros)} registros con URLs de media")
                    
                    for registro_id, valor in registros:
                        if valor and '/media/' in str(valor):
                            # Reemplazar /media/ por /static/
                            nuevo_valor = str(valor).replace('/media/', '/static/')
                            
                            # Actualizar el registro
                            cursor.execute(f"""
                                UPDATE {tabla}
                                SET {columna} = %s
                                WHERE id = %s
                            """, [nuevo_valor, registro_id])
                            
                            total_actualizados += 1
                            print(f"      ✅ ID {registro_id}: {valor} → {nuevo_valor}")
    
    # Hacer commit de los cambios
    connection.commit()
    
    print(f"\n🎉 Actualización completada!")
    print(f"📊 Total de registros actualizados: {total_actualizados}")
    
    return total_actualizados

def verificar_urls_actualizadas():
    """Verificar que las URLs se actualizaron correctamente"""
    
    print("\n🔍 Verificando URLs actualizadas:")
    print("=" * 40)
    
    with connection.cursor() as cursor:
        # Verificar herramientas especiales
        cursor.execute("""
            SELECT id, imagen, nombre
            FROM gestionDeTaller_herramientaespecial
            WHERE imagen LIKE '%/static/%'
            LIMIT 5
        """)
        
        herramientas = cursor.fetchall()
        print(f"📋 Herramientas especiales con URLs /static/: {len(herramientas)}")
        
        for herramienta_id, imagen, nombre in herramientas:
            print(f"   🔧 {nombre}: {imagen}")
        
        # Verificar evidencias 5S
        cursor.execute("""
            SELECT id, imagen
            FROM gestionDeTaller_evidenciarevision5s
            WHERE imagen LIKE '%/static/%'
            LIMIT 3
        """)
        
        evidencias = cursor.fetchall()
        print(f"\n📋 Evidencias 5S con URLs /static/: {len(evidencias)}")
        
        for evidencia_id, imagen in evidencias:
            print(f"   📸 ID {evidencia_id}: {imagen}")

if __name__ == '__main__':
    actualizar_urls_media()
    verificar_urls_actualizadas() 