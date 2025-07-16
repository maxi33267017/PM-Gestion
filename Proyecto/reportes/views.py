from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
import json

# Importar modelos necesarios
from gestionDeTaller.models import Servicio, PreOrden
from recursosHumanos.models import RegistroHorasTecnico, Usuario, Sucursal
from crm.models import Campania
from centroSoluciones.models import AlertaEquipo, LeadJohnDeere
from clientes.models import Cliente

@login_required
def dashboard_reportes(request):
    """Dashboard principal de reportes"""
    context = {
        'titulo': 'Dashboard de Reportes',
        'secciones': [
            {
                'titulo': 'Facturación',
                'icono': 'bi-cash-stack',
                'url': 'reportes:facturacion',
                'descripcion': 'Reportes de facturación por técnico, sucursal y períodos'
            },
            {
                'titulo': 'Registro de Horas',
                'icono': 'bi-clock-history',
                'url': 'reportes:horas',
                'descripcion': 'Reportes de horas trabajadas, productividad y eficiencia'
            },
            {
                'titulo': 'Servicios',
                'icono': 'bi-tools',
                'url': 'reportes:servicios',
                'descripcion': 'Reportes de servicios, preórdenes y tiempos promedio'
            },
            {
                'titulo': 'Embudos',
                'icono': 'bi-funnel',
                'url': 'reportes:embudos',
                'descripcion': 'Reportes de embudos de ventas y estadísticas'
            },
            {
                'titulo': 'CSC',
                'icono': 'bi-headset',
                'url': 'reportes:csc',
                'descripcion': 'Reportes del Centro de Soluciones al Cliente'
            },
            {
                'titulo': 'Encuestas',
                'icono': 'bi-clipboard-data',
                'url': 'reportes:encuestas',
                'descripcion': 'Reportes de encuestas de satisfacción'
            }
        ]
    }
    return render(request, 'reportes/dashboard.html', context)

# ===== REPORTES DE FACTURACIÓN =====

@login_required
def reportes_facturacion(request):
    """Dashboard de reportes de facturación"""
    return render(request, 'reportes/facturacion/dashboard.html')

@login_required
def facturacion_por_tecnico(request):
    """Reporte de facturación por técnico"""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    # Lógica para obtener datos de facturación por técnico
    context = {
        'titulo': 'Facturación por Técnico',
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    }
    return render(request, 'reportes/facturacion/por_tecnico.html', context)

@login_required
def facturacion_por_sucursal(request):
    """Reporte de facturación por sucursal"""
    return render(request, 'reportes/facturacion/por_sucursal.html')

@login_required
def facturacion_mensual(request):
    """Reporte de facturación mensual"""
    return render(request, 'reportes/facturacion/mensual.html')

@login_required
def facturacion_trimestral(request):
    """Reporte de facturación trimestral"""
    return render(request, 'reportes/facturacion/trimestral.html')

@login_required
def facturacion_semestral(request):
    """Reporte de facturación semestral"""
    return render(request, 'reportes/facturacion/semestral.html')

@login_required
def facturacion_anual(request):
    """Reporte de facturación anual"""
    return render(request, 'reportes/facturacion/anual.html')

# ===== REPORTES DE HORAS =====

@login_required
def reportes_horas(request):
    """Dashboard de reportes de horas"""
    return render(request, 'reportes/horas/dashboard.html')

@login_required
def horas_por_sucursal(request):
    """Reporte de horas por sucursal"""
    return render(request, 'reportes/horas/por_sucursal.html')

@login_required
def horas_por_tecnico(request):
    """Reporte de horas por técnico"""
    return render(request, 'reportes/horas/por_tecnico.html')

@login_required
def productividad_tecnicos(request):
    """Reporte de productividad de técnicos"""
    return render(request, 'reportes/horas/productividad.html')

@login_required
def eficiencia_tecnicos(request):
    """Reporte de eficiencia de técnicos"""
    return render(request, 'reportes/horas/eficiencia.html')

@login_required
def desempeno_tecnicos(request):
    """Reporte de desempeño de técnicos"""
    return render(request, 'reportes/horas/desempeno.html')

# ===== REPORTES DE SERVICIOS =====

@login_required
def reportes_servicios(request):
    """Dashboard de reportes de servicios"""
    return render(request, 'reportes/servicios/dashboard.html')

@login_required
def preordenes_estadisticas(request):
    """Estadísticas de preórdenes"""
    return render(request, 'reportes/servicios/preordenes.html')

@login_required
def servicios_programados(request):
    """Reporte de servicios programados"""
    return render(request, 'reportes/servicios/programados.html')

@login_required
def servicios_en_proceso(request):
    """Reporte de servicios en proceso"""
    return render(request, 'reportes/servicios/en_proceso.html')

