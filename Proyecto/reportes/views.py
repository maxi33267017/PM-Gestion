from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
import json
import pandas as pd
from decimal import Decimal

# Importar modelos necesarios
from gestionDeTaller.models import Servicio, PreOrden
from recursosHumanos.models import RegistroHorasTecnico, Usuario, Sucursal
from crm.models import Campania
from centroSoluciones.models import AlertaEquipo, LeadJohnDeere
from clientes.models import Cliente

@login_required
def dashboard_reportes(request):
    """Dashboard principal de reportes"""
    
    # Calcular estadísticas
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    # Fecha actual y mes actual
    ahora = timezone.now()
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Servicios activos (en proceso, programados, espera repuestos)
    servicios_count = Servicio.objects.filter(
        estado__in=['EN_PROCESO', 'PROGRAMADO', 'ESPERA_REPUESTOS']
    ).count()
    
    # Técnicos activos
    tecnicos_count = Usuario.objects.filter(
        rol='TECNICO',
        is_active=True
    ).count()
    
    # Clientes activos
    clientes_count = Cliente.objects.filter(activo=True).count()
    
    # Facturación mensual
    facturacion_mensual = Servicio.objects.filter(
        estado='COMPLETADO',
        fecha_servicio__gte=inicio_mes
    ).aggregate(
        total=Sum('valor_mano_obra')
    )['total'] or 0
    
    # Agregar gastos y repuestos a la facturación
    servicios_mes = Servicio.objects.filter(
        estado='COMPLETADO',
        fecha_servicio__gte=inicio_mes
    )
    
    total_gastos = servicios_mes.aggregate(
        total=Sum('gastos__monto')
    )['total'] or 0
    
    total_repuestos = servicios_mes.aggregate(
        total=Sum(F('repuestos__precio_unitario') * F('repuestos__cantidad'))
    )['total'] or 0
    
    facturacion_mensual += total_gastos + total_repuestos
    
    context = {
        'titulo': 'Dashboard de Reportes',
        'servicios_count': servicios_count,
        'tecnicos_count': tecnicos_count,
        'clientes_count': clientes_count,
        'facturacion_mensual': f"${facturacion_mensual:,.0f}",
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

@login_required
def servicios_sin_ingresos(request):
    servicios = Servicio.objects.filter(estado='COMPLETADO').select_related('preorden__cliente', 'preorden__equipo').prefetch_related('gastos', 'repuestos').order_by('fecha_servicio')
    servicios_sin_ingresos = []
    for servicio in servicios:
        valor_mano_obra = servicio.valor_mano_obra or Decimal('0.00')
        total_gastos = servicio.gastos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        total_repuestos = servicio.repuestos.aggregate(total=Sum(F('precio_unitario') * F('cantidad')))['total'] or Decimal('0.00')
        valor_total = valor_mano_obra + total_gastos + total_repuestos
        if valor_total == Decimal('0.00'):
            servicios_sin_ingresos.append({
                'servicio': servicio,
                'valor_mano_obra': valor_mano_obra,
                'total_gastos': total_gastos,
                'total_repuestos': total_repuestos,
                'valor_total': valor_total
            })
    # Descarga Excel
    if request.GET.get('excel') == '1':
        datos = []
        for item in servicios_sin_ingresos:
            s = item['servicio']
            datos.append({
                'ID': s.id,
                'Fecha': s.fecha_servicio,
                'Cliente': s.preorden.cliente.razon_social,
                'Equipo': f"{s.preorden.equipo.modelo} - {s.preorden.equipo.numero_serie}",
                'Tipo de trabajo': s.get_trabajo_display(),
                'Orden de servicio': s.orden_servicio or '',
                'Observaciones': s.observaciones or '',
                'Mano de obra': float(item['valor_mano_obra']),
                'Gastos': float(item['total_gastos']),
                'Repuestos': float(item['total_repuestos']),
                'Total': float(item['valor_total'])
            })
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=servicios_sin_ingresos.xlsx'
        df.to_excel(response, index=False)
        return response
    return render(request, 'reportes/servicios/sin_ingresos.html', {'servicios': servicios_sin_ingresos})

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
