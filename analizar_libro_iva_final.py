#!/usr/bin/env python3
"""
Análisis final del Libro IVA basado en la estructura real encontrada
Analiza: Fecha, Denominación Receptor (clientes), CUIT, Punto de Venta (sucursal),
Número Desde (comprobante), montos en pesos
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re

def analizar_libro_iva_final(archivo_excel):
    """Análisis final del Libro IVA con la estructura real"""
    
    print("=" * 80)
    print("ANÁLISIS FINAL DEL LIBRO IVA - JULIO 2025")
    print("=" * 80)
    
    try:
        # Leer el archivo Excel
        df = pd.read_excel(archivo_excel)
        
        print(f"\n📊 ESTRUCTURA REAL ENCONTRADA:")
        print(f"   • Total registros: {len(df)}")
        print(f"   • Columnas identificadas:")
        print(f"     - Fecha: {df.columns[0]}")
        print(f"     - Tipo: {df.columns[1]}")
        print(f"     - Punto de Venta (Sucursal): {df.columns[2]}")
        print(f"     - Número Desde (Comprobante): {df.columns[3]}")
        print(f"     - Denominación Receptor (Cliente): {df.columns[7]}")
        print(f"     - Nro. Doc. Receptor (CUIT): {df.columns[6]}")
        print(f"     - Imp. Neto Gravado (NETO): {df.columns[10]}")
        print(f"     - Imp. Neto No Gravado (NO Gravado): {df.columns[12]}")
        print(f"     - Imp. Total (TOTAL): {df.columns[20]}")
        
        # Analizar sucursales (Punto de Venta)
        print(f"\n🏢 ANÁLISIS DE SUCURSALES:")
        sucursales = df['Punto de Venta'].value_counts().sort_index()
        for sucursal, cantidad in sucursales.items():
            print(f"   • Sucursal {sucursal}: {cantidad} registros")
        
        # Mapear sucursales a nombres
        mapeo_sucursales = {
            1: "Rio Grande",
            2: "Comodoro", 
            4: "Sucursal 4",
            7: "Sucursal 7",
            8: "Sucursal 8",
            9: "Sucursal 9",
            10: "Sucursal 10",
            11: "Sucursal 11"
        }
        
        print(f"\n🏢 SUCURSALES CON NOMBRES:")
        for sucursal, cantidad in sucursales.items():
            nombre = mapeo_sucursales.get(sucursal, f"Sucursal {sucursal}")
            print(f"   • {nombre} (Punto {sucursal}): {cantidad} registros")
        
        # Analizar montos en pesos
        print(f"\n💰 ANÁLISIS DE MONTOS (EN PESOS):")
        
        # Usar las columnas correctas
        neto_col = 'Imp. Neto Gravado'
        no_gravado_col = 'Imp. Neto No Gravado'
        total_col = 'Imp. Total'
        
        print(f"\n   📊 NETO (Imp. Neto Gravado):")
        print(f"     - Total: ${df[neto_col].sum():,.2f} pesos")
        print(f"     - Promedio: ${df[neto_col].mean():,.2f} pesos")
        print(f"     - Máximo: ${df[neto_col].max():,.2f} pesos")
        print(f"     - Mínimo: ${df[neto_col].min():,.2f} pesos")
        
        print(f"\n   📊 NO GRAVADO (Imp. Neto No Gravado):")
        print(f"     - Total: ${df[no_gravado_col].sum():,.2f} pesos")
        print(f"     - Promedio: ${df[no_gravado_col].mean():,.2f} pesos")
        print(f"     - Máximo: ${df[no_gravado_col].max():,.2f} pesos")
        print(f"     - Mínimo: ${df[no_gravado_col].min():,.2f} pesos")
        
        print(f"\n   📊 TOTAL (Imp. Total):")
        print(f"     - Total: ${df[total_col].sum():,.2f} pesos")
        print(f"     - Promedio: ${df[total_col].mean():,.2f} pesos")
        print(f"     - Máximo: ${df[total_col].max():,.2f} pesos")
        print(f"     - Mínimo: ${df[total_col].min():,.2f} pesos")
        
        # Analizar por sucursal
        print(f"\n🏢 ANÁLISIS POR SUCURSAL:")
        for sucursal in sucursales.index:
            df_sucursal = df[df['Punto de Venta'] == sucursal]
            nombre = mapeo_sucursales.get(sucursal, f"Sucursal {sucursal}")
            
            print(f"\n   📊 {nombre} (Punto {sucursal}):")
            print(f"     - Registros: {len(df_sucursal)}")
            print(f"     - Total Neto: ${df_sucursal[neto_col].sum():,.2f} pesos")
            print(f"     - Total No Gravado: ${df_sucursal[no_gravado_col].sum():,.2f} pesos")
            print(f"     - Total General: ${df_sucursal[total_col].sum():,.2f} pesos")
        
        # Top clientes por volumen
        print(f"\n👥 TOP 10 CLIENTES POR VOLUMEN:")
        clientes_volumen = df.groupby('Denominación Receptor')[total_col].sum().sort_values(ascending=False)
        for i, (cliente, monto) in enumerate(clientes_volumen.head(10).items(), 1):
            print(f"   {i:2d}. {cliente[:50]:<50} ${monto:>12,.2f}")
        
        # Buscar patrones en nombres de clientes para categorizar
        print(f"\n🏷️ CATEGORIZACIÓN POR PATRONES EN NOMBRES:")
        
        # Patrones para identificar tipos de venta
        patrones_repuestos = [
            'REPUESTO', 'FILTRO', 'ACEITE', 'BATERIA', 'FRENO', 'EMBRAGUE',
            'NEUMATICO', 'LUBRICANTE', 'MOTOR', 'TRANSMISION', 'HIDRAULICO'
        ]
        
        patrones_maquinarias = [
            'MAQUINA', 'TRACTOR', 'EXCAVADORA', 'CARGADOR', 'MARTILLO',
            'COMPRESOR', 'GENERADOR', 'SOLDADORA', 'MOTOSIERRA', 'EQUIPO'
        ]
        
        patrones_servicios = [
            'SERVICIO', 'MANTENIMIENTO', 'REPARACION', 'INSTALACION',
            'MONTAJE', 'DIAGNOSTICO', 'REVISION', 'CALIBRACION'
        ]
        
        # Categorizar por patrones en nombres de clientes
        repuestos = df[df['Denominación Receptor'].str.contains('|'.join(patrones_repuestos), case=False, na=False)]
        maquinarias = df[df['Denominación Receptor'].str.contains('|'.join(patrones_maquinarias), case=False, na=False)]
        servicios = df[df['Denominación Receptor'].str.contains('|'.join(patrones_servicios), case=False, na=False)]
        
        print(f"\n🔧 REPUESTOS (por patrones en nombres):")
        print(f"   • Registros identificados: {len(repuestos)}")
        if len(repuestos) > 0:
            print(f"   • Total: ${repuestos[total_col].sum():,.2f} pesos")
            print(f"   • Promedio: ${repuestos[total_col].mean():,.2f} pesos")
        
        print(f"\n🚜 MAQUINARIAS (por patrones en nombres):")
        print(f"   • Registros identificados: {len(maquinarias)}")
        if len(maquinarias) > 0:
            print(f"   • Total: ${maquinarias[total_col].sum():,.2f} pesos")
            print(f"   • Promedio: ${maquinarias[total_col].mean():,.2f} pesos")
        
        print(f"\n🔧 SERVICIOS (por patrones en nombres):")
        print(f"   • Registros identificados: {len(servicios)}")
        if len(servicios) > 0:
            print(f"   • Total: ${servicios[total_col].sum():,.2f} pesos")
            print(f"   • Promedio: ${servicios[total_col].mean():,.2f} pesos")
        
        # Mostrar ejemplos de registros
        print(f"\n📋 EJEMPLOS DE REGISTROS:")
        print(f"   📊 PRIMEROS 5 REGISTROS:")
        for i, (idx, row) in enumerate(df.head().iterrows(), 1):
            print(f"     {i}. Cliente: {row['Denominación Receptor'][:40]}")
            print(f"        CUIT: {row['Nro. Doc. Receptor']}")
            punto_venta = row['Punto de Venta']
            nombre_sucursal = mapeo_sucursales.get(punto_venta, f'Sucursal {punto_venta}')
            print(f"        Sucursal: {nombre_sucursal}")
            print(f"        Comprobante: {row['Número Desde']}")
            print(f"        Total: ${row[total_col]:,.2f} pesos")
            print()
        
        return df
        
    except Exception as e:
        print(f"❌ Error al analizar el archivo: {e}")
        return None

def sugerir_implementacion_final(df):
    """Sugiere la implementación final basada en el análisis real"""
    
    print(f"\n" + "=" * 80)
    print("IMPLEMENTACIÓN FINAL SUGERIDA")
    print("=" * 80)
    
    if df is None:
        print("❌ No se puede sugerir implementación sin datos válidos")
        return
    
    print(f"\n🎯 MODELO DE DATOS FINAL:")
    print(f"""
