#!/usr/bin/env python3
"""
Script para hacer backup de todas las apps usando Django dumpdata
Este script exporta cada app completa con todos sus modelos
"""

import os
import sys
import django
import json
import subprocess
from datetime import datetime

# Configurar Django para usar settings locales (MySQL)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings')
django.setup()

def backup_por_apps():
    """Backup de todas las apps usando dumpdata"""
    
    # Crear directorio de backup con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backups_apps_{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)
    
    print("🚀 Iniciando backup por apps de toda la base de datos")
    print("=" * 60)
    print("📊 Usando Django dumpdata por app")
    print("=" * 60)
    
    # Lista de apps a respaldar
    apps = [
        'recursosHumanos',
        'clientes', 
        'operationsCenter',
        'centroSoluciones',
        'crm',
        'ventaMaquinarias',
        'gestionDeTaller'
    ]
    
    total_apps = len(apps)
    exitosos = 0
    fallidos = 0
    resumen = []
    
    print(f"📊 Total de apps a respaldar: {total_apps}")
    print()
    
    for i, app_name in enumerate(apps, 1):
        print(f"📊 Respaldando {i:2d}/{total_apps} - {app_name}...")
        
        try:
            # Crear nombre de archivo
            filename = f"{i:02d}_{app_name}_completo.json"
            filepath = os.path.join(backup_dir, filename)
            
            # Ejecutar dumpdata
            result = subprocess.run([
                'python', 'manage.py', 'dumpdata', app_name,
                '--output', filepath,
                '--indent', '2'
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode == 0:
                # Verificar que se guardó correctamente
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    
                    # Contar registros en el archivo JSON
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        registros = len(data)
                    except:
                        registros = 0
                    
                    print(f"✅ {app_name}: {registros:,} registros ({file_size:,} bytes)")
                    
                    resumen.append({
                        'app': app_name,
                        'registros': registros,
                        'archivo': filename,
                        'estado': 'exitoso',
                        'tamaño': file_size
                    })
                    
                    exitosos += 1
                else:
                    print(f"❌ {app_name}: Archivo no se creó")
                    fallidos += 1
            else:
                print(f"❌ {app_name}: Error - {result.stderr}")
                fallidos += 1
                
        except Exception as e:
            print(f"❌ {app_name}: Error - {str(e)}")
            resumen.append({
                'app': app_name,
                'registros': 0,
                'archivo': None,
                'estado': 'error',
                'error': str(e)
            })
            fallidos += 1
    
    # Crear archivo de resumen
    resumen_data = {
        'fecha_backup': timestamp,
        'total_apps': total_apps,
        'exitosos': exitosos,
        'fallidos': fallidos,
        'detalles': resumen
    }
    
    resumen_file = os.path.join(backup_dir, 'RESUMEN_BACKUP_APPS.json')
    with open(resumen_file, 'w', encoding='utf-8') as f:
        json.dump(resumen_data, f, indent=2, ensure_ascii=False)
    
    # Mostrar resumen final
    print()
    print("=" * 60)
    print("📋 RESUMEN DEL BACKUP POR APPS")
    print("=" * 60)
    print(f"📁 Directorio: {backup_dir}/")
    print(f"📊 Total de apps: {total_apps}")
    print(f"✅ Exitosos: {exitosos}")
    print(f"❌ Fallidos: {fallidos}")
    print()
    
    # Mostrar apps con más datos
    apps_con_datos = [r for r in resumen if r['estado'] == 'exitoso' and r['registros'] > 0]
    if apps_con_datos:
        print("🏆 Apps con más registros:")
        apps_con_datos.sort(key=lambda x: x['registros'], reverse=True)
        for i, app in enumerate(apps_con_datos, 1):
            print(f"   {i:2d}. {app['app']}: {app['registros']:,} registros")
    
    print()
    print("🎉 Backup por apps finalizado!")
    print(f"📁 Archivos guardados en: {backup_dir}/")
    print(f"📋 Resumen detallado: {resumen_file}")
    
    return backup_dir, resumen_data

if __name__ == '__main__':
    backup_por_apps() 