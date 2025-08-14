#!/usr/bin/env python3
"""
Script para analizar archivos Excel y entender su estructura
"""
import pandas as pd
import os
from pathlib import Path

def analizar_excel(archivo_path):
    """Analizar la estructura de un archivo Excel"""
    print(f"\n{'='*60}")
    print(f"ANALIZANDO: {archivo_path}")
    print(f"{'='*60}")
    
    try:
        # Leer todas las hojas del Excel
        excel_file = pd.ExcelFile(archivo_path)
        print(f"Hojas disponibles: {excel_file.sheet_names}")
        
        for sheet_name in excel_file.sheet_names:
            print(f"\n--- HOJA: {sheet_name} ---")
            
            # Leer la hoja
            df = pd.read_excel(archivo_path, sheet_name=sheet_name)
            
            print(f"Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")
            print(f"Columnas: {list(df.columns)}")
            
            # Mostrar tipos de datos
            print(f"Tipos de datos:")
            for col in df.columns:
                print(f"  {col}: {df[col].dtype}")
            
            # Mostrar primeras filas
            print(f"\nPrimeras 3 filas:")
            print(df.head(3).to_string())
            
            # Mostrar valores únicos en columnas importantes
            print(f"\nValores únicos por columna (primeros 10):")
            for col in df.columns:
                unique_vals = df[col].dropna().unique()
                if len(unique_vals) <= 10:
                    print(f"  {col}: {unique_vals}")
                else:
                    print(f"  {col}: {unique_vals[:10]}... (total: {len(unique_vals)})")
            
            # Estadísticas básicas para columnas numéricas
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                print(f"\nEstadísticas básicas (columnas numéricas):")
                print(df[numeric_cols].describe())
            
            print(f"\n{'='*60}")
    
    except Exception as e:
        print(f"Error analizando {archivo_path}: {str(e)}")

def main():
    """Función principal"""
    print("ANALIZADOR DE ARCHIVOS EXCEL")
    print("="*60)
    
    # Buscar archivos Excel en el directorio actual y subdirectorios
    archivos_excel = []
    
    # Buscar en directorio actual y subdirectorios
    for root, dirs, files in os.walk('.'):
        for archivo in files:
            if archivo.endswith(('.xlsx', '.xls')):
                archivo_path = os.path.join(root, archivo)
                archivos_excel.append(archivo_path)
    
    if not archivos_excel:
        print("No se encontraron archivos Excel.")
        return
    
    print(f"Archivos Excel encontrados ({len(archivos_excel)}):")
    for archivo in archivos_excel:
        print(f"  - {archivo}")
    
    print(f"\nAnalizando todos los archivos Excel...")
    
    # Analizar cada archivo
    for archivo in archivos_excel:
        analizar_excel(archivo)

if __name__ == "__main__":
    main()