class LibroIva(models.Model):
    fecha = models.DateField()
    tipo_comprobante = models.CharField(max_length=50)
    sucursal = models.CharField(max_length=50)  # Punto de Venta
    numero_comprobante = models.IntegerField()  # Número Desde
    cod_autorizacion = models.CharField(max_length=50)
    tipo_doc_receptor = models.CharField(max_length=20)
    cuit = models.CharField(max_length=20)  # Nro. Doc. Receptor
    cliente = models.CharField(max_length=200)  # Denominación Receptor
    tipo_cambio = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=10)
    neto = models.DecimalField(max_digits=15, decimal_places=2)  # Imp. Neto Gravado
    no_gravado = models.DecimalField(max_digits=15, decimal_places=2)  # Imp. Neto No Gravado
    exentas = models.DecimalField(max_digits=15, decimal_places=2)  # Imp. Op. Exentas
    iva = models.DecimalField(max_digits=15, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2)  # Imp. Total
    categoria = models.CharField(max_length=10, choices=[
        ('RE', 'Repuestos'),
        ('MN', 'Maquinarias'),
        ('SE', 'Servicios'),
        ('OT', 'Otros')
    ], default='OT')
    mes = models.IntegerField()
    año = models.IntegerField()
    
    class Meta:
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['sucursal']),
            models.Index(fields=['categoria']),
            models.Index(fields=['mes', 'año']),
        ]
    """)
    
    print(f"\n🔧 FUNCIÓN DE IMPORTACIÓN FINAL:")
    print(f"""
