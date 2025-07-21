#!/usr/bin/env python
import os
import sys
import django
from datetime import timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PatagoniaMaquinarias.settings_render')
django.setup()

from django.utils import timezone
from gestionDeTaller.models import PreOrden
from django.db.models import Q, Count

def diagnosticar_metricas_conversion():
    """Diagnóstico de las métricas de conversión"""
    
    print("=== DIAGNÓSTICO DE MÉTRICAS DE CONVERSIÓN ===\n")
    
    # Fecha límite de 30 días
    fecha_limite = timezone.now().date() - timedelta(days=30)
    print(f"Fecha límite (30 días atrás): {fecha_limite}")
    print(f"Fecha actual: {timezone.now().date()}\n")
    
    # 1. Todas las preórdenes de los últimos 30 días
    preordenes_30_dias = PreOrden.objects.filter(
        fecha_creacion__gte=fecha_limite,
        activo=True
    )
    
    print("1. PREÓRDENES DE LOS ÚLTIMOS 30 DÍAS:")
    print(f"   Total: {preordenes_30_dias.count()}")
    
    # 2. Preórdenes con servicio
    con_servicio = preordenes_30_dias.filter(servicio__isnull=False)
    print(f"   Con servicio: {con_servicio.count()}")
    
    # 3. Preórdenes sin servicio
    sin_servicio = preordenes_30_dias.filter(servicio__isnull=True)
    print(f"   Sin servicio: {sin_servicio.count()}")
    
    # 4. Verificar que la suma coincida
    total_calculado = con_servicio.count() + sin_servicio.count()
    print(f"   Total calculado: {total_calculado}")
    print(f"   ¿Coincide?: {'SÍ' if total_calculado == preordenes_30_dias.count() else 'NO'}\n")
    
    # 5. Detalle de preórdenes sin servicio
    print("2. DETALLE DE PREÓRDENES SIN SERVICIO (últimos 30 días):")
    for preorden in sin_servicio.order_by('-fecha_creacion'):
        print(f"   - Preorden #{preorden.numero}: {preorden.cliente.razon_social} ({preorden.fecha_creacion.date()})")
    
    print(f"\n   Total sin servicio: {sin_servicio.count()}")
    
    # 6. Comparar con las preórdenes que aparecen en el reporte principal
    print("\n3. COMPARACIÓN CON REPORTE PRINCIPAL:")
    
    # Preórdenes sin servicio (todas, sin filtro de 30 días)
    todas_sin_servicio = PreOrden.objects.filter(
        activo=True,
        servicio__isnull=True
    )
    
    print(f"   Total preórdenes sin servicio (todas): {todas_sin_servicio.count()}")
    
    # Categorizar por tiempo
    fecha_actual = timezone.now().date()
    recientes = 0
    en_riesgo = 0
    perdidas = 0
    
    for preorden in todas_sin_servicio:
        dias_desde_creacion = (fecha_actual - preorden.fecha_creacion.date()).days
        
        if dias_desde_creacion <= 7:
            recientes += 1
        elif dias_desde_creacion <= 15:
            en_riesgo += 1
        else:
            perdidas += 1
    
    print(f"   Recientes (0-7 días): {recientes}")
    print(f"   En riesgo (8-15 días): {en_riesgo}")
    print(f"   Perdidas (15+ días): {perdidas}")
    print(f"   Total categorizadas: {recientes + en_riesgo + perdidas}")
    
    # 7. Verificar preórdenes específicas que aparecen en el reporte
    print("\n4. VERIFICACIÓN DE PREÓRDENES ESPECÍFICAS:")
    preordenes_especificas = [37, 30, 29, 28, 25, 17]  # Las que aparecen en el reporte
    
    for numero in preordenes_especificas:
        try:
            preorden = PreOrden.objects.get(numero=numero)
            tiene_servicio = preorden.servicio is not None
            dias_desde_creacion = (fecha_actual - preorden.fecha_creacion.date()).days
            print(f"   Preorden #{numero}: {'SIN servicio' if not tiene_servicio else 'CON servicio'} - {dias_desde_creacion} días")
        except PreOrden.DoesNotExist:
            print(f"   Preorden #{numero}: NO EXISTE")
    
    print("\n=== FIN DEL DIAGNÓSTICO ===")

if __name__ == "__main__":
    diagnosticar_metricas_conversion() 