@login_required
def servicios_completados(request):
    """Reporte de servicios completados"""
    return render(request, 'reportes/servicios/completados.html')

@login_required
def tiempo_promedio_servicios(request):
    """Reporte de tiempo promedio de servicios"""
    return render(request, 'reportes/servicios/tiempo_promedio.html')

@login_required
def servicios_por_sucursal(request):
    """Reporte de servicios por sucursal"""
    return render(request, 'reportes/servicios/por_sucursal.html')

@login_required
def servicios_por_tecnico(request):
    """Reporte de servicios por técnico"""
    return render(request, 'reportes/servicios/por_tecnico.html')

# ===== REPORTES DE EMBUDOS =====

@login_required
def reportes_embudos(request):
    """Dashboard de reportes de embudos"""
    return render(request, 'reportes/embudos/dashboard.html')

@login_required
def embudos_cantidad(request):
    """Reporte de cantidad de embudos"""
    return render(request, 'reportes/embudos/cantidad.html')

@login_required
def embudos_abiertos_cerrados(request):
    """Reporte de embudos abiertos y cerrados"""
    return render(request, 'reportes/embudos/abiertos_cerrados.html')

@login_required
def embudos_por_tipo(request):
    """Reporte de embudos por tipo"""
    return render(request, 'reportes/embudos/por_tipo.html')

@login_required
def embudos_por_sucursal(request):
    """Reporte de embudos por sucursal"""
    return render(request, 'reportes/embudos/por_sucursal.html')

@login_required
def embudos_estadisticas(request):
    """Estadísticas generales de embudos"""
    return render(request, 'reportes/embudos/estadisticas.html')

# ===== REPORTES DE CSC =====

@login_required
def reportes_csc(request):
    """Dashboard de reportes de CSC"""
    return render(request, 'reportes/csc/dashboard.html')

@login_required
def csc_leads(request):
    """Reporte de leads del CSC"""
    return render(request, 'reportes/csc/leads.html')

@login_required
def csc_alertas(request):
    """Reporte de alertas del CSC"""
    return render(request, 'reportes/csc/alertas.html')

@login_required
def csc_asignadas(request):
    """Reporte de alertas asignadas del CSC"""
    return render(request, 'reportes/csc/asignadas.html')

@login_required
def csc_procesadas(request):
    """Reporte de alertas procesadas del CSC"""
    return render(request, 'reportes/csc/procesadas.html')

@login_required
def csc_por_tecnico(request):
    """Reporte de CSC por técnico"""
    return render(request, 'reportes/csc/por_tecnico.html')

@login_required
def csc_por_sucursal(request):
    """Reporte de CSC por sucursal"""
    return render(request, 'reportes/csc/por_sucursal.html')

# ===== REPORTES DE ENCUESTAS =====

@login_required
def reportes_encuestas(request):
    """Dashboard de reportes de encuestas"""
    return render(request, 'reportes/encuestas/dashboard.html')

@login_required
def encuestas_enviadas(request):
    """Reporte de encuestas enviadas"""
    return render(request, 'reportes/encuestas/enviadas.html')

@login_required
def encuestas_respuestas(request):
    """Reporte de encuestas con respuesta"""
    return render(request, 'reportes/encuestas/respuestas.html')

@login_required
def encuestas_porcentajes(request):
    """Reporte de porcentajes de encuestas"""
    return render(request, 'reportes/encuestas/porcentajes.html')

# ===== EXPORTACIÓN DE REPORTES =====

@login_required
def exportar_reporte(request, tipo, formato):
    """Exportar reporte en diferentes formatos"""
    # Lógica para exportar reportes
    return HttpResponse(f"Exportando reporte {tipo} en formato {formato}")

# ===== APIs PARA GRÁFICOS =====

@login_required
def api_facturacion_mensual(request):
    """API para obtener datos de facturación mensual"""
    # Obtener datos de facturación del último año
    datos = []
    for i in range(12):
        fecha = timezone.now() - timedelta(days=30*i)
        # Aquí iría la lógica para obtener datos reales
        datos.append({
            'mes': fecha.strftime('%B'),
            'facturacion': 0  # Placeholder
        })
    
    return JsonResponse({'datos': datos})

@login_required
def api_productividad_tecnicos(request):
    """API para obtener datos de productividad de técnicos"""
    # Obtener datos de productividad
    tecnicos = Usuario.objects.filter(rol='TECNICO')
    datos = []
    
    for tecnico in tecnicos:
        # Aquí iría la lógica para calcular productividad real
        datos.append({
            'tecnico': tecnico.nombre,
            'productividad': 0  # Placeholder
        })
    
    return JsonResponse({'datos': datos})
