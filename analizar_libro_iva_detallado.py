#!/usr/bin/env python3
"""
Script detallado para analizar el Libro IVA con las columnas específicas
Analiza: Fecha, Cliente (sin título), CUIT, Tipo de cuenta (SE/RE/MN), 
Número de comprobante, Descripción, NETO, NO Gravado, TOTAL, Sucursal
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re

def analizar_libro_iva_detallado(archivo_excel):
    """Analiza el archivo Excel del Libro IVA con las columnas específicas"""
    
    print("=" * 80)
    print("ANÁLISIS DETALLADO DEL LIBRO IVA - JULIO 2025")
    print("=" * 80)
    
    try:
        # Leer el archivo Excel
        df = pd.read_excel(archivo_excel)
        
        print(f"\n📊 INFORMACIÓN GENERAL:")
        print(f"   • Filas totales: {len(df)}")
        print(f"   • Columnas totales: {len(df.columns)}")
        print(f"   • Tamaño del archivo: {df.shape}")
        
        # Mostrar todas las columnas para identificar la estructura
        print(f"\n📋 ESTRUCTURA DE COLUMNAS:")
        for i, col in enumerate(df.columns):
            print(f"   {i:2d}. '{col}'")
        
        # Mostrar las primeras filas para entender la estructura
        print(f"\n📋 PRIMERAS 5 FILAS (TODAS LAS COLUMNAS):")
        print(df.head().to_string())
        
        # Buscar la columna sin título (entre Fecha y CUIT)
        print(f"\n🔍 BUSCANDO COLUMNA SIN TÍTULO (CLIENTES):")
        
        # Identificar columnas que podrían ser nombres de clientes
        columnas_posibles_clientes = []
        for i, col in enumerate(df.columns):
            if pd.isna(col) or col == '' or 'Unnamed' in str(col):
                columnas_posibles_clientes.append((i, col))
                print(f"   • Columna {i}: '{col}' (posible columna de clientes)")
        
        # Buscar columnas con CUIT
        columnas_cuit = []
        for i, col in enumerate(df.columns):
            if 'CUIT' in str(col).upper() or 'DOC' in str(col).upper():
                columnas_cuit.append((i, col))
                print(f"   • Columna {i}: '{col}' (posible CUIT)")
        
        # Buscar columnas con tipo de cuenta
        columnas_tipo_cuenta = []
        for i, col in enumerate(df.columns):
            if 'TIPO' in str(col).upper() and 'CUENTA' in str(col).upper():
                columnas_tipo_cuenta.append((i, col))
                print(f"   • Columna {i}: '{col}' (posible tipo de cuenta)")
        
        # Buscar columnas con número de comprobante
        columnas_comprobante = []
        for i, col in enumerate(df.columns):
            if 'COMPROBANTE' in str(col).upper() or 'NÚMERO' in str(col).upper():
                columnas_comprobante.append((i, col))
                print(f"   • Columna {i}: '{col}' (posible número de comprobante)")
        
        # Buscar columnas con descripción
        columnas_descripcion = []
        for i, col in enumerate(df.columns):
            if 'DESCRIPCIÓN' in str(col).upper() or 'DESCRIPCION' in str(col).upper():
                columnas_descripcion.append((i, col))
                print(f"   • Columna {i}: '{col}' (posible descripción)")
        
        # Buscar columnas monetarias
        columnas_monetarias = []
        for i, col in enumerate(df.columns):
            if any(palabra in str(col).upper() for palabra in ['NETO', 'TOTAL', 'GRAVADO', 'IVA']):
                columnas_monetarias.append((i, col))
                print(f"   • Columna {i}: '{col}' (posible monto)")
        
        # Buscar columnas de sucursal
        columnas_sucursal = []
        for i, col in enumerate(df.columns):
            if 'SUCURSAL' in str(col).upper() or 'PUNTO' in str(col).upper():
                columnas_sucursal.append((i, col))
                print(f"   • Columna {i}: '{col}' (posible sucursal)")
        
        # Analizar valores únicos en columnas clave
        print(f"\n📊 ANÁLISIS DE VALORES ÚNICOS:")
        
        # Analizar tipos de cuenta si se encontraron
        if columnas_tipo_cuenta:
            for i, col in columnas_tipo_cuenta:
                print(f"\n🏷️ TIPOS DE CUENTA EN COLUMNA '{col}':")
                valores_unicos = df[col].dropna().unique()
                for valor in valores_unicos:
                    print(f"   • {valor}")
        
        # Analizar sucursales si se encontraron
        if columnas_sucursal:
            for i, col in columnas_sucursal:
                print(f"\n🏢 SUCURSALES EN COLUMNA '{col}':")
                valores_unicos = df[col].dropna().unique()
                for valor in valores_unicos:
                    print(f"   • {valor}")
        
        # Analizar montos en pesos
        print(f"\n💰 ANÁLISIS DE MONTOS (EN PESOS):")
        for i, col in columnas_monetarias:
            if df[col].dtype in ['int64', 'float64']:
                print(f"\n   📊 COLUMNA '{col}':")
                print(f"     - Total: ${df[col].sum():,.2f} pesos")
                print(f"     - Promedio: ${df[col].mean():,.2f} pesos")
                print(f"     - Máximo: ${df[col].max():,.2f} pesos")
                print(f"     - Mínimo: ${df[col].min():,.2f} pesos")
                print(f"     - Registros con valor: {df[col].notna().sum()}")
        
        # Categorizar por tipo de cuenta
        print(f"\n🏷️ CATEGORIZACIÓN POR TIPO DE CUENTA:")
        
        if columnas_tipo_cuenta:
            for i, col in columnas_tipo_cuenta:
                print(f"\n   📊 ANÁLISIS DE COLUMNA '{col}':")
                
                # Buscar RE (Repuestos)
                repuestos = df[df[col].astype(str).str.contains('RE', case=False, na=False)]
                if len(repuestos) > 0:
                    print(f"     🔧 REPUESTOS (RE): {len(repuestos)} registros")
                    if columnas_monetarias:
                        for j, col_mon in columnas_monetarias:
                            if df[col_mon].dtype in ['int64', 'float64']:
                                total = repuestos[col_mon].sum()
                                print(f"       - Total {col_mon}: ${total:,.2f} pesos")
                
                # Buscar MN (Maquinarias)
                maquinarias = df[df[col].astype(str).str.contains('MN', case=False, na=False)]
                if len(maquinarias) > 0:
                    print(f"     🚜 MAQUINARIAS (MN): {len(maquinarias)} registros")
                    if columnas_monetarias:
                        for j, col_mon in columnas_monetarias:
                            if df[col_mon].dtype in ['int64', 'float64']:
                                total = maquinarias[col_mon].sum()
                                print(f"       - Total {col_mon}: ${total:,.2f} pesos")
                
                # Buscar SE (Servicios)
                servicios = df[df[col].astype(str).str.contains('SE', case=False, na=False)]
                if len(servicios) > 0:
                    print(f"     🔧 SERVICIOS (SE): {len(servicios)} registros")
                    if columnas_monetarias:
                        for j, col_mon in columnas_monetarias:
                            if df[col_mon].dtype in ['int64', 'float64']:
                                total = servicios[col_mon].sum()
                                print(f"       - Total {col_mon}: ${total:,.2f} pesos")
        
        # Analizar por sucursal
        print(f"\n🏢 ANÁLISIS POR SUCURSAL:")
        if columnas_sucursal:
            for i, col in columnas_sucursal:
                print(f"\n   📊 SUCURSAL EN COLUMNA '{col}':")
                sucursales = df[col].value_counts()
                for sucursal, cantidad in sucursales.items():
                    print(f"     • {sucursal}: {cantidad} registros")
                    
                    # Filtrar por sucursal y analizar montos
                    df_sucursal = df[df[col] == sucursal]
                    if columnas_monetarias:
                        for j, col_mon in columnas_monetarias:
                            if df[col_mon].dtype in ['int64', 'float64']:
                                total = df_sucursal[col_mon].sum()
                                print(f"       - Total {col_mon}: ${total:,.2f} pesos")
        
        # Mostrar ejemplos de registros
        print(f"\n📋 EJEMPLOS DE REGISTROS:")
        if columnas_tipo_cuenta and columnas_monetarias:
            for i, col_tipo in columnas_tipo_cuenta:
                for j, col_mon in columnas_monetarias:
                    if df[col_mon].dtype in ['int64', 'float64']:
                        print(f"\n   📊 REGISTROS CON VALORES EN '{col_mon}':")
                        muestra = df[df[col_mon].notna()].head(3)
                        for idx, row in muestra.iterrows():
                            tipo_cuenta = row[col_tipo] if col_tipo in row else "N/A"
                            monto = row[col_mon]
                            print(f"     • Tipo: {tipo_cuenta}, Monto: ${monto:,.2f} pesos")
        
        return df
        
    except Exception as e:
        print(f"❌ Error al analizar el archivo: {e}")
        return None

def sugerir_estructura_importacion(df):
    """Sugiere la estructura de importación basada en el análisis"""
    
    print(f"\n" + "=" * 80)
    print("ESTRUCTURA DE IMPORTACIÓN SUGERIDA")
    print("=" * 80)
    
    if df is None:
        print("❌ No se puede sugerir estructura sin datos válidos")
        return
    
    print(f"\n🎯 MODELO DE DATOS OPTIMIZADO:")
    print(f"""
