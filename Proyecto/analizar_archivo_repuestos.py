#!/usr/bin/env python
"""
Script para analizar la estructura del archivo AR.DMS.DWNLD.V2
y entender todos los campos disponibles
"""

import os
import sys
from datetime import datetime

def analizar_estructura_archivo(archivo_path, num_lineas=10):
    """Analiza la estructura del archivo de repuestos"""
    
    print(f"🔍 Analizando archivo: {archivo_path}")
    print(f"📊 Tamaño: {os.path.getsize(archivo_path) / (1024*1024):.1f} MB")
    
    with open(archivo_path, 'r', encoding='utf-8', errors='ignore') as f:
        # Contar líneas totales
        total_lineas = sum(1 for _ in f)
        print(f"📈 Total de líneas: {total_lineas:,}")
        
        # Volver al inicio
        f.seek(0)
        
        # Analizar las primeras líneas
        print(f"\n📋 Analizando las primeras {num_lineas} líneas:")
        print("=" * 80)
        
        for i, linea in enumerate(f, 1):
            if i > num_lineas:
                break
                
            print(f"\n--- Línea {i} ---")
            print(f"Longitud: {len(linea)} caracteres")
            print(f"Contenido: {repr(linea)}")
            
            # Intentar identificar campos por posición
            analizar_campos_linea(linea, i)
            
        # Analizar algunas líneas del medio
        print(f"\n📋 Analizando líneas del medio:")
        print("=" * 80)
        
        f.seek(0)
        linea_medio = total_lineas // 2
        
        for i, linea in enumerate(f, 1):
            if i >= linea_medio and i < linea_medio + 5:
                print(f"\n--- Línea {i} ---")
                analizar_campos_linea(linea, i)
            elif i > linea_medio + 5:
                break

def analizar_campos_linea(linea, numero_linea):
    """Analiza los campos de una línea específica"""
    
    # Limpiar la línea
    linea = linea.rstrip('\n\r')
    
    print(f"Línea completa: {linea}")
    
    # Intentar identificar campos por patrones
    campos = {}
    
    # Código del repuesto (primeros caracteres)
    if len(linea) >= 15:
        codigo = linea[:15].strip()
        campos['codigo'] = codigo
        print(f"  Código: '{codigo}'")
    
    # Buscar descripción (después del código)
    if len(linea) >= 50:
        # Buscar el final de la descripción (antes de los números)
        desc_start = 15
        desc_end = desc_start
        
        for i in range(desc_start, min(80, len(linea))):
            if linea[i].isdigit() and i > desc_start + 10:
                desc_end = i
                break
        else:
            desc_end = 80
        
        descripcion = linea[desc_start:desc_end].strip()
        campos['descripcion'] = descripcion
        print(f"  Descripción: '{descripcion}'")
    
    # Buscar precios (números decimales)
    import re
    precios = re.findall(r'\d+\.\d+', linea)
    if precios:
        print(f"  Precios encontrados: {precios[:5]}...")  # Mostrar solo los primeros 5
    
    # Buscar fechas (formato YYYYMMDD)
    fechas = re.findall(r'\d{8}', linea)
    if fechas:
        print(f"  Fechas encontradas: {fechas}")
    
    # Buscar códigos de moneda
    monedas = re.findall(r'[A-Z]{3}', linea)
    if monedas:
        print(f"  Monedas encontradas: {monedas}")
    
    # Buscar códigos de estado/indicadores
    indicadores = re.findall(r'[A-Z]{2,4}', linea)
    if indicadores:
        print(f"  Indicadores encontrados: {indicadores[:5]}...")

def generar_esquema_campos(archivo_path, num_muestras=100):
    """Genera un esquema de campos basado en múltiples líneas"""
    
    print(f"\n🔬 Generando esquema de campos con {num_muestras} muestras...")
    
    esquema = {
        'codigos': set(),
        'descripciones': set(),
        'precios': [],
        'fechas': set(),
        'monedas': set(),
        'indicadores': set()
    }
    
    import re
    
    with open(archivo_path, 'r', encoding='utf-8', errors='ignore') as f:
        for i, linea in enumerate(f):
            if i >= num_muestras:
                break
                
            linea = linea.rstrip('\n\r')
            
            # Códigos
            if len(linea) >= 15:
                codigo = linea[:15].strip()
                if codigo:
                    esquema['codigos'].add(codigo)
            
            # Descripciones
            if len(linea) >= 80:
                desc_start = 15
                desc_end = 80
                descripcion = linea[desc_start:desc_end].strip()
                if descripcion and len(descripcion) > 3:
                    esquema['descripciones'].add(descripcion)
            
            # Precios
            precios = re.findall(r'\d+\.\d+', linea)
            esquema['precios'].extend(precios[:3])  # Solo los primeros 3
            
            # Fechas
            fechas = re.findall(r'\d{8}', linea)
            esquema['fechas'].update(fechas)
            
            # Monedas
            monedas = re.findall(r'[A-Z]{3}', linea)
            esquema['monedas'].update(monedas)
            
            # Indicadores
            indicadores = re.findall(r'[A-Z]{2,4}', linea)
            esquema['indicadores'].update(indicadores)
    
    # Mostrar resultados
    print(f"\n📊 Resultados del análisis:")
    print(f"  Códigos únicos: {len(esquema['codigos'])}")
    print(f"  Descripciones únicas: {len(esquema['descripciones'])}")
    print(f"  Precios encontrados: {len(esquema['precios'])}")
    print(f"  Fechas únicas: {len(esquema['fechas'])}")
    print(f"  Monedas: {esquema['monedas']}")
    print(f"  Indicadores únicos: {len(esquema['indicadores'])}")
    
    # Mostrar ejemplos
    print(f"\n📝 Ejemplos de códigos: {list(esquema['codigos'])[:10]}")
    print(f"📝 Ejemplos de descripciones: {list(esquema['descripciones'])[:5]}")
    print(f"📝 Ejemplos de precios: {esquema['precios'][:10]}")
    print(f"📝 Fechas encontradas: {sorted(list(esquema['fechas']))[:5]}")

if __name__ == "__main__":
    archivo = "AR.DMS.DWNLD.V2-2025-06-05"
    
    if not os.path.exists(archivo):
        print(f"❌ Error: El archivo {archivo} no existe")
        sys.exit(1)
    
    # Análisis básico
    analizar_estructura_archivo(archivo, num_lineas=5)
    
    # Generar esquema
    generar_esquema_campos(archivo, num_muestras=50)
    
    print(f"\n✅ Análisis completado!") 