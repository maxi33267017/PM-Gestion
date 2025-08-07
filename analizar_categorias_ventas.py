#!/usr/bin/env python3
"""
Script específico para analizar categorías de ventas del Libro IVA
Extrae información detallada sobre Repuestos (RE), Maquinarias (MN) y Servicios (SE)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re

def analizar_categorias_ventas(archivo_excel):
    """Analiza las categorías de ventas del Libro IVA"""
    
    print("=" * 80)
    print("ANÁLISIS DETALLADO DE CATEGORÍAS DE VENTAS")
    print("=" * 80)
    
    try:
        # Leer el archivo Excel
        df = pd.read_excel(archivo_excel)
        
        print(f"\n📊 RESUMEN GENERAL:")
        print(f"   • Total de registros: {len(df)}")
        print(f"   • Período: Julio 2025")
        print(f"   • Moneda principal: USD")
        
        # Analizar por tipo de comprobante
        print(f"\n📄 ANÁLISIS POR TIPO DE COMPROBANTE:")
        tipos_comprobante = df['Tipo'].value_counts()
        for tipo, cantidad in tipos_comprobante.items():
            print(f"   • {tipo}: {cantidad} registros")
        
        # Analizar clientes más frecuentes
        print(f"\n👥 TOP 10 CLIENTES POR VOLUMEN:")
        clientes_volumen = df.groupby('Denominación Receptor')['Imp. Total'].sum().sort_values(ascending=False)
        for i, (cliente, monto) in enumerate(clientes_volumen.head(10).items(), 1):
            print(f"   {i:2d}. {cliente[:50]:<50} ${monto:>12,.2f}")
        
        # Categorizar por patrones en nombres de clientes
        print(f"\n🏷️ CATEGORIZACIÓN POR PATRONES:")
        
        # Buscar repuestos (RE) - patrones comunes
        patrones_repuestos = [
            'REPUESTO', 'REP', 'FILTRO', 'ACEITE', 'LUBRICANTE', 'BATERIA', 'BATERÍA',
            'NEUMATICO', 'NEUMÁTICO', 'FRENO', 'EMBRAGUE', 'MOTOR', 'TRANSMISION',
            'TRANSMISIÓN', 'HIDRAULICO', 'HIDRÁULICO', 'ELECTRICO', 'ELÉCTRICO'
        ]
        
        repuestos = df[df['Denominación Receptor'].str.contains('|'.join(patrones_repuestos), case=False, na=False)]
        print(f"\n🔧 REPUESTOS (RE):")
        print(f"   • Registros identificados: {len(repuestos)}")
        if len(repuestos) > 0:
            print(f"   • Monto total: ${repuestos['Imp. Total'].sum():,.2f}")
            print(f"   • Promedio por factura: ${repuestos['Imp. Total'].mean():,.2f}")
            print(f"   • Clientes únicos: {repuestos['Denominación Receptor'].nunique()}")
            
            print(f"\n   📋 TOP 5 CLIENTES DE REPUESTOS:")
            top_repuestos = repuestos.groupby('Denominación Receptor')['Imp. Total'].sum().sort_values(ascending=False).head(5)
            for i, (cliente, monto) in enumerate(top_repuestos.items(), 1):
                print(f"      {i}. {cliente[:40]:<40} ${monto:>10,.2f}")
        
        # Buscar maquinarias (MN) - patrones comunes
        patrones_maquinarias = [
            'MAQUINA', 'MÁQUINA', 'TRACTOR', 'EXCAVADORA', 'RETROEXCAVADORA',
            'CARGADOR', 'MARTILLO', 'COMPRESOR', 'GENERADOR', 'SOLDADORA',
            'MOTOSIERRA', 'CORTADORA', 'PULIDORA', 'TALADRO', 'SIERRA',
            'EQUIPO', 'HERRAMIENTA', 'MOTOR', 'BOMBA', 'COMPRESOR'
        ]
        
        maquinarias = df[df['Denominación Receptor'].str.contains('|'.join(patrones_maquinarias), case=False, na=False)]
        print(f"\n🚜 MAQUINARIAS (MN):")
        print(f"   • Registros identificados: {len(maquinarias)}")
        if len(maquinarias) > 0:
            print(f"   • Monto total: ${maquinarias['Imp. Total'].sum():,.2f}")
            print(f"   • Promedio por factura: ${maquinarias['Imp. Total'].mean():,.2f}")
            print(f"   • Clientes únicos: {maquinarias['Denominación Receptor'].nunique()}")
            
            print(f"\n   📋 TOP 5 CLIENTES DE MAQUINARIAS:")
            top_maquinarias = maquinarias.groupby('Denominación Receptor')['Imp. Total'].sum().sort_values(ascending=False).head(5)
            for i, (cliente, monto) in enumerate(top_maquinarias.items(), 1):
                print(f"      {i}. {cliente[:40]:<40} ${monto:>10,.2f}")
        
        # Buscar servicios (SE) - patrones comunes
        patrones_servicios = [
            'SERVICIO', 'MANTENIMIENTO', 'REPARACION', 'REPARACIÓN', 'INSTALACION',
            'INSTALACIÓN', 'MONTAJE', 'ARMADO', 'DESARMADO', 'LIMPIEZA',
            'DIAGNOSTICO', 'DIAGNÓSTICO', 'REVISION', 'REVISIÓN', 'CALIBRACION',
            'CALIBRACIÓN', 'AJUSTE', 'CONFIGURACION', 'CONFIGURACIÓN', 'PROGRAMACION',
            'PROGRAMACIÓN', 'CAPACITACION', 'CAPACITACIÓN', 'ASESORAMIENTO'
        ]
        
        servicios = df[df['Denominación Receptor'].str.contains('|'.join(patrones_servicios), case=False, na=False)]
        print(f"\n🔧 SERVICIOS (SE):")
        print(f"   • Registros identificados: {len(servicios)}")
        if len(servicios) > 0:
            print(f"   • Monto total: ${servicios['Imp. Total'].sum():,.2f}")
            print(f"   • Promedio por factura: ${servicios['Imp. Total'].mean():,.2f}")
            print(f"   • Clientes únicos: {servicios['Denominación Receptor'].nunique()}")
            
            print(f"\n   📋 TOP 5 CLIENTES DE SERVICIOS:")
            top_servicios = servicios.groupby('Denominación Receptor')['Imp. Total'].sum().sort_values(ascending=False).head(5)
            for i, (cliente, monto) in enumerate(top_servicios.items(), 1):
                print(f"      {i}. {cliente[:40]:<40} ${monto:>10,.2f}")
        
        # Análisis de rentabilidad por categoría
        print(f"\n💰 ANÁLISIS DE RENTABILIDAD POR CATEGORÍA:")
        
        total_ventas = df['Imp. Total'].sum()
        
        if len(repuestos) > 0:
            porcentaje_repuestos = (repuestos['Imp. Total'].sum() / total_ventas) * 100
            print(f"   • Repuestos: ${repuestos['Imp. Total'].sum():,.2f} ({porcentaje_repuestos:.1f}%)")
        
        if len(maquinarias) > 0:
            porcentaje_maquinarias = (maquinarias['Imp. Total'].sum() / total_ventas) * 100
            print(f"   • Maquinarias: ${maquinarias['Imp. Total'].sum():,.2f} ({porcentaje_maquinarias:.1f}%)")
        
        if len(servicios) > 0:
            porcentaje_servicios = (servicios['Imp. Total'].sum() / total_ventas) * 100
            print(f"   • Servicios: ${servicios['Imp. Total'].sum():,.2f} ({porcentaje_servicios:.1f}%)")
        
        # Análisis temporal
        print(f"\n📅 ANÁLISIS TEMPORAL:")
        df['Fecha'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y')
        ventas_por_dia = df.groupby(df['Fecha'].dt.date)['Imp. Total'].sum()
        
        print(f"   • Días con ventas: {len(ventas_por_dia)}")
        print(f"   • Promedio diario: ${ventas_por_dia.mean():,.2f}")
        print(f"   • Día de mayor venta: {ventas_por_dia.idxmax()} (${ventas_por_dia.max():,.2f})")
        print(f"   • Día de menor venta: {ventas_por_dia.idxmin()} (${ventas_por_dia.min():,.2f})")
        
        return {
            'repuestos': repuestos,
            'maquinarias': maquinarias,
            'servicios': servicios,
            'total': df
        }
        
    except Exception as e:
        print(f"❌ Error al analizar categorías: {e}")
        return None

def sugerir_implementacion(datos):
    """Sugiere cómo implementar la importación en la aplicación"""
    
    print(f"\n" + "=" * 80)
    print("SUGERENCIAS DE IMPLEMENTACIÓN")
    print("=" * 80)
    
    if datos is None:
        print("❌ No se pueden generar sugerencias sin datos válidos")
        return
    
    print(f"\n🎯 MODELO DE DATOS SUGERIDO:")
    print(f"""