class LibroIva(models.Model):
    fecha = models.DateField()
    cliente = models.CharField(max_length=200)  # Columna sin título
    cuit = models.CharField(max_length=20)
    tipo_cuenta = models.CharField(max_length=10, choices=[
        ('RE', 'Repuestos'),
        ('MN', 'Maquinarias'),
        ('SE', 'Servicios'),
        ('OT', 'Otros')
    ])
    numero_comprobante = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True)
    neto = models.DecimalField(max_digits=15, decimal_places=2)
    no_gravado = models.DecimalField(max_digits=15, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    sucursal = models.CharField(max_length=50)
    mes = models.IntegerField()
    año = models.IntegerField()
    
    class Meta:
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['tipo_cuenta']),
            models.Index(fields=['sucursal']),
            models.Index(fields=['mes', 'año']),
        ]
    """)
    
    print(f"\n🔧 FUNCIÓN DE IMPORTACIÓN:")
    print(f"""
def importar_libro_iva_optimizado(archivo_excel, mes, año):
    '''Importa datos del Libro IVA con estructura optimizada'''
    
    # Leer archivo Excel
    df = pd.read_excel(archivo_excel)
    
    # Mapear columnas específicas
    # (Aquí se mapearían las columnas según el análisis)
    
    for _, row in df.iterrows():
        LibroIva.objects.create(
            fecha=row['Fecha'],
            cliente=row['Cliente'],  # Columna sin título
            cuit=row['CUIT'],
            tipo_cuenta=row['Tipo_Cuenta'],
            numero_comprobante=row['Numero_Comprobante'],
            descripcion=row['Descripcion'],
            neto=row['Neto'],
            no_gravado=row['No_Gravado'],
            total=row['Total'],
            sucursal=row['Sucursal'],
            mes=mes,
            año=año
        )
    
    return len(df)
    """)

if __name__ == "__main__":
    # Analizar el archivo con detalle
    df = analizar_libro_iva_detallado("LIBRO IVA 07-2025.xlsx")
    
    # Sugerir estructura de importación
    sugerir_estructura_importacion(df) 