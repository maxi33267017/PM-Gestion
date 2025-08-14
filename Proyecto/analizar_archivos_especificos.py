#!/usr/bin/env python3
"""
Script para analizar archivos Excel específicos de datos de utilización y notificaciones
"""
import pandas as pd
import os
import glob

def analizar_archivo_especifico(nombre_archivo):
    """Analizar un archivo Excel específico"""
    print(f"\n{'='*80}")
    print(f"ANALIZANDO: {nombre_archivo}")
    print(f"{'='*80}")
    
    try:
        # Verificar si el archivo existe
        if not os.path.exists(nombre_archivo):
            print(f"❌ Archivo no encontrado: {nombre_archivo}")
            return False
        
        # Leer todas las hojas del Excel
        excel_file = pd.ExcelFile(nombre_archivo)
        print(f"✅ Archivo encontrado - Hojas disponibles: {excel_file.sheet_names}")
        
        for sheet_name in excel_file.sheet_names:
            print(f"\n{'='*60}")
            print(f"📊 HOJA: {sheet_name}")
            print(f"{'='*60}")
            
            # Leer la hoja
            df = pd.read_excel(nombre_archivo, sheet_name=sheet_name)
            
            print(f"📈 Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")
            print(f"📋 Columnas: {list(df.columns)}")
            
            # Mostrar tipos de datos
            print(f"\n🔍 Tipos de datos:")
            for col in df.columns:
                print(f"  {col}: {df[col].dtype}")
            
            # Mostrar primeras filas
            print(f"\n📄 Primeras 3 filas:")
            print(df.head(3).to_string())
            
            # Mostrar valores únicos en columnas importantes
            print(f"\n🎯 Valores únicos por columna (primeros 10):")
            for col in df.columns:
                unique_vals = df[col].dropna().unique()
                if len(unique_vals) <= 10:
                    print(f"  {col}: {unique_vals}")
                else:
                    print(f"  {col}: {unique_vals[:10]}... (total: {len(unique_vals)})")
            
            # Estadísticas básicas para columnas numéricas
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                print(f"\n📊 Estadísticas básicas (columnas numéricas):")
                print(df[numeric_cols].describe())
            
            print(f"\n{'='*60}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error analizando {nombre_archivo}: {str(e)}")
        return False

def buscar_archivos_similares():
    """Buscar archivos con nombres similares"""
    print("\n🔍 BUSCANDO ARCHIVOS SIMILARES...")
    print("="*60)
    
    # Buscar archivos que contengan ciertas palabras clave
    patrones = [
        "Analizador*",
        "Notificaciones*",
        "*máquina*",
        "*utilizacion*",
        "*datos*"
    ]
    
    archivos_encontrados = []
    
    for patron in patrones:
        archivos = glob.glob(f"**/{patron}*.xlsx", recursive=True)
        archivos_encontrados.extend(archivos)
    
    # También buscar en el directorio actual
    for archivo in os.listdir('.'):
        if archivo.endswith('.xlsx') and any(palabra in archivo.lower() for palabra in ['analizador', 'notificaciones', 'máquina', 'utilizacion', 'datos']):
            archivos_encontrados.append(archivo)
    
    if archivos_encontrados:
        print(f"📁 Archivos encontrados ({len(set(archivos_encontrados))}):")
        for archivo in sorted(set(archivos_encontrados)):
            print(f"  - {archivo}")
    else:
        print("❌ No se encontraron archivos similares")
    
    return list(set(archivos_encontrados))

def main():
    """Función principal"""
    print("🔬 ANALIZADOR DE ARCHIVOS EXCEL ESPECÍFICOS")
    print("="*80)
    
    # Archivos específicos que mencionaste
    archivos_especificos = [
        "Analizador_de_máquina_01_07_2025-31_07_2025 (1).xlsx",
        "Notificaciones_14_08_2025, 09_50 a.m..xlsx"
    ]
    
    print("🎯 ANALIZANDO ARCHIVOS ESPECÍFICOS...")
    archivos_analizados = []
    
    for archivo in archivos_especificos:
        if analizar_archivo_especifico(archivo):
            archivos_analizados.append(archivo)
    
    if not archivos_analizados:
        print("\n⚠️ No se pudieron analizar los archivos específicos.")
        print("🔍 Buscando archivos similares...")
        archivos_similares = buscar_archivos_similares()
        
        if archivos_similares:
            print(f"\n📊 Analizando archivos similares encontrados...")
            for archivo in archivos_similares:
                analizar_archivo_especifico(archivo)
    
    print(f"\n✅ Análisis completado!")

if __name__ == "__main__":
    main()