class LibroIva(models.Model):
    fecha = models.DateField()
    tipo_comprobante = models.CharField(max_length=50)
    punto_venta = models.IntegerField()
    numero_desde = models.IntegerField()
    cod_autorizacion = models.CharField(max_length=50)
    tipo_doc_receptor = models.CharField(max_length=20)
    nro_doc_receptor = models.CharField(max_length=20)
    denominacion_receptor = models.CharField(max_length=200)
    tipo_cambio = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=10)
    imp_neto_gravado = models.DecimalField(max_digits=15, decimal_places=2)
    imp_neto_no_gravado = models.DecimalField(max_digits=15, decimal_places=2)
    imp_op_exentas = models.DecimalField(max_digits=15, decimal_places=2)
    iva = models.DecimalField(max_digits=15, decimal_places=2)
    imp_total = models.DecimalField(max_digits=15, decimal_places=2)
    categoria = models.CharField(max_length=10, choices=[
        ('RE', 'Repuestos'),
        ('MN', 'Maquinarias'),
        ('SE', 'Servicios'),
        ('OT', 'Otros')
    ])
    mes = models.IntegerField()
    año = models.IntegerField()
    
    class Meta:
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['categoria']),
            models.Index(fields=['mes', 'año']),
        ]
    """)
    
    print(f"\n🔧 FUNCIONES DE IMPORTACIÓN:")
    print(f"""
