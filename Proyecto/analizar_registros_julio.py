#!/usr/bin/env python
import os
import sys
import django
from datetime import date, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto.settings')
django.setup()

from recursosHumanos.models import RegistroHorasTecnico, Usuario, ActividadTrabajo
from gestionDeTaller.views import calcular_horas_contratadas

def analizar_registros_julio_2025():
    """Analiza los registros de horas de julio 2025 para entender las métricas"""
    
    # Fechas de julio 2025
    inicio_mes = date(2025, 7, 1)
    fin_mes = date(2025, 7, 31)
    
    print("=" * 80)
    print("ANÁLISIS DE REGISTROS DE HORAS - JULIO 2025")
    print("=" * 80)
    
    # Obtener todos los técnicos
    tecnicos = Usuario.objects.filter(rol='TECNICO')
    print(f"Total de técnicos: {tecnicos.count()}")
    
    # Calcular horas contratadas
    horas_contratadas_mes = calcular_horas_contratadas(inicio_mes, fin_mes)
    print(f"Horas contratadas por técnico en julio: {horas_contratadas_mes}")
    print(f"Total horas contratadas (5 técnicos): {horas_contratadas_mes * 5}")
    
    print("\n" + "=" * 80)
    print("ANÁLISIS POR TÉCNICO")
    print("=" * 80)
    
    total_horas_generan_ingreso = 0
    total_horas_facturadas = 0
    total_tecnicos_con_registros = 0
    
    for tecnico in tecnicos:
        print(f"\n--- {tecnico.get_nombre_completo()} ---")
        
        # Obtener registros del mes
        registros = RegistroHorasTecnico.objects.filter(
            tecnico=tecnico,
            fecha__range=[inicio_mes, fin_mes]
        ).order_by('fecha', 'hora_inicio')
        
        if not registros.exists():
            print("❌ No tiene registros en julio 2025")
            continue
        
        total_tecnicos_con_registros += 1
        
        # Contadores por tipo de actividad
        horas_por_actividad = {}
        horas_disponibles = 0
        horas_generan_ingreso = 0
        horas_facturadas = 0
        total_horas_registradas = 0
        
        print(f"📊 Registros encontrados: {registros.count()}")
        
        for registro in registros:
            # Calcular duración
            inicio = registro.hora_inicio
            fin = registro.hora_fin
            duracion = (fin.hour - inicio.hour) + (fin.minute - inicio.minute) / 60
            if duracion < 0:  # Si pasa de un día a otro
                duracion += 24
            
            total_horas_registradas += duracion
            
            # Clasificar por tipo de actividad
            actividad = registro.tipo_hora
            if actividad.nombre not in horas_por_actividad:
                horas_por_actividad[actividad.nombre] = 0
            horas_por_actividad[actividad.nombre] += duracion
            
            # Clasificar por disponibilidad e ingreso
            if actividad.disponibilidad == 'DISPONIBLE':
                horas_disponibles += duracion
                if actividad.genera_ingreso == 'INGRESO':
                    horas_generan_ingreso += duracion
                    if actividad.categoria_facturacion == 'FACTURABLE':
                        horas_facturadas += duracion
        
        # Mostrar resumen del técnico
        print(f"⏰ Total horas registradas: {total_horas_registradas:.2f}")
        print(f"✅ Horas disponibles: {horas_disponibles:.2f}")
        print(f"💰 Horas que generan ingreso: {horas_generan_ingreso:.2f}")
        print(f"💵 Horas facturadas: {horas_facturadas:.2f}")
        
        # Calcular métricas
        productividad = (horas_generan_ingreso / horas_contratadas_mes * 100) if horas_contratadas_mes > 0 else 0
        eficiencia = (horas_facturadas / horas_generan_ingreso * 100) if horas_generan_ingreso > 0 else 0
        desempeno = (horas_facturadas / horas_contratadas_mes * 100) if horas_contratadas_mes > 0 else 0
        
        print(f"📈 Productividad: {productividad:.1f}%")
        print(f"🎯 Eficiencia: {eficiencia:.1f}%")
        print(f"🏆 Desempeño: {desempeno:.1f}%")
        
        # Mostrar desglose por actividad
        print("\n📋 Desglose por actividad:")
        for actividad, horas in sorted(horas_por_actividad.items(), key=lambda x: x[1], reverse=True):
            act_obj = ActividadTrabajo.objects.get(nombre=actividad)
            print(f"  • {actividad}: {horas:.2f}h ({act_obj.disponibilidad} - {act_obj.genera_ingreso})")
        
        total_horas_generan_ingreso += horas_generan_ingreso
        total_horas_facturadas += horas_facturadas
    
    print("\n" + "=" * 80)
    print("RESUMEN GENERAL")
    print("=" * 80)
    
    if total_tecnicos_con_registros > 0:
        promedio_horas_generan_ingreso = total_horas_generan_ingreso / total_tecnicos_con_registros
        promedio_horas_facturadas = total_horas_facturadas / total_tecnicos_con_registros
        
        productividad_promedio = (promedio_horas_generan_ingreso / horas_contratadas_mes * 100)
        eficiencia_promedio = (promedio_horas_facturadas / promedio_horas_generan_ingreso * 100) if promedio_horas_generan_ingreso > 0 else 0
        desempeno_promedio = (promedio_horas_facturadas / horas_contratadas_mes * 100)
        
        print(f"👥 Técnicos con registros: {total_tecnicos_con_registros}/5")
        print(f"💰 Total horas que generan ingreso: {total_horas_generan_ingreso:.2f}")
        print(f"💵 Total horas facturadas: {total_horas_facturadas:.2f}")
        print(f"📊 Promedio horas que generan ingreso: {promedio_horas_generan_ingreso:.2f}")
        print(f"📈 Productividad promedio: {productividad_promedio:.1f}%")
        print(f"🎯 Eficiencia promedio: {eficiencia_promedio:.1f}%")
        print(f"🏆 Desempeño promedio: {desempeno_promedio:.1f}%")
        
        # Verificar si coincide con los números que mencionaste
        if abs(productividad_promedio - 32) < 1 and abs(eficiencia_promedio - 100) < 1 and abs(desempeno_promedio - 32) < 1:
            print("\n✅ Los números coinciden con tu reporte!")
        else:
            print(f"\n⚠️ Los números no coinciden exactamente con tu reporte:")
            print(f"   Reportado: 32% productividad, 100% eficiencia, 32% desempeño")
            print(f"   Calculado: {productividad_promedio:.1f}% productividad, {eficiencia_promedio:.1f}% eficiencia, {desempeno_promedio:.1f}% desempeño")

if __name__ == "__main__":
    analizar_registros_julio_2025() 