def importar_libro_iva_final(archivo_excel, mes, año):
    '''Importa datos del Libro IVA con estructura real'''
    
    # Leer archivo Excel
    df = pd.read_excel(archivo_excel)
    
    # Mapeo de sucursales
    mapeo_sucursales = {
        1: "Rio Grande",
        2: "Comodoro", 
        4: "Sucursal 4",
        7: "Sucursal 7",
        8: "Sucursal 8",
        9: "Sucursal 9",
        10: "Sucursal 10",
        11: "Sucursal 11"
    }
    
    # Categorizar automáticamente
    df['categoria'] = df['Denominación Receptor'].apply(categorizar_venta)
    
    # Guardar en base de datos
    for _, row in df.iterrows():
        sucursal_nombre = mapeo_sucursales.get(row['Punto de Venta'], f"Sucursal {row['Punto de Venta']}")
        
        LibroIva.objects.create(
            fecha=row['Fecha'],
            tipo_comprobante=row['Tipo'],
            sucursal=sucursal_nombre,
            numero_comprobante=row['Número Desde'],
            cod_autorizacion=row['Cód. Autorización'],
            tipo_doc_receptor=row['Tipo Doc. Receptor'],
            cuit=row['Nro. Doc. Receptor'],
            cliente=row['Denominación Receptor'],
            tipo_cambio=row['Tipo Cambio'],
            moneda=row['Moneda'],
            neto=row['Imp. Neto Gravado'],
            no_gravado=row['Imp. Neto No Gravado'],
            exentas=row['Imp. Op. Exentas'],
            iva=row['IVA'],
            total=row['Imp. Total'],
            categoria=row['categoria'],
            mes=mes,
            año=año
        )
    
    return len(df)

def categorizar_venta(denominacion):
    '''Categoriza automáticamente una venta'''
    
    patrones_repuestos = ['REPUESTO', 'FILTRO', 'ACEITE', 'BATERIA', 'FRENO']
    patrones_maquinarias = ['MAQUINA', 'TRACTOR', 'EXCAVADORA', 'EQUIPO']
    patrones_servicios = ['SERVICIO', 'MANTENIMIENTO', 'REPARACION']
    
    denominacion_upper = denominacion.upper()
    
    if any(patron in denominacion_upper for patron in patrones_repuestos):
        return 'RE'
    elif any(patron in denominacion_upper for patron in patrones_maquinarias):
        return 'MN'
    elif any(patron in denominacion_upper for patron in patrones_servicios):
        return 'SE'
    else:
        return 'OT'
    """)
    
    print(f"\n📊 FUNCIONALIDADES DEL DASHBOARD:")
    print(f"""
# En views.py
def dashboard_ventas_libro_iva(request):
    '''Dashboard de ventas del Libro IVA'''
    
    # Obtener datos del mes actual
    mes_actual = datetime.now().month
    año_actual = datetime.now().year
    
    # Ventas por categoría
    ventas_repuestos = LibroIva.objects.filter(
        categoria='RE', 
        mes=mes_actual, 
        año=año_actual
    ).aggregate(total=Sum('total'))
    
    ventas_maquinarias = LibroIva.objects.filter(
        categoria='MN', 
        mes=mes_actual, 
        año=año_actual
    ).aggregate(total=Sum('total'))
    
    ventas_servicios = LibroIva.objects.filter(
        categoria='SE', 
        mes=mes_actual, 
        año=año_actual
    ).aggregate(total=Sum('total'))
    
    # Ventas por sucursal
    ventas_por_sucursal = LibroIva.objects.filter(
        mes=mes_actual, 
        año=año_actual
    ).values('sucursal').annotate(
        total=Sum('total'),
        cantidad=Count('id')
    ).order_by('-total')
    
    # Top clientes
    top_clientes = LibroIva.objects.filter(
        mes=mes_actual, 
        año=año_actual
    ).values('cliente').annotate(
        total=Sum('total'),
        cantidad=Count('id')
    ).order_by('-total')[:10]
    
    context = {
        'ventas_repuestos': ventas_repuestos['total'] or 0,
        'ventas_maquinarias': ventas_maquinarias['total'] or 0,
        'ventas_servicios': ventas_servicios['total'] or 0,
        'ventas_por_sucursal': ventas_por_sucursal,
        'top_clientes': top_clientes,
    }
    
    return render(request, 'dashboard_ventas_libro_iva.html', context)
    """)

if __name__ == "__main__":
    # Analizar el archivo con la estructura real
    df = analizar_libro_iva_final("LIBRO IVA 07-2025.xlsx")
    
    # Sugerir implementación final
    sugerir_implementacion_final(df) 