def importar_libro_iva(archivo_excel, mes, año):
    '''Importa datos del Libro IVA desde Excel'''
    
    # Leer archivo Excel
    df = pd.read_excel(archivo_excel)
    
    # Categorizar automáticamente
    df['categoria'] = df['Denominación Receptor'].apply(categorizar_venta)
    
    # Guardar en base de datos
    for _, row in df.iterrows():
        LibroIva.objects.create(
            fecha=row['Fecha'],
            tipo_comprobante=row['Tipo'],
            punto_venta=row['Punto de Venta'],
            numero_desde=row['Número Desde'],
            cod_autorizacion=row['Cód. Autorización'],
            tipo_doc_receptor=row['Tipo Doc. Receptor'],
            nro_doc_receptor=row['Nro. Doc. Receptor'],
            denominacion_receptor=row['Denominación Receptor'],
            tipo_cambio=row['Tipo Cambio'],
            moneda=row['Moneda'],
            imp_neto_gravado=row['Imp. Neto Gravado'],
            imp_neto_no_gravado=row['Imp. Neto No Gravado'],
            imp_op_exentas=row['Imp. Op. Exentas'],
            iva=row['IVA'],
            imp_total=row['Imp. Total'],
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
def dashboard_ventas(request):
    '''Dashboard de ventas por categoría'''
    
    # Obtener datos del mes actual
    mes_actual = datetime.now().month
    año_actual = datetime.now().year
    
    # Ventas por categoría
    ventas_repuestos = LibroIva.objects.filter(
        categoria='RE', 
        mes=mes_actual, 
        año=año_actual
    ).aggregate(total=Sum('imp_total'))
    
    ventas_maquinarias = LibroIva.objects.filter(
        categoria='MN', 
        mes=mes_actual, 
        año=año_actual
    ).aggregate(total=Sum('imp_total'))
    
    ventas_servicios = LibroIva.objects.filter(
        categoria='SE', 
        mes=mes_actual, 
        año=año_actual
    ).aggregate(total=Sum('imp_total'))
    
    # Top clientes por categoría
    top_clientes_repuestos = LibroIva.objects.filter(
        categoria='RE', 
        mes=mes_actual, 
        año=año_actual
    ).values('denominacion_receptor').annotate(
        total=Sum('imp_total')
    ).order_by('-total')[:5]
    
    context = {
        'ventas_repuestos': ventas_repuestos['total'] or 0,
        'ventas_maquinarias': ventas_maquinarias['total'] or 0,
        'ventas_servicios': ventas_servicios['total'] or 0,
        'top_clientes_repuestos': top_clientes_repuestos,
        # ... más datos
    }
    
    return render(request, 'dashboard_ventas.html', context)
    """)

if __name__ == "__main__":
    # Analizar categorías
    datos = analizar_categorias_ventas("LIBRO IVA 07-2025.xlsx")
    
    # Sugerir implementación
    sugerir_implementacion(datos) 