#!/usr/bin/env python3
"""
Script para analizar el archivo Excel del Libro IVA
Extrae información sobre ventas de repuestos (RE), maquinarias (MN) y servicios (SE)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re

def analizar_libro_iva(archivo_excel):
    """Analiza el archivo Excel del Libro IVA"""
    
    print("=" * 80)
    print("ANÁLISIS DEL LIBRO IVA - JULIO 2025")
    print("=" * 80)
    
    try:
        # Leer el archivo Excel
        df = pd.read_excel(archivo_excel)
        
        print(f"\n📊 INFORMACIÓN GENERAL:")
        print(f"   • Filas totales: {len(df)}")
        print(f"   • Columnas: {list(df.columns)}")
        print(f"   • Tamaño del archivo: {df.shape}")
        
        # Mostrar las primeras filas para entender la estructura
        print(f"\n📋 PRIMERAS 10 FILAS:")
        print(df.head(10).to_string())
        
        # Buscar columnas que contengan información relevante
        columnas_relevantes = []
        for col in df.columns:
            if any(palabra in str(col).upper() for palabra in ['FECHA', 'TIPO', 'COMPROBANTE', 'CLIENTE', 'MONTO', 'IVA', 'NETO', 'TOTAL']):
                columnas_relevantes.append(col)
        
        print(f"\n🎯 COLUMNAS RELEVANTES ENCONTRADAS:")
        for col in columnas_relevantes:
            print(f"   • {col}")
        
        # Buscar patrones de códigos (RE, MN, SE)
        print(f"\n🔍 BUSCANDO PATRONES DE CÓDIGOS (RE, MN, SE):")
        
        # Buscar en todas las columnas de texto
        for col in df.columns:
            if df[col].dtype == 'object':  # Columnas de texto
                valores_unicos = df[col].dropna().unique()
                for valor in valores_unicos:
                    if isinstance(valor, str):
                        # Buscar patrones RE, MN, SE
                        if re.search(r'\b(RE|MN|SE)\b', valor.upper()):
                            print(f"   • Columna '{col}': {valor}")
        
        # Analizar tipos de comprobantes
        print(f"\n📄 TIPOS DE COMPROBANTES:")
        if 'TIPO' in df.columns:
            tipos = df['TIPO'].value_counts()
            print(tipos.to_string())
        elif 'COMPROBANTE' in df.columns:
            tipos = df['COMPROBANTE'].value_counts()
            print(tipos.to_string())
        
        # Analizar montos y totales
        print(f"\n💰 ANÁLISIS DE MONTOS:")
        columnas_monetarias = []
        for col in df.columns:
            if any(palabra in str(col).upper() for palabra in ['MONTO', 'TOTAL', 'NETO', 'IVA', 'PRECIO']):
                columnas_monetarias.append(col)
        
        for col in columnas_monetarias:
            if df[col].dtype in ['int64', 'float64']:
                print(f"   • {col}:")
                print(f"     - Total: ${df[col].sum():,.2f}")
                print(f"     - Promedio: ${df[col].mean():,.2f}")
                print(f"     - Máximo: ${df[col].max():,.2f}")
                print(f"     - Mínimo: ${df[col].min():,.2f}")
        
        # Buscar información específica por categorías
        print(f"\n🏷️ ANÁLISIS POR CATEGORÍAS:")
        
        # Buscar repuestos (RE)
        print(f"\n🔧 REPUESTOS (RE):")
        for col in df.columns:
            if df[col].dtype == 'object':
                repuestos = df[df[col].astype(str).str.contains('RE', case=False, na=False)]
                if len(repuestos) > 0:
                    print(f"   • Encontrados {len(repuestos)} registros de repuestos en columna '{col}'")
                    print(f"   • Valores únicos: {repuestos[col].unique()[:5]}")  # Primeros 5
        
        # Buscar maquinarias (MN)
        print(f"\n🚜 MAQUINARIAS (MN):")
        for col in df.columns:
            if df[col].dtype == 'object':
                maquinarias = df[df[col].astype(str).str.contains('MN', case=False, na=False)]
                if len(maquinarias) > 0:
                    print(f"   • Encontrados {len(maquinarias)} registros de maquinarias en columna '{col}'")
                    print(f"   • Valores únicos: {maquinarias[col].unique()[:5]}")  # Primeros 5
        
        # Buscar servicios (SE)
        print(f"\n🔧 SERVICIOS (SE):")
        for col in df.columns:
            if df[col].dtype == 'object':
                servicios = df[df[col].astype(str).str.contains('SE', case=False, na=False)]
                if len(servicios) > 0:
                    print(f"   • Encontrados {len(servicios)} registros de servicios en columna '{col}'")
                    print(f"   • Valores únicos: {servicios[col].unique()[:5]}")  # Primeros 5
        
        # Mostrar estadísticas generales
        print(f"\n📈 ESTADÍSTICAS GENERALES:")
        print(f"   • Registros con datos completos: {df.dropna().shape[0]}")
        print(f"   • Registros con datos faltantes: {df.shape[0] - df.dropna().shape[0]}")
        
        # Guardar información para importación
        print(f"\n💾 INFORMACIÓN PARA IMPORTACIÓN:")
        print(f"   • Estructura de columnas identificada")
        print(f"   • Patrones de códigos encontrados")
        print(f"   • Tipos de datos detectados")
        
        return df
        
    except Exception as e:
        print(f"❌ Error al analizar el archivo: {e}")
        return None

def sugerir_importacion(df):
    """Sugiere cómo importar los datos a la aplicación"""
    
    print(f"\n" + "=" * 80)
    print("SUGERENCIAS PARA IMPORTACIÓN")
    print("=" * 80)
    
    if df is None:
        print("❌ No se puede sugerir importación sin datos válidos")
        return
    
    print(f"\n🎯 ESTRATEGIA DE IMPORTACIÓN:")
    print(f"   1. Crear modelo 'LibroIva' para almacenar registros mensuales")
    print(f"   2. Implementar función de importación desde Excel")
    print(f"   3. Categorizar automáticamente por códigos (RE/MN/SE)")
    print(f"   4. Vincular con clientes existentes")
    print(f"   5. Generar reportes de ventas por categoría")
    
    print(f"\n📊 DATOS QUE SE PUEDEN EXTRAER:")
    print(f"   • Ventas de Repuestos (RE): Cantidad, montos, clientes")
    print(f"   • Ventas de Maquinarias (MN): Equipos, valores, clientes")
    print(f"   • Ventas de Servicios (SE): Tipos de servicio, horas, clientes")
    print(f"   • Análisis de rentabilidad por categoría")
    print(f"   • Tendencias mensuales de ventas")
    
    print(f"\n🔧 FUNCIONALIDADES SUGERIDAS:")
    print(f"   • Dashboard de ventas por categoría")
    print(f"   • Reportes de rentabilidad")
    print(f"   • Análisis de clientes más frecuentes")
    print(f"   • Comparativas mensuales")
    print(f"   • Exportación de datos procesados")

if __name__ == "__main__":
    # Analizar el archivo
    df = analizar_libro_iva("LIBRO IVA 07-2025.xlsx")
    
    # Sugerir estrategia de importación
    sugerir_importacion(df) 