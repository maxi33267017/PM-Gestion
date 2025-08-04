from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models.functions import TruncMonth, TruncYear
from decimal import Decimal
import pandas as pd
import io
from datetime import datetime, timedelta, date

from recursosHumanos.models import Usuario, RegistroHorasTecnico, ActividadTrabajo, Sucursal
from gestionDeTaller.models import (
    Servicio, PreOrden, 
    GastoAsistencia, VentaRepuesto, 
    GastoAsistenciaSimplificado, VentaRepuestosSimplificada, GastoInsumosTerceros
)
from clientes.models import Cliente
from crm.models import Embudo, AnalisisCliente

def calcular_gastos_servicios(servicios_query):
    """
    Calcula el total de gastos para un conjunto de servicios,
    incluyendo modelos antiguos y nuevos simplificados
    """
    # Gastos antiguos
    total_gastos_antiguos = servicios_query.aggregate(
        total=Sum('gastos__monto')
    )['total'] or 0
    
    # Gastos simplificados
    total_gastos_simplificados = servicios_query.aggregate(
        total=Sum('gastos_asistencia_simplificados__monto')
    )['total'] or 0
    
    # Gastos de terceros
    total_gastos_terceros = servicios_query.aggregate(
        total=Sum('gastos_insumos_terceros__monto')
    )['total'] or 0
    
    return total_gastos_antiguos + total_gastos_simplificados + total_gastos_terceros

def calcular_repuestos_servicios(servicios_query):
    """
    Calcula el total de repuestos para un conjunto de servicios,
    incluyendo modelos antiguos y nuevos simplificados
    """
    # Repuestos antiguos
    total_repuestos_antiguos = servicios_query.aggregate(
        total=Sum(F('repuestos__precio_unitario') * F('repuestos__cantidad'))
    )['total'] or 0
    
    # Repuestos simplificados
    total_repuestos_simplificados = servicios_query.aggregate(
        total=Sum('venta_repuestos_simplificada__monto_total')
    )['total'] or 0
    
    return total_repuestos_antiguos + total_repuestos_simplificados

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
    
    # Agregar gastos y repuestos a la facturación (incluyendo modelos antiguos y nuevos)
    servicios_mes = Servicio.objects.filter(
        estado='COMPLETADO',
        fecha_servicio__gte=inicio_mes
    )
    
    total_gastos = calcular_gastos_servicios(servicios_mes)
    total_repuestos = calcular_repuestos_servicios(servicios_mes)
    
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
                'titulo': 'Preórdenes Sin Servicio',
                'icono': 'bi-exclamation-triangle',
                'url': 'reportes:preordenes_sin_servicio',
                'descripcion': 'Seguimiento de oportunidades de negocio sin servicio asignado'
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
    
    # Calcular estadísticas de facturación
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    # Fecha actual y año actual
    ahora = timezone.now()
    inicio_ano = ahora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Servicios completados con facturación
    servicios_completados = Servicio.objects.filter(
        estado='COMPLETADO'
    )
    
    # Facturación total (mano de obra + gastos + repuestos)
    facturacion_total = servicios_completados.aggregate(
        total=Sum('valor_mano_obra')
    )['total'] or 0
    
    # Agregar gastos y repuestos (incluyendo modelos antiguos y nuevos)
    total_gastos = calcular_gastos_servicios(servicios_completados)
    total_repuestos = calcular_repuestos_servicios(servicios_completados)
    
    facturacion_total += total_gastos + total_repuestos
    
    # Servicios facturados (con algún valor)
    servicios_facturados = servicios_completados.filter(
        Q(valor_mano_obra__gt=0) | 
        Q(gastos__isnull=False) | 
        Q(repuestos__isnull=False)
    ).distinct().count()
    
    # Técnicos activos
    tecnicos_activos = Usuario.objects.filter(
        rol='TECNICO',
        is_active=True
    ).count()
    
    # Sucursales
    sucursales_count = Sucursal.objects.count()
    
    context = {
        'facturacion_total': f"${facturacion_total:,.0f}",
        'servicios_facturados': servicios_facturados,
        'tecnicos_activos': tecnicos_activos,
        'sucursales_count': sucursales_count
    }
    
    return render(request, 'reportes/facturacion/dashboard.html', context)

@login_required
def facturacion_por_tecnico(request):
    """Reporte de facturación por técnico"""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    # Obtener técnicos activos
    tecnicos = Usuario.objects.filter(
        rol='TECNICO',
        is_active=True
    ).order_by('first_name', 'last_name')
    
    # Filtrar por fechas si se proporcionan
    servicios_query = Servicio.objects.filter(estado='COMPLETADO')
    if fecha_inicio:
        servicios_query = servicios_query.filter(fecha_servicio__gte=fecha_inicio)
    if fecha_fin:
        servicios_query = servicios_query.filter(fecha_servicio__lte=fecha_fin)
    
    # Calcular facturación por técnico
    facturacion_por_tecnico = []
    for tecnico in tecnicos:
        # Obtener servicios donde el técnico registró horas
        servicios_tecnico = servicios_query.filter(
            registrohorastecnico__tecnico=tecnico
        ).distinct()
        
        # Calcular facturación
        total_mano_obra = servicios_tecnico.aggregate(
            total=Sum('valor_mano_obra')
        )['total'] or 0
        
        total_gastos = calcular_gastos_servicios(servicios_tecnico)
        total_repuestos = calcular_repuestos_servicios(servicios_tecnico)
        
        total_facturacion = total_mano_obra + total_gastos + total_repuestos
        
        # Calcular horas trabajadas
        horas_trabajadas = servicios_tecnico.aggregate(
            total_horas=Sum(
                ExpressionWrapper(
                    F('registrohorastecnico__hora_fin') - F('registrohorastecnico__hora_inicio'),
                    output_field=DurationField()
                )
            )
        )['total_horas'] or timedelta()
        
        horas_decimal = horas_trabajadas.total_seconds() / 3600 if horas_trabajadas else 0
        
        # Calcular servicios completados
        servicios_completados = servicios_tecnico.count()
        
        # Calcular valor por hora
        valor_por_hora = total_mano_obra / Decimal(str(horas_decimal)) if horas_decimal > 0 else Decimal('0')
        
        facturacion_por_tecnico.append({
            'tecnico': tecnico,
            'total_facturacion': total_facturacion,
            'mano_obra': total_mano_obra,
            'gastos': total_gastos,
            'repuestos': total_repuestos,
            'horas_trabajadas': horas_decimal,
            'servicios_completados': servicios_completados,
            'promedio_por_servicio': total_facturacion / servicios_completados if servicios_completados > 0 else 0,
            'valor_por_hora': valor_por_hora
        })
    
    # Ordenar por facturación total
    facturacion_por_tecnico.sort(key=lambda x: x['total_facturacion'], reverse=True)
    
    # Descarga Excel
    if request.GET.get('excel') == '1':
        datos = []
        for item in facturacion_por_tecnico:
            datos.append({
                'Técnico': f"{item['tecnico'].first_name} {item['tecnico'].last_name}",
                'Email': item['tecnico'].email,
                'Total Facturación': float(item['total_facturacion']),
                'Mano de Obra': float(item['mano_obra']),
                'Gastos': float(item['gastos']),
                'Repuestos': float(item['repuestos']),
                'Horas Trabajadas': round(item['horas_trabajadas'], 2),
                'Servicios Completados': item['servicios_completados'],
                'Promedio por Servicio': float(item['promedio_por_servicio']),
                'Valor por Hora': float(item['valor_por_hora'])
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=facturacion_por_tecnico.xlsx'
        df.to_excel(response, index=False)
        return response
    
    context = {
        'titulo': 'Facturación por Técnico',
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'facturacion_por_tecnico': facturacion_por_tecnico,
        'total_general': sum(item['total_facturacion'] for item in facturacion_por_tecnico)
    }
    return render(request, 'reportes/facturacion/por_tecnico.html', context)

@login_required
def facturacion_por_sucursal(request):
    """Reporte de facturación por sucursal"""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    # Obtener sucursales
    sucursales = Sucursal.objects.all().order_by('nombre')
    
    # Filtrar por fechas si se proporcionan
    servicios_query = Servicio.objects.filter(estado='COMPLETADO')
    if fecha_inicio:
        servicios_query = servicios_query.filter(fecha_servicio__gte=fecha_inicio)
    if fecha_fin:
        servicios_query = servicios_query.filter(fecha_servicio__lte=fecha_fin)
    
    # Calcular facturación por sucursal
    facturacion_por_sucursal = []
    for sucursal in sucursales:
        # Obtener servicios de la sucursal
        servicios_sucursal = servicios_query.filter(
            preorden__cliente__sucursal=sucursal
        )
        
        # Calcular facturación
        total_mano_obra = servicios_sucursal.aggregate(
            total=Sum('valor_mano_obra')
        )['total'] or 0
        
        # GASTOS: Incluir modelos antiguos y nuevos
        total_gastos = servicios_sucursal.aggregate(
            total=Sum('gastos__monto')
        )['total'] or 0
        
        total_gastos_simplificados = servicios_sucursal.aggregate(
            total=Sum('gastos_asistencia_simplificados__monto')
        )['total'] or 0
        
        total_gastos_terceros = servicios_sucursal.aggregate(
            total=Sum('gastos_insumos_terceros__monto')
        )['total'] or 0
        
        total_gastos = total_gastos_antiguos + total_gastos_simplificados + total_gastos_terceros
        
        # REPUESTOS: Incluir modelos antiguos y nuevos
        total_repuestos_antiguos = servicios_sucursal.aggregate(
            total=Sum(F('repuestos__precio_unitario') * F('repuestos__cantidad'))
        )['total'] or 0
        
        total_repuestos_simplificados = servicios_sucursal.aggregate(
            total=Sum('venta_repuestos_simplificada__monto_total')
        )['total'] or 0
        
        total_repuestos = total_repuestos_antiguos + total_repuestos_simplificados
        
        total_facturacion = total_mano_obra + total_gastos + total_repuestos
        
        # Calcular servicios completados
        servicios_completados = servicios_sucursal.count()
        
        # Calcular clientes únicos
        clientes_unicos = servicios_sucursal.values('preorden__cliente').distinct().count()
        
        # Calcular técnicos que trabajaron
        tecnicos_unicos = servicios_sucursal.values('registrohorastecnico__tecnico').distinct().count()
        
        facturacion_por_sucursal.append({
            'sucursal': sucursal,
            'total_facturacion': total_facturacion,
            'mano_obra': total_mano_obra,
            'gastos': total_gastos,
            'repuestos': total_repuestos,
            'servicios_completados': servicios_completados,
            'clientes_unicos': clientes_unicos,
            'tecnicos_unicos': tecnicos_unicos,
            'promedio_por_servicio': total_facturacion / servicios_completados if servicios_completados > 0 else 0
        })
    
    # Ordenar por facturación total
    facturacion_por_sucursal.sort(key=lambda x: x['total_facturacion'], reverse=True)
    
    # Descarga Excel
    if request.GET.get('excel') == '1':
        datos = []
        for item in facturacion_por_sucursal:
            datos.append({
                'Sucursal': item['sucursal'].nombre,
                'Total Facturación': float(item['total_facturacion']),
                'Mano de Obra': float(item['mano_obra']),
                'Gastos': float(item['gastos']),
                'Repuestos': float(item['repuestos']),
                'Servicios Completados': item['servicios_completados'],
                'Clientes Únicos': item['clientes_unicos'],
                'Técnicos Únicos': item['tecnicos_unicos'],
                'Promedio por Servicio': float(item['promedio_por_servicio'])
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=facturacion_por_sucursal.xlsx'
        df.to_excel(response, index=False)
        return response
    
    context = {
        'titulo': 'Facturación por Sucursal',
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'facturacion_por_sucursal': facturacion_por_sucursal,
        'total_general': sum(item['total_facturacion'] for item in facturacion_por_sucursal)
    }
    return render(request, 'reportes/facturacion/por_sucursal.html', context)

@login_required
def facturacion_mensual(request):
    """Reporte de facturación mensual"""
    año = request.GET.get('año', timezone.now().year)
    
    # Calcular facturación por mes del año seleccionado
    facturacion_mensual = []
    total_anual = 0
    
    for mes in range(1, 13):
        # Fecha inicio y fin del mes
        fecha_inicio = timezone.datetime(int(año), mes, 1, tzinfo=timezone.utc)
        if mes == 12:
            fecha_fin = timezone.datetime(int(año) + 1, 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
        else:
            fecha_fin = timezone.datetime(int(año), mes + 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
        
        # Obtener servicios del mes
        servicios_mes = Servicio.objects.filter(
            estado='COMPLETADO',
            fecha_servicio__gte=fecha_inicio,
            fecha_servicio__lte=fecha_fin
        )
        
        # Calcular facturación
        total_mano_obra = servicios_mes.aggregate(
            total=Sum('valor_mano_obra')
        )['total'] or 0
        
        total_gastos = servicios_mes.aggregate(
            total=Sum('gastos__monto')
        )['total'] or 0
        
        total_repuestos = servicios_mes.aggregate(
            total=Sum(F('repuestos__precio_unitario') * F('repuestos__cantidad'))
        )['total'] or 0
        
        total_facturacion = total_mano_obra + total_gastos + total_repuestos
        total_anual += total_facturacion
        
        # Calcular servicios completados
        servicios_completados = servicios_mes.count()
        
        # Calcular clientes únicos
        clientes_unicos = servicios_mes.values('preorden__cliente').distinct().count()
        
        facturacion_mensual.append({
            'mes': mes,
            'nombre_mes': fecha_inicio.strftime('%B'),
            'total_facturacion': total_facturacion,
            'mano_obra': total_mano_obra,
            'gastos': total_gastos,
            'repuestos': total_repuestos,
            'servicios_completados': servicios_completados,
            'clientes_unicos': clientes_unicos,
            'promedio_por_servicio': total_facturacion / servicios_completados if servicios_completados > 0 else 0
        })
    
    # Descarga Excel
    if request.GET.get('excel') == '1':
        datos = []
        for item in facturacion_mensual:
            datos.append({
                'Mes': item['nombre_mes'],
                'Total Facturación': float(item['total_facturacion']),
                'Mano de Obra': float(item['mano_obra']),
                'Gastos': float(item['gastos']),
                'Repuestos': float(item['repuestos']),
                'Servicios Completados': item['servicios_completados'],
                'Clientes Únicos': item['clientes_unicos'],
                'Promedio por Servicio': float(item['promedio_por_servicio'])
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=facturacion_mensual_{año}.xlsx'
        df.to_excel(response, index=False)
        return response
    
    context = {
        'titulo': 'Facturación Mensual',
        'año': año,
        'facturacion_mensual': facturacion_mensual,
        'total_anual': total_anual,
        'años_disponibles': range(2020, timezone.now().year + 1)
    }
    return render(request, 'reportes/facturacion/mensual.html', context)

@login_required
def facturacion_trimestral(request):
    """Reporte de facturación trimestral"""
    año = request.GET.get('año', timezone.now().year)
    
    # Calcular facturación por trimestre del año seleccionado
    facturacion_trimestral = []
    total_anual = 0
    
    for trimestre in range(1, 5):
        # Definir meses del trimestre
        if trimestre == 1:
            meses = [1, 2, 3]
            nombre_trimestre = "Q1 (Ene-Mar)"
        elif trimestre == 2:
            meses = [4, 5, 6]
            nombre_trimestre = "Q2 (Abr-Jun)"
        elif trimestre == 3:
            meses = [7, 8, 9]
            nombre_trimestre = "Q3 (Jul-Sep)"
        else:
            meses = [10, 11, 12]
            nombre_trimestre = "Q4 (Oct-Dic)"
        
        # Calcular facturación del trimestre
        total_trimestre = 0
        servicios_trimestre = 0
        clientes_unicos = set()
        
        for mes in meses:
            # Fecha inicio y fin del mes
            fecha_inicio = timezone.datetime(int(año), mes, 1, tzinfo=timezone.utc)
            if mes == 12:
                fecha_fin = timezone.datetime(int(año) + 1, 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
            else:
                fecha_fin = timezone.datetime(int(año), mes + 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
            
            # Obtener servicios del mes
            servicios_mes = Servicio.objects.filter(
                estado='COMPLETADO',
                fecha_servicio__gte=fecha_inicio,
                fecha_servicio__lte=fecha_fin
            )
            
            # Calcular facturación del mes (incluyendo modelos antiguos y nuevos)
            total_mano_obra = servicios_mes.aggregate(
                total=Sum('valor_mano_obra')
            )['total'] or 0
            
        total_gastos = calcular_gastos_servicios(servicios_mes)
        total_repuestos = calcular_repuestos_servicios(servicios_mes)
            
        total_mes = total_mano_obra + total_gastos + total_repuestos
        total_trimestre += total_mes
        servicios_trimestre += servicios_mes.count()
            
            # Agregar clientes únicos
        clientes_mes = servicios_mes.values_list('preorden__cliente', flat=True)
        clientes_unicos.update(clientes_mes)
        
        total_anual += total_trimestre
        
        facturacion_trimestral.append({
            'trimestre': trimestre,
            'nombre_trimestre': nombre_trimestre,
            'meses': meses,
            'total_facturacion': total_trimestre,
            'servicios_completados': servicios_trimestre,
            'clientes_unicos': len(clientes_unicos),
            'promedio_por_servicio': total_trimestre / servicios_trimestre if servicios_trimestre > 0 else 0
        })
    
    # Calcular datos del año anterior para comparación
    año_anterior = int(año) - 1
    facturacion_anterior = []
    total_anterior = 0
    
    for trimestre in range(1, 5):
        total_trimestre_anterior = 0
        for mes in range((trimestre-1)*3 + 1, trimestre*3 + 1):
            fecha_inicio = timezone.datetime(año_anterior, mes, 1, tzinfo=timezone.utc)
            if mes == 12:
                fecha_fin = timezone.datetime(año_anterior + 1, 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
            else:
                fecha_fin = timezone.datetime(año_anterior, mes + 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
            
            servicios_mes = Servicio.objects.filter(
                estado='COMPLETADO',
                fecha_servicio__gte=fecha_inicio,
                fecha_servicio__lte=fecha_fin
            )
            
            total_mano_obra = servicios_mes.aggregate(total=Sum('valor_mano_obra'))['total'] or 0
            total_gastos = calcular_gastos_servicios(servicios_mes)
            total_repuestos = calcular_repuestos_servicios(servicios_mes)
            
            total_trimestre_anterior += total_mano_obra + total_gastos + total_repuestos
        
        total_anterior += total_trimestre_anterior
        facturacion_anterior.append(total_trimestre_anterior)
    
    # Agregar comparación con año anterior
    for i, item in enumerate(facturacion_trimestral):
        item['facturacion_anterior'] = facturacion_anterior[i]
        item['variacion'] = item['total_facturacion'] - item['facturacion_anterior']
        item['variacion_porcentual'] = (
            (item['variacion'] / item['facturacion_anterior'] * 100) 
            if item['facturacion_anterior'] > 0 else 0
        )
    
    # Descarga Excel
    if request.GET.get('excel') == '1':
        datos = []
        for item in facturacion_trimestral:
            datos.append({
                'Trimestre': item['nombre_trimestre'],
                'Total Facturación': float(item['total_facturacion']),
                'Servicios Completados': item['servicios_completados'],
                'Clientes Únicos': item['clientes_unicos'],
                'Promedio por Servicio': float(item['promedio_por_servicio']),
                'Facturación Año Anterior': float(item['facturacion_anterior']),
                'Variación': float(item['variacion']),
                'Variación %': round(item['variacion_porcentual'], 2)
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=facturacion_trimestral_{año}.xlsx'
        df.to_excel(response, index=False)
        return response
    
    context = {
        'titulo': 'Facturación Trimestral',
        'año': año,
        'facturacion_trimestral': facturacion_trimestral,
        'total_anual': total_anual,
        'total_anterior': total_anterior,
        'variacion_anual': total_anual - total_anterior,
        'variacion_anual_porcentual': ((total_anual - total_anterior) / total_anterior * 100) if total_anterior > 0 else 0,
        'años_disponibles': range(2020, timezone.now().year + 1)
    }
    return render(request, 'reportes/facturacion/trimestral.html', context)

@login_required
def facturacion_semestral(request):
    """Reporte de facturación semestral"""
    año = request.GET.get('año', timezone.now().year)
    
    # Calcular facturación por semestre del año seleccionado
    facturacion_semestral = []
    total_anual = 0
    
    for semestre in range(1, 3):
        # Definir meses del semestre
        if semestre == 1:
            meses = [1, 2, 3, 4, 5, 6]
            nombre_semestre = "S1 (Ene-Jun)"
        else:
            meses = [7, 8, 9, 10, 11, 12]
            nombre_semestre = "S2 (Jul-Dic)"
        
        # Calcular facturación del semestre
        total_semestre = 0
        servicios_semestre = 0
        clientes_unicos = set()
        
        for mes in meses:
            # Fecha inicio y fin del mes
            fecha_inicio = timezone.datetime(int(año), mes, 1, tzinfo=timezone.utc)
            if mes == 12:
                fecha_fin = timezone.datetime(int(año) + 1, 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
            else:
                fecha_fin = timezone.datetime(int(año), mes + 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
            
            # Obtener servicios del mes
            servicios_mes = Servicio.objects.filter(
                estado='COMPLETADO',
                fecha_servicio__gte=fecha_inicio,
                fecha_servicio__lte=fecha_fin
            )
            
            # Calcular facturación del mes (incluyendo modelos antiguos y nuevos)
            total_mano_obra = servicios_mes.aggregate(
                total=Sum('valor_mano_obra')
            )['total'] or 0
            
            total_gastos = calcular_gastos_servicios(servicios_mes)
            total_repuestos = calcular_repuestos_servicios(servicios_mes)
            
            total_mes = total_mano_obra + total_gastos + total_repuestos
            total_semestre += total_mes
            servicios_semestre += servicios_mes.count()
            
            # Agregar clientes únicos
            clientes_mes = servicios_mes.values_list('preorden__cliente', flat=True)
            clientes_unicos.update(clientes_mes)
        
        total_anual += total_semestre
        
        facturacion_semestral.append({
            'semestre': semestre,
            'nombre_semestre': nombre_semestre,
            'meses': meses,
            'total_facturacion': total_semestre,
            'servicios_completados': servicios_semestre,
            'clientes_unicos': len(clientes_unicos),
            'promedio_por_servicio': total_semestre / servicios_semestre if servicios_semestre > 0 else 0
        })
    
    # Calcular datos del año anterior para comparación
    año_anterior = int(año) - 1
    facturacion_anterior = []
    total_anterior = 0
    
    for semestre in range(1, 3):
        total_semestre_anterior = 0
        for mes in range((semestre-1)*6 + 1, semestre*6 + 1):
            fecha_inicio = timezone.datetime(año_anterior, mes, 1, tzinfo=timezone.utc)
            if mes == 12:
                fecha_fin = timezone.datetime(año_anterior + 1, 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
            else:
                fecha_fin = timezone.datetime(año_anterior, mes + 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
            
            servicios_mes = Servicio.objects.filter(
                estado='COMPLETADO',
                fecha_servicio__gte=fecha_inicio,
                fecha_servicio__lte=fecha_fin
            )
            
            total_mano_obra = servicios_mes.aggregate(total=Sum('valor_mano_obra'))['total'] or 0
            total_gastos = calcular_gastos_servicios(servicios_mes)
            total_repuestos = calcular_repuestos_servicios(servicios_mes)
            
            total_semestre_anterior += total_mano_obra + total_gastos + total_repuestos
        
        total_anterior += total_semestre_anterior
        facturacion_anterior.append(total_semestre_anterior)
    
    # Agregar comparación con año anterior
    for i, item in enumerate(facturacion_semestral):
        item['facturacion_anterior'] = facturacion_anterior[i]
        item['variacion'] = item['total_facturacion'] - item['facturacion_anterior']
        item['variacion_porcentual'] = (
            (item['variacion'] / item['facturacion_anterior'] * 100) 
            if item['facturacion_anterior'] > 0 else 0
        )
    
    # Descarga Excel
    if request.GET.get('excel') == '1':
        datos = []
        for item in facturacion_semestral:
            datos.append({
                'Semestre': item['nombre_semestre'],
                'Total Facturación': float(item['total_facturacion']),
                'Servicios Completados': item['servicios_completados'],
                'Clientes Únicos': item['clientes_unicos'],
                'Promedio por Servicio': float(item['promedio_por_servicio']),
                'Facturación Año Anterior': float(item['facturacion_anterior']),
                'Variación': float(item['variacion']),
                'Variación %': round(item['variacion_porcentual'], 2)
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=facturacion_semestral_{año}.xlsx'
        df.to_excel(response, index=False)
        return response
    
    context = {
        'titulo': 'Facturación Semestral',
        'año': año,
        'facturacion_semestral': facturacion_semestral,
        'total_anual': total_anual,
        'total_anterior': total_anterior,
        'variacion_anual': total_anual - total_anterior,
        'variacion_anual_porcentual': ((total_anual - total_anterior) / total_anterior * 100) if total_anterior > 0 else 0,
        'años_disponibles': range(2020, timezone.now().year + 1)
    }
    return render(request, 'reportes/facturacion/semestral.html', context)

@login_required
def facturacion_anual(request):
    """Reporte de facturación anual"""
    año = request.GET.get('año', timezone.now().year)
    
    # Calcular facturación del año seleccionado
    facturacion_anual = []
    total_anual = 0
    
    for mes in range(1, 13):
        # Fecha inicio y fin del mes
        fecha_inicio = timezone.datetime(int(año), mes, 1, tzinfo=timezone.utc)
        if mes == 12:
            fecha_fin = timezone.datetime(int(año) + 1, 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
        else:
            fecha_fin = timezone.datetime(int(año), mes + 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
        
        # Obtener servicios del mes
        servicios_mes = Servicio.objects.filter(
            estado='COMPLETADO',
            fecha_servicio__gte=fecha_inicio,
            fecha_servicio__lte=fecha_fin
        )
        
        # Calcular facturación del mes (incluyendo modelos antiguos y nuevos)
        total_mano_obra = servicios_mes.aggregate(
            total=Sum('valor_mano_obra')
        )['total'] or 0
        
        total_gastos = calcular_gastos_servicios(servicios_mes)
        total_repuestos = calcular_repuestos_servicios(servicios_mes)
        
        total_mes = total_mano_obra + total_gastos + total_repuestos
        total_anual += total_mes
        
        # Calcular servicios completados
        servicios_completados = servicios_mes.count()
        
        # Calcular clientes únicos
        clientes_unicos = servicios_mes.values('preorden__cliente').distinct().count()
        
        facturacion_anual.append({
            'mes': mes,
            'nombre_mes': fecha_inicio.strftime('%B'),
            'total_facturacion': total_mes,
            'mano_obra': total_mano_obra,
            'gastos': total_gastos,
            'repuestos': total_repuestos,
            'servicios_completados': servicios_completados,
            'clientes_unicos': clientes_unicos,
            'promedio_por_servicio': total_mes / servicios_completados if servicios_completados > 0 else 0
        })
    
    # Calcular datos del año anterior para comparación
    año_anterior = int(año) - 1
    facturacion_anterior = []
    total_anterior = 0
    
    for mes in range(1, 13):
        fecha_inicio = timezone.datetime(año_anterior, mes, 1, tzinfo=timezone.utc)
        if mes == 12:
            fecha_fin = timezone.datetime(año_anterior + 1, 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
        else:
            fecha_fin = timezone.datetime(año_anterior, mes + 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
        
        servicios_mes = Servicio.objects.filter(
            estado='COMPLETADO',
            fecha_servicio__gte=fecha_inicio,
            fecha_servicio__lte=fecha_fin
        )
        
        total_mano_obra = servicios_mes.aggregate(total=Sum('valor_mano_obra'))['total'] or 0
        total_gastos = calcular_gastos_servicios(servicios_mes)
        total_repuestos = calcular_repuestos_servicios(servicios_mes)
        
        total_mes_anterior = total_mano_obra + total_gastos + total_repuestos
        total_anterior += total_mes_anterior
        facturacion_anterior.append(total_mes_anterior)
    
    # Agregar comparación con año anterior
    for i, item in enumerate(facturacion_anual):
        item['facturacion_anterior'] = facturacion_anterior[i]
        item['variacion'] = item['total_facturacion'] - item['facturacion_anterior']
        item['variacion_porcentual'] = (
            (item['variacion'] / item['facturacion_anterior'] * 100) 
            if item['facturacion_anterior'] > 0 else 0
        )
    
    # Calcular métricas adicionales
    total_servicios = sum(item['servicios_completados'] for item in facturacion_anual)
    total_clientes = sum(item['clientes_unicos'] for item in facturacion_anual)
    promedio_mensual = total_anual / 12 if total_anual > 0 else 0
    
    # Calcular trimestres
    q1 = sum(item['total_facturacion'] for item in facturacion_anual[:3])
    q2 = sum(item['total_facturacion'] for item in facturacion_anual[3:6])
    q3 = sum(item['total_facturacion'] for item in facturacion_anual[6:9])
    q4 = sum(item['total_facturacion'] for item in facturacion_anual[9:12])
    
    # Calcular porcentajes trimestrales
    q1_porcentaje = (q1 / total_anual * 100) if total_anual > 0 else 0
    q2_porcentaje = (q2 / total_anual * 100) if total_anual > 0 else 0
    q3_porcentaje = (q3 / total_anual * 100) if total_anual > 0 else 0
    q4_porcentaje = (q4 / total_anual * 100) if total_anual > 0 else 0
    
    # Descarga Excel
    if request.GET.get('excel') == '1':
        datos = []
        for item in facturacion_anual:
            datos.append({
                'Mes': item['nombre_mes'],
                'Total Facturación': float(item['total_facturacion']),
                'Mano de Obra': float(item['mano_obra']),
                'Gastos': float(item['gastos']),
                'Repuestos': float(item['repuestos']),
                'Servicios Completados': item['servicios_completados'],
                'Clientes Únicos': item['clientes_unicos'],
                'Promedio por Servicio': float(item['promedio_por_servicio']),
                'Facturación Año Anterior': float(item['facturacion_anterior']),
                'Variación': float(item['variacion']),
                'Variación %': round(item['variacion_porcentual'], 2)
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=facturacion_anual_{año}.xlsx'
        df.to_excel(response, index=False)
        return response
    
    context = {
        'titulo': 'Facturación Anual',
        'año': año,
        'facturacion_anual': facturacion_anual,
        'total_anual': total_anual,
        'total_anterior': total_anterior,
        'variacion_anual': total_anual - total_anterior,
        'variacion_anual_porcentual': ((total_anual - total_anterior) / total_anterior * 100) if total_anterior > 0 else 0,
        'total_servicios': total_servicios,
        'total_clientes': total_clientes,
        'promedio_mensual': promedio_mensual,
        'q1': q1,
        'q2': q2,
        'q3': q3,
        'q4': q4,
        'q1_porcentaje': q1_porcentaje,
        'q2_porcentaje': q2_porcentaje,
        'q3_porcentaje': q3_porcentaje,
        'q4_porcentaje': q4_porcentaje,
        'años_disponibles': range(2020, timezone.now().year + 1)
    }
    return render(request, 'reportes/facturacion/anual.html', context)

# ===== REPORTES DE HORAS =====

@login_required
def reportes_horas(request):
    """Dashboard de reportes de horas"""
    from recursosHumanos.models import RegistroHorasTecnico, Usuario
    from django.db.models import Sum, Count, Avg, F, ExpressionWrapper, fields, Q
    from datetime import datetime, timedelta
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    # Filtrar registros de horas
    registros = RegistroHorasTecnico.objects.all()
    
    # Aplicar filtros de fecha
    if fecha_inicio:
        registros = registros.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        registros = registros.filter(fecha__lte=fecha_fin)
    
    # Calcular estadísticas generales
    total_registros = registros.count()
    total_tecnicos = registros.values('tecnico').distinct().count()
    
    # Calcular horas totales
    total_horas = registros.aggregate(
        total=Sum(
            ExpressionWrapper(
                F('hora_fin') - F('hora_inicio'),
                output_field=fields.DurationField()
            )
        )
    )['total'] or timedelta(0)
    
    # Calcular horas por tipo
    horas_disponibles = registros.filter(
        tipo_hora__disponibilidad='DISPONIBLE'
    ).aggregate(
        total=Sum(
            ExpressionWrapper(
                F('hora_fin') - F('hora_inicio'),
                output_field=fields.DurationField()
            )
        )
    )['total'] or timedelta(0)
    
    horas_no_disponibles = registros.filter(
        tipo_hora__disponibilidad='NO_DISPONIBLE'
    ).aggregate(
        total=Sum(
            ExpressionWrapper(
                F('hora_fin') - F('hora_inicio'),
                output_field=fields.DurationField()
            )
        )
    )['total'] or timedelta(0)
    
    # Calcular horas que generan ingreso
    horas_generan_ingreso = registros.filter(
        tipo_hora__disponibilidad='DISPONIBLE',
        tipo_hora__genera_ingreso='INGRESO'
    ).aggregate(
        total=Sum(
            ExpressionWrapper(
                F('hora_fin') - F('hora_inicio'),
                output_field=fields.DurationField()
            )
        )
    )['total'] or timedelta(0)
    
    # Calcular horas aprobadas
    horas_aprobadas = registros.filter(aprobado=True).aggregate(
        total=Sum(
            ExpressionWrapper(
                F('hora_fin') - F('hora_inicio'),
                output_field=fields.DurationField()
            )
        )
    )['total'] or timedelta(0)
    
    # Calcular promedio de horas por técnico
    promedio_horas_tecnico = registros.values('tecnico').annotate(
        horas_tecnico=Sum(
            ExpressionWrapper(
                F('hora_fin') - F('hora_inicio'),
                output_field=fields.DurationField()
            )
        )
    ).aggregate(
        promedio=Avg('horas_tecnico')
    )['promedio'] or timedelta(0)
    
    # Calcular eficiencia (horas que generan ingreso / horas disponibles)
    eficiencia = 0
    if horas_disponibles.total_seconds() > 0:
        eficiencia = (horas_generan_ingreso.total_seconds() / horas_disponibles.total_seconds()) * 100
    
    # Calcular productividad (horas aprobadas / horas totales)
    productividad = 0
    if total_horas.total_seconds() > 0:
        productividad = (horas_aprobadas.total_seconds() / total_horas.total_seconds()) * 100
    
    context = {
        'titulo': 'Dashboard de Reportes de Horas',
        'total_registros': total_registros,
        'total_tecnicos': total_tecnicos,
        'total_horas': total_horas,
        'horas_disponibles': horas_disponibles,
        'horas_no_disponibles': horas_no_disponibles,
        'horas_generan_ingreso': horas_generan_ingreso,
        'horas_aprobadas': horas_aprobadas,
        'promedio_horas_tecnico': promedio_horas_tecnico,
        'eficiencia': eficiencia,
        'productividad': productividad,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'secciones': [
            {
                'titulo': 'Por Sucursal',
                'icono': 'bi-building',
                'url': 'reportes:horas_sucursal',
                'descripcion': 'Análisis de horas trabajadas por sucursal'
            },
            {
                'titulo': 'Por Técnico',
                'icono': 'bi-person-workspace',
                'url': 'reportes:horas_tecnico',
                'descripcion': 'Análisis detallado de horas por técnico'
            },
            {
                'titulo': 'Productividad',
                'icono': 'bi-graph-up-arrow',
                'url': 'reportes:productividad',
                'descripcion': 'Métricas de productividad de técnicos'
            },
            {
                'titulo': 'Eficiencia',
                'icono': 'bi-speedometer2',
                'url': 'reportes:eficiencia',
                'descripcion': 'Análisis de eficiencia en el uso del tiempo'
            },
            {
                'titulo': 'Desempeño',
                'icono': 'bi-trophy',
                'url': 'reportes:desempeno',
                'descripcion': 'Evaluación del desempeño de técnicos'
            }
        ]
    }
    
    return render(request, 'reportes/horas/dashboard.html', context)

@login_required
def horas_por_sucursal(request):
    """Reporte de horas por sucursal"""
    from recursosHumanos.models import RegistroHorasTecnico, Sucursal
    from django.db.models import Sum, Count, F, ExpressionWrapper, fields, Q
    from datetime import datetime, timedelta
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    exportar = request.GET.get('exportar') == 'excel'
    
    # Filtrar registros de horas
    registros = RegistroHorasTecnico.objects.all()
    
    # Aplicar filtros de fecha
    if fecha_inicio:
        registros = registros.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        registros = registros.filter(fecha__lte=fecha_fin)
    
    # Obtener todas las sucursales
    sucursales = Sucursal.objects.filter(activo=True).order_by('nombre')
    
    # Calcular estadísticas por sucursal
    horas_por_sucursal = []
    for sucursal in sucursales:
        # Filtrar registros de la sucursal
        registros_sucursal = registros.filter(tecnico__sucursal=sucursal)
        
        # Calcular totales
        total_horas = registros_sucursal.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_disponibles = registros_sucursal.filter(
            tipo_hora__disponibilidad='DISPONIBLE'
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_no_disponibles = registros_sucursal.filter(
            tipo_hora__disponibilidad='NO_DISPONIBLE'
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_generan_ingreso = registros_sucursal.filter(
            tipo_hora__disponibilidad='DISPONIBLE',
            tipo_hora__genera_ingreso='INGRESO'
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_aprobadas = registros_sucursal.filter(aprobado=True).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        # Calcular métricas
        total_tecnicos = registros_sucursal.values('tecnico').distinct().count()
        total_registros = registros_sucursal.count()
        
        # Calcular eficiencia
        eficiencia = 0
        if horas_disponibles.total_seconds() > 0:
            eficiencia = (horas_generan_ingreso.total_seconds() / horas_disponibles.total_seconds()) * 100
        
        # Calcular productividad
        productividad = 0
        if total_horas.total_seconds() > 0:
            productividad = (horas_aprobadas.total_seconds() / total_horas.total_seconds()) * 100
        
        # Calcular promedio por técnico
        promedio_por_tecnico = timedelta(0)
        if total_tecnicos > 0:
            promedio_por_tecnico = timedelta(seconds=total_horas.total_seconds() / total_tecnicos)
        
        horas_por_sucursal.append({
            'sucursal': sucursal,
            'total_horas': total_horas,
            'horas_disponibles': horas_disponibles,
            'horas_no_disponibles': horas_no_disponibles,
            'horas_generan_ingreso': horas_generan_ingreso,
            'horas_aprobadas': horas_aprobadas,
            'total_tecnicos': total_tecnicos,
            'total_registros': total_registros,
            'eficiencia': eficiencia,
            'productividad': productividad,
            'promedio_por_tecnico': promedio_por_tecnico
        })
    
    # Ordenar por total de horas
    horas_por_sucursal.sort(key=lambda x: x['total_horas'], reverse=True)
    
    # Calcular totales generales
    total_general_horas = timedelta(0)
    for item in horas_por_sucursal:
        if isinstance(item['total_horas'], timedelta):
            total_general_horas += item['total_horas']
        else:
            total_general_horas += timedelta(seconds=item['total_horas'])
    
    total_general_tecnicos = sum(item['total_tecnicos'] for item in horas_por_sucursal)
    total_general_registros = sum(item['total_registros'] for item in horas_por_sucursal)
    
    # Exportar a Excel si se solicita
    if exportar:
        import pandas as pd
        from django.http import HttpResponse
        
        datos = []
        for item in horas_por_sucursal:
            datos.append({
                'Sucursal': item['sucursal'].nombre,
                'Total Horas': round(item['total_horas'].total_seconds() / 3600, 2),
                'Horas Disponibles': round(item['horas_disponibles'].total_seconds() / 3600, 2),
                'Horas No Disponibles': round(item['horas_no_disponibles'].total_seconds() / 3600, 2),
                'Horas Generan Ingreso': round(item['horas_generan_ingreso'].total_seconds() / 3600, 2),
                'Horas Aprobadas': round(item['horas_aprobadas'].total_seconds() / 3600, 2),
                'Total Técnicos': item['total_tecnicos'],
                'Total Registros': item['total_registros'],
                'Eficiencia (%)': round(item['eficiencia'], 2),
                'Productividad (%)': round(item['productividad'], 2),
                'Promedio por Técnico (h)': round(item['promedio_por_tecnico'].total_seconds() / 3600, 2)
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=horas_por_sucursal.xlsx'
        df.to_excel(response, index=False)
        return response
    
    context = {
        'titulo': 'Horas por Sucursal',
        'horas_por_sucursal': horas_por_sucursal,
        'total_general_horas': total_general_horas,
        'total_general_tecnicos': total_general_tecnicos,
        'total_general_registros': total_general_registros,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }
    
    return render(request, 'reportes/horas/por_sucursal.html', context)

@login_required
def horas_por_tecnico(request):
    """Reporte de horas por técnico"""
    from recursosHumanos.models import RegistroHorasTecnico, Usuario
    from django.db.models import Sum, Count, F, ExpressionWrapper, fields, Q
    from datetime import datetime, timedelta
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    sucursal = request.GET.get('sucursal')
    exportar = request.GET.get('exportar') == 'excel'
    
    # Filtrar registros de horas
    registros = RegistroHorasTecnico.objects.all()
    
    # Aplicar filtros
    if fecha_inicio:
        registros = registros.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        registros = registros.filter(fecha__lte=fecha_fin)
    if sucursal:
        registros = registros.filter(tecnico__sucursal_id=sucursal)
    
    # Obtener técnicos que tienen registros
    tecnicos_con_registros = registros.values('tecnico').distinct()
    tecnicos = Usuario.objects.filter(
        id__in=tecnicos_con_registros,
        rol='TECNICO'
    ).select_related('sucursal').order_by('sucursal__nombre', 'apellido', 'nombre')
    
    # Calcular estadísticas por técnico
    horas_por_tecnico = []
    for tecnico in tecnicos:
        # Filtrar registros del técnico
        registros_tecnico = registros.filter(tecnico=tecnico)
        
        # Calcular totales
        total_horas = registros_tecnico.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_disponibles = registros_tecnico.filter(
            tipo_hora__disponibilidad='DISPONIBLE'
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_no_disponibles = registros_tecnico.filter(
            tipo_hora__disponibilidad='NO_DISPONIBLE'
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_generan_ingreso = registros_tecnico.filter(
            tipo_hora__disponibilidad='DISPONIBLE',
            tipo_hora__genera_ingreso='INGRESO'
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_aprobadas = registros_tecnico.filter(aprobado=True).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        # Calcular métricas
        total_registros = registros_tecnico.count()
        dias_trabajados = registros_tecnico.values('fecha').distinct().count()
        
        # Calcular eficiencia
        eficiencia = 0
        if horas_disponibles.total_seconds() > 0:
            eficiencia = (horas_generan_ingreso.total_seconds() / horas_disponibles.total_seconds()) * 100
        
        # Calcular productividad
        productividad = 0
        if total_horas.total_seconds() > 0:
            productividad = (horas_aprobadas.total_seconds() / total_horas.total_seconds()) * 100
        
        # Calcular promedio por día
        promedio_por_dia = timedelta(0)
        if dias_trabajados > 0:
            promedio_por_dia = timedelta(seconds=total_horas.total_seconds() / dias_trabajados)
        
        # Calcular horas pendientes de aprobación
        horas_pendientes = total_horas - horas_aprobadas
        
        horas_por_tecnico.append({
            'tecnico': tecnico,
            'total_horas': total_horas,
            'horas_disponibles': horas_disponibles,
            'horas_no_disponibles': horas_no_disponibles,
            'horas_generan_ingreso': horas_generan_ingreso,
            'horas_aprobadas': horas_aprobadas,
            'horas_pendientes': horas_pendientes,
            'total_registros': total_registros,
            'dias_trabajados': dias_trabajados,
            'eficiencia': eficiencia,
            'productividad': productividad,
            'promedio_por_dia': promedio_por_dia
        })
    
    # Ordenar por total de horas
    horas_por_tecnico.sort(key=lambda x: x['total_horas'], reverse=True)
    
    # Calcular totales generales
    total_general_horas = timedelta(0)
    for item in horas_por_tecnico:
        if isinstance(item['total_horas'], timedelta):
            total_general_horas += item['total_horas']
        else:
            total_general_horas += timedelta(seconds=item['total_horas'])
    
    total_general_tecnicos = len(horas_por_tecnico)
    total_general_registros = sum(item['total_registros'] for item in horas_por_tecnico)
    
    # Exportar a Excel si se solicita
    if exportar:
        import pandas as pd
        from django.http import HttpResponse
        
        datos = []
        for item in horas_por_tecnico:
            datos.append({
                'Técnico': f"{item['tecnico'].apellido}, {item['tecnico'].nombre}",
                'Email': item['tecnico'].email,
                'Sucursal': item['tecnico'].sucursal.nombre if item['tecnico'].sucursal else 'Sin sucursal',
                'Total Horas': round(item['total_horas'].total_seconds() / 3600, 2),
                'Horas Disponibles': round(item['horas_disponibles'].total_seconds() / 3600, 2),
                'Horas No Disponibles': round(item['horas_no_disponibles'].total_seconds() / 3600, 2),
                'Horas Generan Ingreso': round(item['horas_generan_ingreso'].total_seconds() / 3600, 2),
                'Horas Aprobadas': round(item['horas_aprobadas'].total_seconds() / 3600, 2),
                'Horas Pendientes': round(item['horas_pendientes'].total_seconds() / 3600, 2),
                'Total Registros': item['total_registros'],
                'Días Trabajados': item['dias_trabajados'],
                'Eficiencia (%)': round(item['eficiencia'], 2),
                'Productividad (%)': round(item['productividad'], 2),
                'Promedio por Día (h)': round(item['promedio_por_dia'].total_seconds() / 3600, 2)
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=horas_por_tecnico.xlsx'
        df.to_excel(response, index=False)
        return response
    
    # Obtener lista de sucursales para el filtro
    from recursosHumanos.models import Sucursal
    sucursales_filtro = Sucursal.objects.filter(activo=True)
    
    context = {
        'titulo': 'Horas por Técnico',
        'horas_por_tecnico': horas_por_tecnico,
        'total_general_horas': total_general_horas,
        'total_general_tecnicos': total_general_tecnicos,
        'total_general_registros': total_general_registros,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'sucursal_filtro': sucursal,
        'sucursales_filtro': sucursales_filtro,
    }
    
    return render(request, 'reportes/horas/por_tecnico.html', context)

@login_required
def productividad_tecnicos(request):
    """Reporte de productividad de técnicos"""
    from recursosHumanos.models import RegistroHorasTecnico, Usuario
    from django.db.models import Sum, Count, F, ExpressionWrapper, fields, Q, Avg
    from datetime import datetime, timedelta
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    sucursal = request.GET.get('sucursal')
    exportar = request.GET.get('exportar') == 'excel'
    
    # Filtrar registros de horas
    registros = RegistroHorasTecnico.objects.all()
    
    # Aplicar filtros
    if fecha_inicio:
        registros = registros.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        registros = registros.filter(fecha__lte=fecha_fin)
    if sucursal:
        registros = registros.filter(tecnico__sucursal_id=sucursal)
    
    # Obtener técnicos que tienen registros
    tecnicos_con_registros = registros.values('tecnico').distinct()
    tecnicos = Usuario.objects.filter(
        id__in=tecnicos_con_registros,
        rol='TECNICO'
    ).select_related('sucursal').order_by('sucursal__nombre', 'apellido', 'nombre')
    
    # Calcular métricas de productividad por técnico
    productividad_tecnicos = []
    for tecnico in tecnicos:
        # Filtrar registros del técnico
        registros_tecnico = registros.filter(tecnico=tecnico)
        
        # Calcular horas por tipo de actividad
        horas_por_actividad = registros_tecnico.values('tipo_hora__nombre').annotate(
            total_horas=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            ),
            cantidad_registros=Count('id', distinct=True)
        ).order_by('-total_horas')
        
        # Calcular métricas generales
        total_horas = registros_tecnico.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_disponibles = registros_tecnico.filter(
            tipo_hora__disponibilidad='DISPONIBLE'
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_generan_ingreso = registros_tecnico.filter(
            tipo_hora__disponibilidad='DISPONIBLE',
            tipo_hora__genera_ingreso='INGRESO'
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_aprobadas = registros_tecnico.filter(aprobado=True).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        # Calcular métricas de productividad
        total_registros = registros_tecnico.count()
        dias_trabajados = registros_tecnico.values('fecha').distinct().count()
        
        # Productividad = (horas que generan ingreso / horas disponibles) * 100
        productividad = 0
        if horas_disponibles.total_seconds() > 0:
            productividad = (horas_generan_ingreso.total_seconds() / horas_disponibles.total_seconds()) * 100
        
        # Eficiencia = (horas aprobadas / horas totales) * 100
        eficiencia = 0
        if total_horas.total_seconds() > 0:
            eficiencia = (horas_aprobadas.total_seconds() / total_horas.total_seconds()) * 100
        
        # Utilización = (horas disponibles / horas totales) * 100
        utilizacion = 0
        if total_horas.total_seconds() > 0:
            utilizacion = (horas_disponibles.total_seconds() / total_horas.total_seconds()) * 100
        
        # Promedio de horas por día
        promedio_por_dia = timedelta(0)
        if dias_trabajados > 0:
            promedio_por_dia = timedelta(seconds=total_horas.total_seconds() / dias_trabajados)
        
        # Promedio de horas productivas por día
        promedio_productivo_por_dia = timedelta(0)
        if dias_trabajados > 0:
            promedio_productivo_por_dia = timedelta(seconds=horas_generan_ingreso.total_seconds() / dias_trabajados)
        
        # Calcular tendencia (comparar con período anterior si hay datos)
        tendencia = 0
        if fecha_inicio and fecha_fin:
            # Calcular período anterior de igual duración
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            duracion_periodo = (fecha_fin_dt - fecha_inicio_dt).days
            
            fecha_inicio_anterior = fecha_inicio_dt - timedelta(days=duracion_periodo)
            fecha_fin_anterior = fecha_inicio_dt - timedelta(days=1)
            
            registros_anterior = RegistroHorasTecnico.objects.filter(
                tecnico=tecnico,
                fecha__range=[fecha_inicio_anterior, fecha_fin_anterior]
            )
            
            horas_anterior = registros_anterior.aggregate(
                total=Sum(
                    ExpressionWrapper(
                        F('hora_fin') - F('hora_inicio'),
                        output_field=fields.DurationField()
                    )
                )
            )['total'] or timedelta(0)
            
            if horas_anterior.total_seconds() > 0:
                tendencia = ((total_horas.total_seconds() - horas_anterior.total_seconds()) / horas_anterior.total_seconds()) * 100
        
        productividad_tecnicos.append({
            'tecnico': tecnico,
            'total_horas': total_horas,
            'horas_disponibles': horas_disponibles,
            'horas_generan_ingreso': horas_generan_ingreso,
            'horas_aprobadas': horas_aprobadas,
            'total_registros': total_registros,
            'dias_trabajados': dias_trabajados,
            'productividad': productividad,
            'eficiencia': eficiencia,
            'utilizacion': utilizacion,
            'promedio_por_dia': promedio_por_dia,
            'promedio_productivo_por_dia': promedio_productivo_por_dia,
            'tendencia': tendencia,
            'horas_por_actividad': horas_por_actividad
        })
    
    # Ordenar por productividad
    productividad_tecnicos.sort(key=lambda x: x['productividad'], reverse=True)
    
    # Calcular promedios generales
    if productividad_tecnicos:
        promedio_productividad = sum(item['productividad'] for item in productividad_tecnicos) / len(productividad_tecnicos)
        promedio_eficiencia = sum(item['eficiencia'] for item in productividad_tecnicos) / len(productividad_tecnicos)
        promedio_utilizacion = sum(item['utilizacion'] for item in productividad_tecnicos) / len(productividad_tecnicos)
    else:
        promedio_productividad = promedio_eficiencia = promedio_utilizacion = 0
    
    # Exportar a Excel si se solicita
    if exportar:
        import pandas as pd
        from django.http import HttpResponse
        
        datos = []
        for item in productividad_tecnicos:
            datos.append({
                'Técnico': f"{item['tecnico'].apellido}, {item['tecnico'].nombre}",
                'Email': item['tecnico'].email,
                'Sucursal': item['tecnico'].sucursal.nombre if item['tecnico'].sucursal else 'Sin sucursal',
                'Total Horas': round(item['total_horas'].total_seconds() / 3600, 2),
                'Horas Disponibles': round(item['horas_disponibles'].total_seconds() / 3600, 2),
                'Horas Generan Ingreso': round(item['horas_generan_ingreso'].total_seconds() / 3600, 2),
                'Horas Aprobadas': round(item['horas_aprobadas'].total_seconds() / 3600, 2),
                'Total Registros': item['total_registros'],
                'Días Trabajados': item['dias_trabajados'],
                'Productividad (%)': round(item['productividad'], 2),
                'Eficiencia (%)': round(item['eficiencia'], 2),
                'Utilización (%)': round(item['utilizacion'], 2),
                'Promedio por Día (h)': round(item['promedio_por_dia'].total_seconds() / 3600, 2),
                'Promedio Productivo por Día (h)': round(item['promedio_productivo_por_dia'].total_seconds() / 3600, 2),
                'Tendencia (%)': round(item['tendencia'], 2)
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=productividad_tecnicos.xlsx'
        df.to_excel(response, index=False)
        return response
    
    # Obtener lista de sucursales para el filtro
    from recursosHumanos.models import Sucursal
    sucursales_filtro = Sucursal.objects.filter(activo=True)
    
    context = {
        'titulo': 'Productividad de Técnicos',
        'productividad_tecnicos': productividad_tecnicos,
        'promedio_productividad': promedio_productividad,
        'promedio_eficiencia': promedio_eficiencia,
        'promedio_utilizacion': promedio_utilizacion,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'sucursal_filtro': sucursal,
        'sucursales_filtro': sucursales_filtro,
    }
    
    return render(request, 'reportes/horas/productividad.html', context)

@login_required
def eficiencia_tecnicos(request):
    """Reporte de eficiencia de técnicos"""
    from recursosHumanos.models import RegistroHorasTecnico, Usuario
    from django.db.models import Sum, Count, F, ExpressionWrapper, fields, Q, Avg
    from datetime import datetime, timedelta
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    sucursal = request.GET.get('sucursal')
    exportar = request.GET.get('exportar') == 'excel'
    
    # Filtrar registros de horas
    registros = RegistroHorasTecnico.objects.all()
    
    # Aplicar filtros
    if fecha_inicio:
        registros = registros.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        registros = registros.filter(fecha__lte=fecha_fin)
    if sucursal:
        registros = registros.filter(tecnico__sucursal_id=sucursal)
    
    # Obtener técnicos que tienen registros
    tecnicos_con_registros = registros.values('tecnico').distinct()
    tecnicos = Usuario.objects.filter(
        id__in=tecnicos_con_registros,
        rol='TECNICO'
    ).select_related('sucursal').order_by('sucursal__nombre', 'apellido', 'nombre')
    
    # Calcular métricas de eficiencia por técnico
    eficiencia_tecnicos = []
    for tecnico in tecnicos:
        # Filtrar registros del técnico
        registros_tecnico = registros.filter(tecnico=tecnico)
        
        # Calcular horas por categoría de facturación
        horas_facturables = registros_tecnico.filter(
            tipo_hora__categoria_facturacion='FACTURABLE'
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_no_facturables = registros_tecnico.filter(
            tipo_hora__categoria_facturacion='NO_FACTURABLE'
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        # Calcular horas por disponibilidad
        horas_disponibles = registros_tecnico.filter(
            tipo_hora__disponibilidad='DISPONIBLE'
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_no_disponibles = registros_tecnico.filter(
            tipo_hora__disponibilidad='NO_DISPONIBLE'
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        # Calcular horas por generación de ingreso
        horas_generan_ingreso = registros_tecnico.filter(
            tipo_hora__genera_ingreso='INGRESO'
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_no_generan_ingreso = registros_tecnico.filter(
            tipo_hora__genera_ingreso='NO_INGRESO'
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        # Calcular horas aprobadas vs pendientes
        horas_aprobadas = registros_tecnico.filter(aprobado=True).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_pendientes = registros_tecnico.filter(aprobado=False).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        # Calcular totales
        total_horas = registros_tecnico.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        # Calcular métricas de eficiencia
        total_registros = registros_tecnico.count()
        dias_trabajados = registros_tecnico.values('fecha').distinct().count()
        
        # Eficiencia operacional = (horas facturables / horas totales) * 100
        eficiencia_operacional = 0
        if total_horas.total_seconds() > 0:
            eficiencia_operacional = (horas_facturables.total_seconds() / total_horas.total_seconds()) * 100
        
        # Eficiencia de aprobación = (horas aprobadas / horas totales) * 100
        eficiencia_aprobacion = 0
        if total_horas.total_seconds() > 0:
            eficiencia_aprobacion = (horas_aprobadas.total_seconds() / total_horas.total_seconds()) * 100
        
        # Eficiencia de disponibilidad = (horas disponibles / horas totales) * 100
        eficiencia_disponibilidad = 0
        if total_horas.total_seconds() > 0:
            eficiencia_disponibilidad = (horas_disponibles.total_seconds() / total_horas.total_seconds()) * 100
        
        # Eficiencia de generación de ingreso = (horas que generan ingreso / horas disponibles) * 100
        eficiencia_generacion_ingreso = 0
        if horas_disponibles.total_seconds() > 0:
            eficiencia_generacion_ingreso = (horas_generan_ingreso.total_seconds() / horas_disponibles.total_seconds()) * 100
        
        # Calcular horas por actividad específica
        horas_por_actividad = registros_tecnico.values('tipo_hora__nombre', 'tipo_hora__categoria_facturacion').annotate(
            total_horas=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            ),
            cantidad_registros=Count('id', distinct=True)
        ).order_by('-total_horas')
        
        # Calcular promedio de horas por día
        promedio_por_dia = timedelta(0)
        if dias_trabajados > 0:
            promedio_por_dia = timedelta(seconds=total_horas.total_seconds() / dias_trabajados)
        
        eficiencia_tecnicos.append({
            'tecnico': tecnico,
            'total_horas': total_horas,
            'horas_facturables': horas_facturables,
            'horas_no_facturables': horas_no_facturables,
            'horas_disponibles': horas_disponibles,
            'horas_no_disponibles': horas_no_disponibles,
            'horas_generan_ingreso': horas_generan_ingreso,
            'horas_no_generan_ingreso': horas_no_generan_ingreso,
            'horas_aprobadas': horas_aprobadas,
            'horas_pendientes': horas_pendientes,
            'total_registros': total_registros,
            'dias_trabajados': dias_trabajados,
            'eficiencia_operacional': eficiencia_operacional,
            'eficiencia_aprobacion': eficiencia_aprobacion,
            'eficiencia_disponibilidad': eficiencia_disponibilidad,
            'eficiencia_generacion_ingreso': eficiencia_generacion_ingreso,
            'promedio_por_dia': promedio_por_dia,
            'horas_por_actividad': horas_por_actividad
        })
    
    # Ordenar por eficiencia operacional
    eficiencia_tecnicos.sort(key=lambda x: x['eficiencia_operacional'], reverse=True)
    
    # Calcular promedios generales
    if eficiencia_tecnicos:
        promedio_eficiencia_operacional = sum(item['eficiencia_operacional'] for item in eficiencia_tecnicos) / len(eficiencia_tecnicos)
        promedio_eficiencia_aprobacion = sum(item['eficiencia_aprobacion'] for item in eficiencia_tecnicos) / len(eficiencia_tecnicos)
        promedio_eficiencia_disponibilidad = sum(item['eficiencia_disponibilidad'] for item in eficiencia_tecnicos) / len(eficiencia_tecnicos)
        promedio_eficiencia_generacion = sum(item['eficiencia_generacion_ingreso'] for item in eficiencia_tecnicos) / len(eficiencia_tecnicos)
    else:
        promedio_eficiencia_operacional = promedio_eficiencia_aprobacion = promedio_eficiencia_disponibilidad = promedio_eficiencia_generacion = 0
    
    # Exportar a Excel si se solicita
    if exportar:
        import pandas as pd
        from django.http import HttpResponse
        
        datos = []
        for item in eficiencia_tecnicos:
            datos.append({
                'Técnico': f"{item['tecnico'].apellido}, {item['tecnico'].nombre}",
                'Email': item['tecnico'].email,
                'Sucursal': item['tecnico'].sucursal.nombre if item['tecnico'].sucursal else 'Sin sucursal',
                'Total Horas': round(item['total_horas'].total_seconds() / 3600, 2),
                'Horas Facturables': round(item['horas_facturables'].total_seconds() / 3600, 2),
                'Horas No Facturables': round(item['horas_no_facturables'].total_seconds() / 3600, 2),
                'Horas Disponibles': round(item['horas_disponibles'].total_seconds() / 3600, 2),
                'Horas No Disponibles': round(item['horas_no_disponibles'].total_seconds() / 3600, 2),
                'Horas Generan Ingreso': round(item['horas_generan_ingreso'].total_seconds() / 3600, 2),
                'Horas No Generan Ingreso': round(item['horas_no_generan_ingreso'].total_seconds() / 3600, 2),
                'Horas Aprobadas': round(item['horas_aprobadas'].total_seconds() / 3600, 2),
                'Horas Pendientes': round(item['horas_pendientes'].total_seconds() / 3600, 2),
                'Total Registros': item['total_registros'],
                'Días Trabajados': item['dias_trabajados'],
                'Eficiencia Operacional (%)': round(item['eficiencia_operacional'], 2),
                'Eficiencia Aprobación (%)': round(item['eficiencia_aprobacion'], 2),
                'Eficiencia Disponibilidad (%)': round(item['eficiencia_disponibilidad'], 2),
                'Eficiencia Generación Ingreso (%)': round(item['eficiencia_generacion_ingreso'], 2),
                'Promedio por Día (h)': round(item['promedio_por_dia'].total_seconds() / 3600, 2)
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=eficiencia_tecnicos.xlsx'
        df.to_excel(response, index=False)
        return response
    
    # Obtener lista de sucursales para el filtro
    from recursosHumanos.models import Sucursal
    sucursales_filtro = Sucursal.objects.filter(activo=True)
    
    context = {
        'titulo': 'Eficiencia de Técnicos',
        'eficiencia_tecnicos': eficiencia_tecnicos,
        'promedio_eficiencia_operacional': promedio_eficiencia_operacional,
        'promedio_eficiencia_aprobacion': promedio_eficiencia_aprobacion,
        'promedio_eficiencia_disponibilidad': promedio_eficiencia_disponibilidad,
        'promedio_eficiencia_generacion': promedio_eficiencia_generacion,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'sucursal_filtro': sucursal,
        'sucursales_filtro': sucursales_filtro,
    }
    
    return render(request, 'reportes/horas/eficiencia.html', context)

@login_required
def desempeno_tecnicos(request):
    """Reporte de desempeño de técnicos"""
    from recursosHumanos.models import RegistroHorasTecnico, Usuario
    from django.db.models import Sum, Count, F, ExpressionWrapper, fields, Q, Avg
    from datetime import datetime, timedelta
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    sucursal = request.GET.get('sucursal')
    exportar = request.GET.get('exportar') == 'excel'
    
    # Filtrar registros de horas
    registros = RegistroHorasTecnico.objects.all()
    
    # Aplicar filtros
    if fecha_inicio:
        registros = registros.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        registros = registros.filter(fecha__lte=fecha_fin)
    if sucursal:
        registros = registros.filter(tecnico__sucursal_id=sucursal)
    
    # Obtener técnicos que tienen registros
    tecnicos_con_registros = registros.values('tecnico').distinct()
    tecnicos = Usuario.objects.filter(
        id__in=tecnicos_con_registros,
        rol='TECNICO'
    ).select_related('sucursal').order_by('sucursal__nombre', 'apellido', 'nombre')
    
    # Calcular métricas de desempeño por técnico
    desempeno_tecnicos = []
    for tecnico in tecnicos:
        # Filtrar registros del técnico
        registros_tecnico = registros.filter(tecnico=tecnico)
        
        # Calcular métricas básicas
        total_horas = registros_tecnico.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_disponibles = registros_tecnico.filter(
            tipo_hora__disponibilidad='DISPONIBLE'
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_generan_ingreso = registros_tecnico.filter(
            tipo_hora__disponibilidad='DISPONIBLE',
            tipo_hora__genera_ingreso='INGRESO'
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        horas_aprobadas = registros_tecnico.filter(aprobado=True).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            )
        )['total'] or timedelta(0)
        
        # Calcular métricas de desempeño
        total_registros = registros_tecnico.count()
        dias_trabajados = registros_tecnico.values('fecha').distinct().count()
        
        # Calcular puntuaciones de desempeño (0-100)
        
        # 1. Puntuación de Productividad (30% del total)
        productividad = 0
        if horas_disponibles.total_seconds() > 0:
            productividad = (horas_generan_ingreso.total_seconds() / horas_disponibles.total_seconds()) * 100
        puntuacion_productividad = min(productividad, 100) * 0.30
        
        # 2. Puntuación de Aprobación (25% del total)
        aprobacion = 0
        if total_horas.total_seconds() > 0:
            aprobacion = (horas_aprobadas.total_seconds() / total_horas.total_seconds()) * 100
        puntuacion_aprobacion = min(aprobacion, 100) * 0.25
        
        # 3. Puntuación de Consistencia (20% del total)
        # Basada en la regularidad de trabajo (días trabajados vs días totales del período)
        if fecha_inicio and fecha_fin:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            dias_periodo = (fecha_fin_dt - fecha_inicio_dt).days + 1
            consistencia = (dias_trabajados / dias_periodo) * 100 if dias_periodo > 0 else 0
        else:
            consistencia = 100  # Si no hay filtro de fechas, asumir consistencia perfecta
        puntuacion_consistencia = min(consistencia, 100) * 0.20
        
        # 4. Puntuación de Eficiencia (15% del total)
        eficiencia = 0
        if total_horas.total_seconds() > 0:
            eficiencia = (horas_disponibles.total_seconds() / total_horas.total_seconds()) * 100
        puntuacion_eficiencia = min(eficiencia, 100) * 0.15
        
        # 5. Puntuación de Volumen (10% del total)
        # Basada en el promedio de horas por día (máximo 8 horas = 100%)
        promedio_por_dia = timedelta(0)
        if dias_trabajados > 0:
            promedio_por_dia = timedelta(seconds=total_horas.total_seconds() / dias_trabajados)
        
        horas_por_dia = promedio_por_dia.total_seconds() / 3600
        volumen = min((horas_por_dia / 8) * 100, 100)  # Máximo 8 horas = 100%
        puntuacion_volumen = volumen * 0.10
        
        # Calcular puntuación total
        puntuacion_total = (
            puntuacion_productividad + 
            puntuacion_aprobacion + 
            puntuacion_consistencia + 
            puntuacion_eficiencia + 
            puntuacion_volumen
        )
        
        # Determinar nivel de desempeño
        if puntuacion_total >= 90:
            nivel_desempeno = "Excelente"
            color_nivel = "success"
        elif puntuacion_total >= 80:
            nivel_desempeno = "Muy Bueno"
            color_nivel = "info"
        elif puntuacion_total >= 70:
            nivel_desempeno = "Bueno"
            color_nivel = "primary"
        elif puntuacion_total >= 60:
            nivel_desempeno = "Regular"
            color_nivel = "warning"
        else:
            nivel_desempeno = "Necesita Mejora"
            color_nivel = "danger"
        
        # Calcular tendencia (comparar con período anterior)
        tendencia = 0
        if fecha_inicio and fecha_fin:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            duracion_periodo = (fecha_fin_dt - fecha_inicio_dt).days
            
            fecha_inicio_anterior = fecha_inicio_dt - timedelta(days=duracion_periodo)
            fecha_fin_anterior = fecha_inicio_dt - timedelta(days=1)
            
            registros_anterior = RegistroHorasTecnico.objects.filter(
                tecnico=tecnico,
                fecha__range=[fecha_inicio_anterior, fecha_fin_anterior]
            )
            
            horas_anterior = registros_anterior.aggregate(
                total=Sum(
                    ExpressionWrapper(
                        F('hora_fin') - F('hora_inicio'),
                        output_field=fields.DurationField()
                    )
                )
            )['total'] or timedelta(0)
            
            if horas_anterior.total_seconds() > 0:
                tendencia = ((total_horas.total_seconds() - horas_anterior.total_seconds()) / horas_anterior.total_seconds()) * 100
        
        # Calcular horas por actividad
        horas_por_actividad = registros_tecnico.values('tipo_hora__nombre').annotate(
            total_horas=Sum(
                ExpressionWrapper(
                    F('hora_fin') - F('hora_inicio'),
                    output_field=fields.DurationField()
                )
            ),
            cantidad_registros=Count('id', distinct=True)
        ).order_by('-total_horas')[:5]  # Top 5 actividades
        
        desempeno_tecnicos.append({
            'tecnico': tecnico,
            'total_horas': total_horas,
            'horas_disponibles': horas_disponibles,
            'horas_generan_ingreso': horas_generan_ingreso,
            'horas_aprobadas': horas_aprobadas,
            'total_registros': total_registros,
            'dias_trabajados': dias_trabajados,
            'productividad': productividad,
            'aprobacion': aprobacion,
            'consistencia': consistencia,
            'eficiencia': eficiencia,
            'volumen': volumen,
            'promedio_por_dia': promedio_por_dia,
            'puntuacion_productividad': puntuacion_productividad,
            'puntuacion_aprobacion': puntuacion_aprobacion,
            'puntuacion_consistencia': puntuacion_consistencia,
            'puntuacion_eficiencia': puntuacion_eficiencia,
            'puntuacion_volumen': puntuacion_volumen,
            'puntuacion_total': puntuacion_total,
            'nivel_desempeno': nivel_desempeno,
            'color_nivel': color_nivel,
            'tendencia': tendencia,
            'horas_por_actividad': horas_por_actividad
        })
    
    # Ordenar por puntuación total
    desempeno_tecnicos.sort(key=lambda x: x['puntuacion_total'], reverse=True)
    
    # Calcular promedios generales
    if desempeno_tecnicos:
        promedio_puntuacion_total = sum(item['puntuacion_total'] for item in desempeno_tecnicos) / len(desempeno_tecnicos)
        promedio_productividad = sum(item['productividad'] for item in desempeno_tecnicos) / len(desempeno_tecnicos)
        promedio_aprobacion = sum(item['aprobacion'] for item in desempeno_tecnicos) / len(desempeno_tecnicos)
        promedio_consistencia = sum(item['consistencia'] for item in desempeno_tecnicos) / len(desempeno_tecnicos)
    else:
        promedio_puntuacion_total = promedio_productividad = promedio_aprobacion = promedio_consistencia = 0
    
    # Exportar a Excel si se solicita
    if exportar:
        import pandas as pd
        from django.http import HttpResponse
        
        datos = []
        for item in desempeno_tecnicos:
            datos.append({
                'Técnico': f"{item['tecnico'].apellido}, {item['tecnico'].nombre}",
                'Email': item['tecnico'].email,
                'Sucursal': item['tecnico'].sucursal.nombre if item['tecnico'].sucursal else 'Sin sucursal',
                'Total Horas': round(item['total_horas'].total_seconds() / 3600, 2),
                'Horas Disponibles': round(item['horas_disponibles'].total_seconds() / 3600, 2),
                'Horas Generan Ingreso': round(item['horas_generan_ingreso'].total_seconds() / 3600, 2),
                'Horas Aprobadas': round(item['horas_aprobadas'].total_seconds() / 3600, 2),
                'Total Registros': item['total_registros'],
                'Días Trabajados': item['dias_trabajados'],
                'Productividad (%)': round(item['productividad'], 2),
                'Aprobación (%)': round(item['aprobacion'], 2),
                'Consistencia (%)': round(item['consistencia'], 2),
                'Eficiencia (%)': round(item['eficiencia'], 2),
                'Volumen (%)': round(item['volumen'], 2),
                'Promedio por Día (h)': round(item['promedio_por_dia'].total_seconds() / 3600, 2),
                'Puntuación Total': round(item['puntuacion_total'], 2),
                'Nivel de Desempeño': item['nivel_desempeno'],
                'Tendencia (%)': round(item['tendencia'], 2)
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=desempeno_tecnicos.xlsx'
        df.to_excel(response, index=False)
        return response
    
    # Obtener lista de sucursales para el filtro
    from recursosHumanos.models import Sucursal
    sucursales_filtro = Sucursal.objects.filter(activo=True)
    
    context = {
        'titulo': 'Desempeño de Técnicos',
        'desempeno_tecnicos': desempeno_tecnicos,
        'promedio_puntuacion_total': promedio_puntuacion_total,
        'promedio_productividad': promedio_productividad,
        'promedio_aprobacion': promedio_aprobacion,
        'promedio_consistencia': promedio_consistencia,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'sucursal_filtro': sucursal,
        'sucursales_filtro': sucursales_filtro,
    }
    
    return render(request, 'reportes/horas/desempeno.html', context)

# ===== REPORTES DE SERVICIOS =====

@login_required
def reportes_servicios(request):
    """Dashboard de reportes de servicios"""
    return render(request, 'reportes/servicios/dashboard.html')

@login_required
def preordenes_estadisticas(request):
    """Estadísticas de preórdenes"""
    from gestionDeTaller.models import PreOrden
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    sucursal = request.GET.get('sucursal')
    exportar = request.GET.get('exportar') == 'excel'
    
    # Filtrar preórdenes
    preordenes = PreOrden.objects.all()
    
    # Aplicar filtros
    if fecha_inicio:
        preordenes = preordenes.filter(fecha_creacion__gte=fecha_inicio)
    if fecha_fin:
        preordenes = preordenes.filter(fecha_creacion__lte=fecha_fin)
    if sucursal:
        preordenes = preordenes.filter(sucursal_id=sucursal)
    
    # Calcular estadísticas generales
    total_preordenes = preordenes.count()
    preordenes_activas = preordenes.filter(activo=True).count()
    preordenes_inactivas = preordenes.filter(activo=False).count()
    
    # Estadísticas por estado de servicio
    preordenes_con_servicio = preordenes.filter(servicio__isnull=False).count()
    preordenes_sin_servicio = preordenes.filter(servicio__isnull=True).count()
    
    # Estadísticas por tipo de trabajo
    tipos_trabajo = preordenes.values('tipo_trabajo').annotate(
        cantidad=Count('numero')
    ).order_by('-cantidad')
    
    # Estadísticas por clasificación
    clasificaciones = preordenes.values('clasificacion').annotate(
        cantidad=Count('numero')
    ).order_by('-cantidad')
    
    # Estadísticas por sucursal
    sucursales = preordenes.values('sucursal__nombre').annotate(
        cantidad=Count('numero')
    ).order_by('-cantidad')
    
    # Estadísticas por mes (últimos 12 meses)
    meses = []
    for i in range(12):
        fecha = datetime.now() - timedelta(days=30*i)
        mes = fecha.strftime('%Y-%m')
        cantidad = preordenes.filter(
            fecha_creacion__year=fecha.year,
            fecha_creacion__month=fecha.month
        ).count()
        meses.append({'mes': mes, 'cantidad': cantidad})
    
    # Exportar a Excel si se solicita
    if exportar:
        import pandas as pd
        from django.http import HttpResponse
        
        # Crear datos para Excel
        datos = []
        for preorden in preordenes.select_related('cliente', 'equipo', 'sucursal', 'creado_por'):
            datos.append({
                'ID': preorden.numero,
                'Fecha Creación': preorden.fecha_creacion.strftime('%d/%m/%Y'),
                'Cliente': preorden.cliente.razon_social,
                'Equipo': f"{preorden.equipo.modelo} - {preorden.equipo.numero_serie}",
                'Sucursal': preorden.sucursal.nombre,
                'Tipo Trabajo': preorden.get_tipo_trabajo_display(),
                'Clasificación': preorden.get_clasificacion_display(),
                'Fecha Estimada': preorden.fecha_estimada.strftime('%d/%m/%Y'),
                'Creado por': f"{preorden.creado_por.apellido}, {preorden.creado_por.nombre}",
                'Activo': 'Sí' if preorden.activo else 'No',
                'Tiene Servicio': 'Sí' if hasattr(preorden, 'servicio') else 'No'
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=estadisticas_preordenes.xlsx'
        df.to_excel(response, index=False)
        return response
    
    # Obtener lista de sucursales para el filtro
    from recursosHumanos.models import Sucursal
    sucursales_filtro = Sucursal.objects.filter(activo=True)
    
    context = {
        'total_preordenes': total_preordenes,
        'preordenes_activas': preordenes_activas,
        'preordenes_inactivas': preordenes_inactivas,
        'preordenes_con_servicio': preordenes_con_servicio,
        'preordenes_sin_servicio': preordenes_sin_servicio,
        'tipos_trabajo': tipos_trabajo,
        'clasificaciones': clasificaciones,
        'sucursales': sucursales,
        'meses': meses,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'sucursal_filtro': sucursal,
        'sucursales_filtro': sucursales_filtro,
    }
    
    return render(request, 'reportes/servicios/preordenes.html', context)

@login_required
def servicios_programados(request):
    """Reporte de servicios programados"""
    from gestionDeTaller.models import Servicio
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    sucursal = request.GET.get('sucursal')
    exportar = request.GET.get('exportar') == 'excel'
    
    # Filtrar servicios programados
    servicios = Servicio.objects.filter(
        estado='PROGRAMADO'
    ).select_related(
        'preorden__cliente',
        'preorden__equipo',
        'preorden__sucursal'
    ).prefetch_related('preorden__tecnicos')
    
    # Aplicar filtros
    if fecha_inicio:
        servicios = servicios.filter(fecha_servicio__gte=fecha_inicio)
    if fecha_fin:
        servicios = servicios.filter(fecha_servicio__lte=fecha_fin)
    if sucursal:
        servicios = servicios.filter(preorden__sucursal_id=sucursal)
    
    # Ordenar por fecha de servicio
    servicios = servicios.order_by('fecha_servicio')
    
    # Exportar a Excel si se solicita
    if exportar:
        import pandas as pd
        from django.http import HttpResponse
        
        datos = []
        for servicio in servicios:
            tecnicos = ', '.join([f"{t.apellido}, {t.nombre}" for t in servicio.preorden.tecnicos.all()])
            datos.append({
                'ID': servicio.id,
                'Fecha Servicio': servicio.fecha_servicio.strftime('%d/%m/%Y'),
                'Cliente': servicio.preorden.cliente.razon_social,
                'Equipo': f"{servicio.preorden.equipo.modelo} - {servicio.preorden.equipo.numero_serie}",
                'Sucursal': servicio.preorden.sucursal.nombre,
                'Técnicos': tecnicos,
                'Tipo Trabajo': servicio.get_trabajo_display(),
                'Orden Servicio': servicio.orden_servicio or '',
                'Prioridad': servicio.get_prioridad_display(),
                'Observaciones': servicio.observaciones or ''
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=servicios_programados.xlsx'
        df.to_excel(response, index=False)
        return response
    
    # Paginación
    paginator = Paginator(servicios, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calcular estadísticas
    total_servicios = servicios.count()
    servicios_hoy = servicios.filter(fecha_servicio=datetime.now().date()).count()
    servicios_semana = servicios.filter(
        fecha_servicio__gte=datetime.now().date(),
        fecha_servicio__lte=datetime.now().date() + timedelta(days=7)
    ).count()
    
    # Obtener lista de sucursales para el filtro
    from recursosHumanos.models import Sucursal
    sucursales_filtro = Sucursal.objects.filter(activo=True)
    
    context = {
        'page_obj': page_obj,
        'total_servicios': total_servicios,
        'servicios_hoy': servicios_hoy,
        'servicios_semana': servicios_semana,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'sucursal_filtro': sucursal,
        'sucursales_filtro': sucursales_filtro,
    }
    
    return render(request, 'reportes/servicios/programados.html', context)

@login_required
def servicios_en_proceso(request):
    """Reporte de servicios en proceso"""
    from gestionDeTaller.models import Servicio
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    sucursal = request.GET.get('sucursal')
    exportar = request.GET.get('exportar') == 'excel'
    
    # Filtrar servicios en proceso
    servicios = Servicio.objects.filter(
        estado='EN_PROCESO'
    ).select_related(
        'preorden__cliente',
        'preorden__equipo',
        'preorden__sucursal'
    ).prefetch_related('preorden__tecnicos')
    
    # Aplicar filtros
    if fecha_inicio:
        servicios = servicios.filter(fecha_servicio__gte=fecha_inicio)
    if fecha_fin:
        servicios = servicios.filter(fecha_servicio__lte=fecha_fin)
    if sucursal:
        servicios = servicios.filter(preorden__sucursal_id=sucursal)
    
    # Ordenar por fecha de servicio
    servicios = servicios.order_by('fecha_servicio')
    
    # Exportar a Excel si se solicita
    if exportar:
        import pandas as pd
        from django.http import HttpResponse
        
        datos = []
        for servicio in servicios:
            tecnicos = ', '.join([f"{t.apellido}, {t.nombre}" for t in servicio.preorden.tecnicos.all()])
            datos.append({
                'ID': servicio.id,
                'Fecha Servicio': servicio.fecha_servicio.strftime('%d/%m/%Y'),
                'Cliente': servicio.preorden.cliente.razon_social,
                'Equipo': f"{servicio.preorden.equipo.modelo} - {servicio.preorden.equipo.numero_serie}",
                'Sucursal': servicio.preorden.sucursal.nombre,
                'Técnicos': tecnicos,
                'Tipo Trabajo': servicio.get_trabajo_display(),
                'Orden Servicio': servicio.orden_servicio or '',
                'Observaciones': servicio.observaciones or ''
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=servicios_en_proceso.xlsx'
        df.to_excel(response, index=False)
        return response
    
    # Paginación
    paginator = Paginator(servicios, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calcular estadísticas
    total_servicios = servicios.count()
    
    # Obtener lista de sucursales para el filtro
    from recursosHumanos.models import Sucursal
    sucursales_filtro = Sucursal.objects.filter(activo=True)
    
    context = {
        'page_obj': page_obj,
        'total_servicios': total_servicios,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'sucursal_filtro': sucursal,
        'sucursales_filtro': sucursales_filtro,
    }
    
    return render(request, 'reportes/servicios/en_proceso.html', context)

@login_required
def servicios_completados(request):
    """Reporte de servicios completados"""
    from gestionDeTaller.models import Servicio
    from django.core.paginator import Paginator
    from django.db.models import Q, Sum, F
    from decimal import Decimal
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    sucursal = request.GET.get('sucursal')
    exportar = request.GET.get('exportar') == 'excel'
    
    # Filtrar servicios completados
    servicios = Servicio.objects.filter(
        estado='COMPLETADO'
    ).select_related(
        'preorden__cliente',
        'preorden__equipo',
        'preorden__sucursal'
    ).prefetch_related('preorden__tecnicos', 'gastos', 'repuestos')
    
    # Aplicar filtros
    if fecha_inicio:
        servicios = servicios.filter(fecha_servicio__gte=fecha_inicio)
    if fecha_fin:
        servicios = servicios.filter(fecha_servicio__lte=fecha_fin)
    if sucursal:
        servicios = servicios.filter(preorden__sucursal_id=sucursal)
    
    # Ordenar por fecha de servicio
    servicios = servicios.order_by('-fecha_servicio')
    
    # Exportar a Excel si se solicita
    if exportar:
        import pandas as pd
        from django.http import HttpResponse
        
        datos = []
        for servicio in servicios:
            tecnicos = ', '.join([f"{t.apellido}, {t.nombre}" for t in servicio.preorden.tecnicos.all()])
            total_gastos = servicio.gastos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
            total_repuestos = servicio.repuestos.aggregate(total=Sum(F('precio_unitario') * F('cantidad')))['total'] or Decimal('0.00')
            valor_total = (servicio.valor_mano_obra or Decimal('0.00')) + total_gastos + total_repuestos
            
            datos.append({
                'ID': servicio.id,
                'Fecha Servicio': servicio.fecha_servicio.strftime('%d/%m/%Y'),
                'Cliente': servicio.preorden.cliente.razon_social,
                'Equipo': f"{servicio.preorden.equipo.modelo} - {servicio.preorden.equipo.numero_serie}",
                'Sucursal': servicio.preorden.sucursal.nombre,
                'Técnicos': tecnicos,
                'Tipo Trabajo': servicio.get_trabajo_display(),
                'Mano de Obra': float(servicio.valor_mano_obra or 0),
                'Gastos': float(total_gastos),
                'Repuestos': float(total_repuestos),
                'Total': float(valor_total)
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=servicios_completados.xlsx'
        df.to_excel(response, index=False)
        return response
    
    # Paginación
    paginator = Paginator(servicios, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calcular estadísticas
    total_servicios = servicios.count()
    total_mano_obra = servicios.aggregate(total=Sum('valor_mano_obra'))['total'] or Decimal('0.00')
    total_gastos = calcular_gastos_servicios(servicios)
    total_repuestos = calcular_repuestos_servicios(servicios)
    valor_total = total_mano_obra + total_gastos + total_repuestos
    
    # Obtener lista de sucursales para el filtro
    from recursosHumanos.models import Sucursal
    sucursales_filtro = Sucursal.objects.filter(activo=True)
    
    context = {
        'page_obj': page_obj,
        'total_servicios': total_servicios,
        'total_mano_obra': total_mano_obra,
        'total_gastos': total_gastos,
        'total_repuestos': total_repuestos,
        'valor_total': valor_total,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'sucursal_filtro': sucursal,
        'sucursales_filtro': sucursales_filtro,
    }
    
    return render(request, 'reportes/servicios/completados.html', context)

@login_required
def tiempo_promedio_servicios(request):
    """Reporte de tiempo promedio de servicios"""
    from gestionDeTaller.models import Servicio
    from django.db.models import Avg, Count, F, ExpressionWrapper, fields, Case, When, Value
    from datetime import datetime, timedelta
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    sucursal = request.GET.get('sucursal')
    exportar = request.GET.get('exportar') == 'excel'
    
    # Filtrar servicios completados
    servicios = Servicio.objects.filter(
        estado='COMPLETADO'
    ).select_related(
        'preorden__sucursal'
    ).prefetch_related('preorden__tecnicos')
    
    # Aplicar filtros
    if fecha_inicio:
        servicios = servicios.filter(fecha_servicio__gte=fecha_inicio)
    if fecha_fin:
        servicios = servicios.filter(fecha_servicio__lte=fecha_fin)
    if sucursal:
        servicios = servicios.filter(preorden__sucursal_id=sucursal)
    
    # Calcular estadísticas generales
    total_servicios = servicios.count()
    
    # Calcular tiempo promedio desde creación hasta fecha de servicio (solo valores positivos)
    tiempo_por_trabajo = servicios.values('trabajo').annotate(
        cantidad=Count('id', distinct=True),
        tiempo_promedio=Avg(
            Case(
                When(
                    fecha_servicio__gt=F('fecha_creacion__date'),
                    then=ExpressionWrapper(
                        F('fecha_servicio') - F('fecha_creacion__date'),
                        output_field=fields.DurationField()
                    )
                ),
                default=Value(timedelta(0))
            )
        )
    ).order_by('-cantidad')
    
    # Tiempo promedio por sucursal
    tiempo_por_sucursal = servicios.values('preorden__sucursal__nombre').annotate(
        cantidad=Count('id', distinct=True),
        tiempo_promedio=Avg(
            Case(
                When(
                    fecha_servicio__gt=F('fecha_creacion__date'),
                    then=ExpressionWrapper(
                        F('fecha_servicio') - F('fecha_creacion__date'),
                        output_field=fields.DurationField()
                    )
                ),
                default=Value(timedelta(0))
            )
        )
    ).order_by('-cantidad')
    
    # Tiempo promedio por técnico
    tiempo_por_tecnico = []
    tecnicos_unicos = set()
    
    for servicio in servicios.prefetch_related('preorden__tecnicos'):
        for tecnico in servicio.preorden.tecnicos.all():
            tecnicos_unicos.add(tecnico.id)
    
    for tecnico_id in tecnicos_unicos:
        tecnico_servicios = servicios.filter(preorden__tecnicos__id=tecnico_id)
        tecnico = tecnico_servicios.first().preorden.tecnicos.get(id=tecnico_id)
        
        cantidad = tecnico_servicios.count()
        tiempo_promedio = tecnico_servicios.aggregate(
            promedio=Avg(
                Case(
                    When(
                        fecha_servicio__gt=F('fecha_creacion__date'),
                        then=ExpressionWrapper(
                            F('fecha_servicio') - F('fecha_creacion__date'),
                            output_field=fields.DurationField()
                        )
                    ),
                    default=Value(timedelta(0))
                )
            )
        )['promedio'] or timedelta(0)
        
        tiempo_por_tecnico.append({
            'tecnico': tecnico,
            'cantidad': cantidad,
            'tiempo_promedio': tiempo_promedio
        })
    
    # Ordenar por cantidad de servicios
    tiempo_por_tecnico.sort(key=lambda x: x['cantidad'], reverse=True)
    
    # Tiempo promedio general
    tiempo_promedio_general = servicios.aggregate(
        promedio=Avg(
            Case(
                When(
                    fecha_servicio__gt=F('fecha_creacion__date'),
                    then=ExpressionWrapper(
                        F('fecha_servicio') - F('fecha_creacion__date'),
                        output_field=fields.DurationField()
                    )
                ),
                default=Value(timedelta(0))
            )
        )
    )['promedio'] or timedelta(0)
    
    # Exportar a Excel si se solicita
    if exportar:
        import pandas as pd
        from django.http import HttpResponse
        
        datos = []
        for servicio in servicios:
            tecnicos = ', '.join([f"{t.apellido}, {t.nombre}" for t in servicio.preorden.tecnicos.all()])
            duracion = (servicio.fecha_servicio - servicio.fecha_creacion.date()).days
            datos.append({
                'ID': servicio.id,
                'Fecha': servicio.fecha_servicio.strftime('%d/%m/%Y'),
                'Sucursal': servicio.preorden.sucursal.nombre,
                'Técnicos': tecnicos,
                'Tipo Trabajo': servicio.get_trabajo_display(),
                'Duración (días)': duracion,
                'Orden Servicio': servicio.orden_servicio or ''
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=tiempo_promedio_servicios.xlsx'
        df.to_excel(response, index=False)
        return response
    
    # Obtener lista de sucursales para el filtro
    from recursosHumanos.models import Sucursal
    sucursales_filtro = Sucursal.objects.filter(activo=True)
    
    context = {
        'total_servicios': total_servicios,
        'tiempo_promedio_general': tiempo_promedio_general,
        'tiempo_por_trabajo': tiempo_por_trabajo,
        'tiempo_por_sucursal': tiempo_por_sucursal,
        'tiempo_por_tecnico': tiempo_por_tecnico,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'sucursal_filtro': sucursal,
        'sucursales_filtro': sucursales_filtro,
    }
    
    return render(request, 'reportes/servicios/tiempo_promedio.html', context)

@login_required
def servicios_por_sucursal(request):
    """Reporte de servicios por sucursal"""
    from gestionDeTaller.models import Servicio
    from django.db.models import Count, Sum, F
    from decimal import Decimal
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    exportar = request.GET.get('exportar') == 'excel'
    
    # Filtrar servicios - solo considerar servicios completados o facturados para cálculos financieros
    servicios = Servicio.objects.all()
    servicios_financieros = Servicio.objects.filter(
        estado__in=['COMPLETADO', 'A_FACTURAR']
    )
    
    # Aplicar filtros
    if fecha_inicio:
        servicios = servicios.filter(fecha_servicio__gte=fecha_inicio)
        servicios_financieros = servicios_financieros.filter(fecha_servicio__gte=fecha_inicio)
    if fecha_fin:
        servicios = servicios.filter(fecha_servicio__lte=fecha_fin)
        servicios_financieros = servicios_financieros.filter(fecha_servicio__lte=fecha_fin)
    
    # Agrupar por sucursal - usar servicios_financieros para cálculos de dinero
    servicios_por_sucursal = servicios.values('preorden__sucursal__nombre').annotate(
        total_servicios=Count('id', distinct=True),
        programados=Count('id', filter=Q(estado='PROGRAMADO'), distinct=True),
        en_proceso=Count('id', filter=Q(estado='EN_PROCESO'), distinct=True),
        completados=Count('id', filter=Q(estado='COMPLETADO'), distinct=True),
        a_facturar=Count('id', filter=Q(estado='A_FACTURAR'), distinct=True),
        # Usar servicios_financieros para cálculos de dinero
        total_mano_obra=Sum('valor_mano_obra', filter=Q(estado__in=['COMPLETADO', 'A_FACTURAR'])),
        total_gastos=Sum('gastos__monto', filter=Q(estado__in=['COMPLETADO', 'A_FACTURAR'])) + 
                     Sum('gastos_asistencia_simplificados__monto', filter=Q(estado__in=['COMPLETADO', 'A_FACTURAR'])) +
                     Sum('gastos_insumos_terceros__monto', filter=Q(estado__in=['COMPLETADO', 'A_FACTURAR'])),
        total_repuestos=Sum(F('repuestos__precio_unitario') * F('repuestos__cantidad'), filter=Q(estado__in=['COMPLETADO', 'A_FACTURAR'])) +
                       Sum('venta_repuestos_simplificada__monto_total', filter=Q(estado__in=['COMPLETADO', 'A_FACTURAR']))
    ).order_by('-total_servicios')
    
    # Calcular totales usando servicios (no servicios_financieros para contar)
    total_servicios = servicios.count()
    
    # Calcular totales por estado para verificación
    total_programados = servicios.filter(estado='PROGRAMADO').count()
    total_en_proceso = servicios.filter(estado='EN_PROCESO').count()
    total_espera_repuestos = servicios.filter(estado='ESPERA_REPUESTOS').count()
    total_a_facturar = servicios.filter(estado='A_FACTURAR').count()
    total_completados = servicios.filter(estado='COMPLETADO').count()
    
    # Calcular servicios sin sucursal correctamente
    servicios_sin_sucursal = servicios.filter(preorden__sucursal__isnull=True).count()
    
    # Calcular totales financieros usando servicios_financieros
    total_mano_obra = servicios_financieros.aggregate(total=Sum('valor_mano_obra'))['total'] or Decimal('0.00')
    total_gastos = calcular_gastos_servicios(servicios_financieros)
    total_repuestos = calcular_repuestos_servicios(servicios_financieros)
    valor_total = total_mano_obra + total_gastos + total_repuestos
    
    # Exportar a Excel si se solicita
    if exportar:
        import pandas as pd
        from django.http import HttpResponse
        
        datos = []
        for item in servicios_por_sucursal:
            total_item = (item['total_mano_obra'] or Decimal('0.00')) + (item['total_gastos'] or Decimal('0.00')) + (item['total_repuestos'] or Decimal('0.00'))
            datos.append({
                'Sucursal': item['preorden__sucursal__nombre'],
                'Total Servicios': item['total_servicios'],
                'Programados': item['programados'],
                'En Proceso': item['en_proceso'],
                'Completados': item['completados'],
                'A Facturar': item['a_facturar'],
                'Mano de Obra': float(item['total_mano_obra'] or 0),
                'Gastos': float(item['total_gastos'] or 0),
                'Repuestos': float(item['total_repuestos'] or 0),
                'Total': float(total_item)
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=servicios_por_sucursal.xlsx'
        df.to_excel(response, index=False)
        return response
    
    context = {
        'servicios_por_sucursal': servicios_por_sucursal,
        'total_servicios': total_servicios,
        'servicios_sin_sucursal': servicios_sin_sucursal,
        'total_mano_obra': total_mano_obra,
        'total_gastos': total_gastos,
        'total_repuestos': total_repuestos,
        'valor_total': valor_total,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }
    
    return render(request, 'reportes/servicios/por_sucursal.html', context)

@login_required
def servicios_por_tecnico(request):
    """Reporte de servicios por técnico"""
    from gestionDeTaller.models import Servicio
    from django.db.models import Count, Sum, F
    from decimal import Decimal
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    exportar = request.GET.get('exportar') == 'excel'
    
    # Filtrar servicios - solo considerar servicios completados o facturados para cálculos financieros
    servicios = Servicio.objects.all()
    servicios_financieros = Servicio.objects.filter(
        estado__in=['COMPLETADO', 'A_FACTURAR']
    )
    
    # Aplicar filtros
    if fecha_inicio:
        servicios = servicios.filter(fecha_servicio__gte=fecha_inicio)
        servicios_financieros = servicios_financieros.filter(fecha_servicio__gte=fecha_inicio)
    if fecha_fin:
        servicios = servicios.filter(fecha_servicio__lte=fecha_fin)
        servicios_financieros = servicios_financieros.filter(fecha_servicio__lte=fecha_fin)
    
    # Agrupar por técnico (usando ManyToMany)
    servicios_por_tecnico = []
    tecnicos_unicos = set()
    
    for servicio in servicios.prefetch_related('preorden__tecnicos'):
        for tecnico in servicio.preorden.tecnicos.all():
            tecnicos_unicos.add(tecnico.id)
    
    for tecnico_id in tecnicos_unicos:
        tecnico_servicios = servicios.filter(preorden__tecnicos__id=tecnico_id)
        tecnico_servicios_financieros = servicios_financieros.filter(preorden__tecnicos__id=tecnico_id)
        tecnico = tecnico_servicios.first().preorden.tecnicos.get(id=tecnico_id)
        
        total_servicios = tecnico_servicios.count()
        programados = tecnico_servicios.filter(estado='PROGRAMADO').count()
        en_proceso = tecnico_servicios.filter(estado='EN_PROCESO').count()
        completados = tecnico_servicios.filter(estado='COMPLETADO').count()
        a_facturar = tecnico_servicios.filter(estado='A_FACTURAR').count()
        
        # Usar servicios_financieros para cálculos de dinero
        total_mano_obra = tecnico_servicios_financieros.aggregate(total=Sum('valor_mano_obra'))['total'] or Decimal('0.00')
        total_gastos = calcular_gastos_servicios(tecnico_servicios_financieros)
        total_repuestos = calcular_repuestos_servicios(tecnico_servicios_financieros)
        
        servicios_por_tecnico.append({
            'tecnico': tecnico,
            'total_servicios': total_servicios,
            'programados': programados,
            'en_proceso': en_proceso,
            'completados': completados,
            'a_facturar': a_facturar,
            'total_mano_obra': total_mano_obra,
            'total_gastos': total_gastos,
            'total_repuestos': total_repuestos,
        })
    
    # Ordenar por total de servicios
    servicios_por_tecnico.sort(key=lambda x: x['total_servicios'], reverse=True)
    
    # Calcular totales usando servicios_financieros
    total_servicios = servicios.count()
    total_mano_obra = servicios_financieros.aggregate(total=Sum('valor_mano_obra'))['total'] or Decimal('0.00')
    total_gastos = calcular_gastos_servicios(servicios_financieros)
    total_repuestos = calcular_repuestos_servicios(servicios_financieros)
    valor_total = total_mano_obra + total_gastos + total_repuestos
    
    # Exportar a Excel si se solicita
    if exportar:
        import pandas as pd
        from django.http import HttpResponse
        
        datos = []
        for item in servicios_por_tecnico:
            total_item = item['total_mano_obra'] + item['total_gastos'] + item['total_repuestos']
            datos.append({
                'Técnico': f"{item['tecnico'].apellido}, {item['tecnico'].nombre}",
                'Total Servicios': item['total_servicios'],
                'Programados': item['programados'],
                'En Proceso': item['en_proceso'],
                'Completados': item['completados'],
                'A Facturar': item['a_facturar'],
                'Mano de Obra': float(item['total_mano_obra']),
                'Gastos': float(item['total_gastos']),
                'Repuestos': float(item['total_repuestos']),
                'Total': float(total_item)
            })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=servicios_por_tecnico.xlsx'
        df.to_excel(response, index=False)
        return response
    
    context = {
        'servicios_por_tecnico': servicios_por_tecnico,
        'total_servicios': total_servicios,
        'total_mano_obra': total_mano_obra,
        'total_gastos': total_gastos,
        'total_repuestos': total_repuestos,
        'valor_total': valor_total,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }
    
    return render(request, 'reportes/servicios/por_tecnico.html', context)

@login_required
def servicios_sin_ingresos(request):
    servicios = Servicio.objects.filter(estado='COMPLETADO').select_related('preorden__cliente', 'preorden__equipo').prefetch_related('gastos', 'repuestos').order_by('fecha_servicio')
    servicios_sin_ingresos = []
    for servicio in servicios:
        valor_mano_obra = servicio.valor_mano_obra or Decimal('0.00')
        # Calcular gastos incluyendo modelos antiguos y nuevos
        total_gastos_antiguos = servicio.gastos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        total_gastos_simplificados = servicio.gastos_asistencia_simplificados.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        total_gastos_terceros = servicio.gastos_insumos_terceros.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        total_gastos = total_gastos_antiguos + total_gastos_simplificados + total_gastos_terceros
        
        # Calcular repuestos incluyendo modelos antiguos y nuevos
        total_repuestos_antiguos = servicio.repuestos.aggregate(total=Sum(F('precio_unitario') * F('cantidad')))['total'] or Decimal('0.00')
        total_repuestos_simplificados = servicio.venta_repuestos_simplificada.aggregate(total=Sum('monto_total'))['total'] or Decimal('0.00')
        total_repuestos = total_repuestos_antiguos + total_repuestos_simplificados
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
    
    # Importar modelos de encuestas
    from gestionDeTaller.models import EncuestaServicio, RespuestaEncuesta
    
    # Calcular estadísticas de encuestas
    total_encuestas = EncuestaServicio.objects.count()
    encuestas_enviadas = EncuestaServicio.objects.filter(estado='ENVIADA').count()
    encuestas_respondidas = EncuestaServicio.objects.filter(estado='RESPONDIDA').count()
    encuestas_no_respondidas = EncuestaServicio.objects.filter(estado='NO_RESPONDIDA').count()
    
    # Calcular NPS (Net Promoter Score)
    respuestas = RespuestaEncuesta.objects.all()
    if respuestas.exists():
        promotores = respuestas.filter(probabilidad_recomendacion__gte=9).count()
        pasivos = respuestas.filter(probabilidad_recomendacion__in=[7, 8]).count()
        detractores = respuestas.filter(probabilidad_recomendacion__lte=6).count()
        total_respuestas = respuestas.count()
        
        nps_score = ((promotores - detractores) / total_respuestas * 100) if total_respuestas > 0 else 0
        nps_promotores = (promotores / total_respuestas * 100) if total_respuestas > 0 else 0
        nps_pasivos = (pasivos / total_respuestas * 100) if total_respuestas > 0 else 0
        nps_detractores = (detractores / total_respuestas * 100) if total_respuestas > 0 else 0
    else:
        nps_score = 0
        nps_promotores = 0
        nps_pasivos = 0
        nps_detractores = 0
    
    # Calcular promedio de cumplimiento del acuerdo
    promedio_cumplimiento = respuestas.aggregate(
        promedio=Avg('cumplimiento_acuerdo')
    )['promedio'] or 0
    
    # Calcular promedio de probabilidad de recomendación
    promedio_recomendacion = respuestas.aggregate(
        promedio=Avg('probabilidad_recomendacion')
    )['promedio'] or 0
    
    # Calcular tasa de respuesta
    tasa_respuesta = (encuestas_respondidas / total_encuestas * 100) if total_encuestas > 0 else 0
    
    # Calcular porcentajes para las barras de progreso
    porcentaje_cumplimiento = promedio_cumplimiento * 10
    porcentaje_recomendacion = promedio_recomendacion * 10
    
    context = {
        'total_encuestas': total_encuestas,
        'encuestas_enviadas': encuestas_enviadas,
        'encuestas_respondidas': encuestas_respondidas,
        'encuestas_no_respondidas': encuestas_no_respondidas,
        'nps_score': round(nps_score, 1),
        'nps_promotores': round(nps_promotores, 1),
        'nps_pasivos': round(nps_pasivos, 1),
        'nps_detractores': round(nps_detractores, 1),
        'promedio_cumplimiento': round(promedio_cumplimiento, 1),
        'promedio_recomendacion': round(promedio_recomendacion, 1),
        'tasa_respuesta': round(tasa_respuesta, 1),
        'porcentaje_cumplimiento': round(porcentaje_cumplimiento, 1),
        'porcentaje_recomendacion': round(porcentaje_recomendacion, 1),
    }
    
    return render(request, 'reportes/encuestas/dashboard.html', context)

@login_required
def encuestas_enviadas(request):
    """Reporte de encuestas enviadas"""
    
    # Importar modelos de encuestas
    from gestionDeTaller.models import EncuestaServicio, RespuestaEncuesta
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    estado = request.GET.get('estado')
    exportar = request.GET.get('exportar') == 'excel'
    
    # Filtrar encuestas enviadas
    encuestas = EncuestaServicio.objects.select_related(
        'servicio__preorden__cliente',
        'servicio__preorden__sucursal'
    ).prefetch_related('respuestas', 'servicio__preorden__tecnicos')
    
    # Aplicar filtros
    if fecha_inicio:
        encuestas = encuestas.filter(fecha_envio__gte=fecha_inicio)
    if fecha_fin:
        encuestas = encuestas.filter(fecha_envio__lte=fecha_fin)
    if estado:
        encuestas = encuestas.filter(estado=estado)
    
    # Ordenar por fecha de envío
    encuestas = encuestas.order_by('-fecha_envio')
    
    # Exportar a Excel si se solicita
    if exportar:
        return exportar_encuestas_enviadas_excel(encuestas)
    
    # Paginación
    paginator = Paginator(encuestas, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calcular estadísticas
    total_encuestas = encuestas.count()
    encuestas_enviadas = encuestas.filter(estado='ENVIADA').count()
    encuestas_respondidas = encuestas.filter(estado='RESPONDIDA').count()
    encuestas_no_respondidas = encuestas.filter(estado='NO_RESPONDIDA').count()
    
    # Calcular tasa de respuesta
    tasa_respuesta = (encuestas_respondidas / total_encuestas * 100) if total_encuestas > 0 else 0
    
    # Calcular tiempo promedio de respuesta
    encuestas_con_respuesta = encuestas.filter(estado='RESPONDIDA', fecha_respuesta__isnull=False)
    tiempo_promedio_respuesta = None
    if encuestas_con_respuesta.exists():
        from django.db.models import Avg, F
        tiempo_promedio_respuesta = encuestas_con_respuesta.aggregate(
            tiempo_promedio=Avg(F('fecha_respuesta') - F('fecha_envio'))
        )['tiempo_promedio']
    
    context = {
        'page_obj': page_obj,
        'total_encuestas': total_encuestas,
        'encuestas_enviadas': encuestas_enviadas,
        'encuestas_respondidas': encuestas_respondidas,
        'encuestas_no_respondidas': encuestas_no_respondidas,
        'tasa_respuesta': round(tasa_respuesta, 1),
        'tiempo_promedio_respuesta': tiempo_promedio_respuesta,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'estado': estado,
    }
    
    return render(request, 'reportes/encuestas/enviadas.html', context)

@login_required
def encuestas_respuestas(request):
    """Reporte de encuestas con respuesta"""
    
    # Importar modelos de encuestas
    from gestionDeTaller.models import EncuestaServicio, RespuestaEncuesta
    from django.db.models import Q
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    nps_min = request.GET.get('nps_min')
    nps_max = request.GET.get('nps_max')
    cumplimiento_min = request.GET.get('cumplimiento_min')
    cumplimiento_max = request.GET.get('cumplimiento_max')
    exportar = request.GET.get('exportar') == 'excel'
    
    # Filtrar encuestas respondidas
    encuestas = EncuestaServicio.objects.filter(
        estado='RESPONDIDA'
    ).select_related(
        'servicio__preorden__cliente',
        'servicio__preorden__sucursal'
    ).prefetch_related('respuestas', 'servicio__preorden__tecnicos')
    
    # Aplicar filtros
    if fecha_inicio:
        encuestas = encuestas.filter(fecha_respuesta__gte=fecha_inicio)
    if fecha_fin:
        encuestas = encuestas.filter(fecha_respuesta__lte=fecha_fin)
    
    # Filtrar por NPS
    if nps_min or nps_max:
        respuestas_filtradas = RespuestaEncuesta.objects.all()
        if nps_min:
            respuestas_filtradas = respuestas_filtradas.filter(probabilidad_recomendacion__gte=nps_min)
        if nps_max:
            respuestas_filtradas = respuestas_filtradas.filter(probabilidad_recomendacion__lte=nps_max)
        encuestas = encuestas.filter(respuestas__in=respuestas_filtradas)
    
    # Filtrar por cumplimiento
    if cumplimiento_min or cumplimiento_max:
        respuestas_filtradas = RespuestaEncuesta.objects.all()
        if cumplimiento_min:
            respuestas_filtradas = respuestas_filtradas.filter(cumplimiento_acuerdo__gte=cumplimiento_min)
        if cumplimiento_max:
            respuestas_filtradas = respuestas_filtradas.filter(cumplimiento_acuerdo__lte=cumplimiento_max)
        encuestas = encuestas.filter(respuestas__in=respuestas_filtradas)
    
    # Ordenar por fecha de respuesta
    encuestas = encuestas.order_by('-fecha_respuesta')
    
    # Exportar a Excel si se solicita
    if exportar:
        return exportar_encuestas_respuestas_excel(encuestas)
    
    # Paginación
    paginator = Paginator(encuestas, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calcular estadísticas
    total_encuestas = encuestas.count()
    if total_encuestas > 0:
        respuestas = RespuestaEncuesta.objects.filter(encuesta__in=encuestas)
        promedio_nps = respuestas.aggregate(avg=Avg('probabilidad_recomendacion'))['avg'] or 0
        promedio_cumplimiento = respuestas.aggregate(avg=Avg('cumplimiento_acuerdo'))['avg'] or 0
        
        # Calcular NPS
        promotores = respuestas.filter(probabilidad_recomendacion__gte=9).count()
        detractores = respuestas.filter(probabilidad_recomendacion__lte=6).count()
        nps_score = ((promotores - detractores) / total_encuestas * 100) if total_encuestas > 0 else 0
    else:
        promedio_nps = 0
        promedio_cumplimiento = 0
        nps_score = 0
    
    context = {
        'page_obj': page_obj,
        'total_encuestas': total_encuestas,
        'promedio_nps': round(promedio_nps, 1),
        'promedio_cumplimiento': round(promedio_cumplimiento, 1),
        'nps_score': round(nps_score, 1),
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'nps_min': nps_min,
        'nps_max': nps_max,
        'cumplimiento_min': cumplimiento_min,
        'cumplimiento_max': cumplimiento_max,
    }
    
    return render(request, 'reportes/encuestas/respuestas.html', context)

@login_required
def encuestas_porcentajes(request):
    """Reporte de porcentajes y tendencias de encuestas"""
    
    # Importar modelos de encuestas
    from gestionDeTaller.models import EncuestaServicio, RespuestaEncuesta
    from django.db.models import Count, Avg
    from datetime import datetime, timedelta
    
    # Obtener parámetros de filtro
    periodo = request.GET.get('periodo', 'mes')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    exportar = request.GET.get('exportar') == 'excel'
    
    # Filtrar encuestas
    encuestas = EncuestaServicio.objects.all()
    respuestas = RespuestaEncuesta.objects.all()
    
    # Aplicar filtros de fecha
    if fecha_inicio:
        encuestas = encuestas.filter(fecha_envio__gte=fecha_inicio)
        respuestas = respuestas.filter(fecha_respuesta__gte=fecha_inicio)
    if fecha_fin:
        encuestas = encuestas.filter(fecha_envio__lte=fecha_fin)
        respuestas = respuestas.filter(fecha_respuesta__lte=fecha_fin)
    
    # Calcular estadísticas generales
    total_encuestas = encuestas.count()
    encuestas_respondidas = encuestas.filter(estado='RESPONDIDA').count()
    tasa_respuesta = (encuestas_respondidas / total_encuestas * 100) if total_encuestas > 0 else 0
    
    # Calcular NPS general
    if respuestas.exists():
        promotores = respuestas.filter(probabilidad_recomendacion__gte=9).count()
        pasivos = respuestas.filter(probabilidad_recomendacion__in=[7, 8]).count()
        detractores = respuestas.filter(probabilidad_recomendacion__lte=6).count()
        total_respuestas = respuestas.count()
        
        nps_score = ((promotores - detractores) / total_respuestas * 100) if total_respuestas > 0 else 0
        porcentaje_promotores = (promotores / total_respuestas * 100) if total_respuestas > 0 else 0
        porcentaje_pasivos = (pasivos / total_respuestas * 100) if total_respuestas > 0 else 0
        porcentaje_detractores = (detractores / total_respuestas * 100) if total_respuestas > 0 else 0
    else:
        nps_score = 0
        porcentaje_promotores = 0
        porcentaje_pasivos = 0
        porcentaje_detractores = 0
    
    # Calcular promedios
    promedio_cumplimiento = respuestas.aggregate(avg=Avg('cumplimiento_acuerdo'))['avg'] or 0
    promedio_recomendacion = respuestas.aggregate(avg=Avg('probabilidad_recomendacion'))['avg'] or 0
    
    # Calcular distribución por calificaciones
    distribucion_cumplimiento = {}
    distribucion_recomendacion = {}
    porcentajes_cumplimiento = {}
    porcentajes_recomendacion = {}
    
    for i in range(1, 11):
        count_cumplimiento = respuestas.filter(cumplimiento_acuerdo=i).count()
        count_recomendacion = respuestas.filter(probabilidad_recomendacion=i).count()
        
        distribucion_cumplimiento[i] = count_cumplimiento
        distribucion_recomendacion[i] = count_recomendacion
        
        # Calcular porcentajes
        porcentajes_cumplimiento[i] = (count_cumplimiento / encuestas_respondidas * 100) if encuestas_respondidas > 0 else 0
        porcentajes_recomendacion[i] = (count_recomendacion / encuestas_respondidas * 100) if encuestas_respondidas > 0 else 0
    
    # Calcular tendencias por período
    if periodo == 'mes':
        # Últimos 12 meses
        tendencias = []
        for i in range(12):
            fecha = datetime.now() - timedelta(days=30*i)
            mes_inicio = fecha.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i == 0:
                mes_fin = datetime.now()
            else:
                mes_fin = (fecha + timedelta(days=30)).replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
            
            respuestas_mes = respuestas.filter(fecha_respuesta__range=[mes_inicio, mes_fin])
            if respuestas_mes.exists():
                promotores_mes = respuestas_mes.filter(probabilidad_recomendacion__gte=9).count()
                detractores_mes = respuestas_mes.filter(probabilidad_recomendacion__lte=6).count()
                total_mes = respuestas_mes.count()
                nps_mes = ((promotores_mes - detractores_mes) / total_mes * 100) if total_mes > 0 else 0
                
                tendencias.append({
                    'periodo': mes_inicio.strftime('%B %Y'),
                    'nps': round(nps_mes, 1),
                    'total_respuestas': total_mes,
                    'promedio_cumplimiento': round(respuestas_mes.aggregate(avg=Avg('cumplimiento_acuerdo'))['avg'] or 0, 1),
                    'promedio_recomendacion': round(respuestas_mes.aggregate(avg=Avg('probabilidad_recomendacion'))['avg'] or 0, 1),
                    'porcentaje_tendencia': round((nps_mes + 100) / 2, 1) if nps_mes >= 0 else 0,
                })
    else:
        # Últimas 12 semanas
        tendencias = []
        for i in range(12):
            fecha = datetime.now() - timedelta(weeks=i)
            semana_inicio = fecha - timedelta(days=fecha.weekday())
            semana_inicio = semana_inicio.replace(hour=0, minute=0, second=0, microsecond=0)
            semana_fin = semana_inicio + timedelta(days=6, hours=23, minutes=59, seconds=59)
            
            respuestas_semana = respuestas.filter(fecha_respuesta__range=[semana_inicio, semana_fin])
            if respuestas_semana.exists():
                promotores_semana = respuestas_semana.filter(probabilidad_recomendacion__gte=9).count()
                detractores_semana = respuestas_semana.filter(probabilidad_recomendacion__lte=6).count()
                total_semana = respuestas_semana.count()
                nps_semana = ((promotores_semana - detractores_semana) / total_semana * 100) if total_semana > 0 else 0
                
                tendencias.append({
                    'periodo': f"Semana {semana_inicio.strftime('%d/%m')} - {semana_fin.strftime('%d/%m')}",
                    'nps': round(nps_semana, 1),
                    'total_respuestas': total_semana,
                    'promedio_cumplimiento': round(respuestas_semana.aggregate(avg=Avg('cumplimiento_acuerdo'))['avg'] or 0, 1),
                    'promedio_recomendacion': round(respuestas_semana.aggregate(avg=Avg('probabilidad_recomendacion'))['avg'] or 0, 1),
                    'porcentaje_tendencia': round((nps_semana + 100) / 2, 1) if nps_semana >= 0 else 0,
                })
    
    # Exportar a Excel si se solicita
    if exportar:
        return exportar_encuestas_porcentajes_excel(tendencias, distribucion_cumplimiento, distribucion_recomendacion)
    
    context = {
        'total_encuestas': total_encuestas,
        'encuestas_respondidas': encuestas_respondidas,
        'tasa_respuesta': round(tasa_respuesta, 1),
        'nps_score': round(nps_score, 1),
        'porcentaje_promotores': round(porcentaje_promotores, 1),
        'porcentaje_pasivos': round(porcentaje_pasivos, 1),
        'porcentaje_detractores': round(porcentaje_detractores, 1),
        'promedio_cumplimiento': round(promedio_cumplimiento, 1),
        'promedio_recomendacion': round(promedio_recomendacion, 1),
        'distribucion_cumplimiento': distribucion_cumplimiento,
        'distribucion_recomendacion': distribucion_recomendacion,
        'porcentajes_cumplimiento': porcentajes_cumplimiento,
        'porcentajes_recomendacion': porcentajes_recomendacion,
        'tendencias': tendencias,
        'periodo': periodo,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }
    
    return render(request, 'reportes/encuestas/porcentajes.html', context)

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

def exportar_encuestas_respuestas_excel(encuestas):
    """Exportar encuestas con respuesta a Excel"""
    from gestionDeTaller.models import RespuestaEncuesta
    
    # Crear DataFrame
    data = []
    for encuesta in encuestas:
        respuesta = encuesta.respuestas.first()
        if respuesta:
            data.append({
                'ID Servicio': encuesta.servicio.id,
                'Cliente': encuesta.servicio.preorden.cliente.razon_social,
                'Técnico': encuesta.servicio.tecnico.get_full_name() if encuesta.servicio.tecnico else 'N/A',
                'Sucursal': encuesta.servicio.sucursal.nombre if encuesta.servicio.sucursal else 'N/A',
                'Fecha Respuesta': respuesta.fecha_respuesta.strftime('%d/%m/%Y %H:%M'),
                'Cumplimiento Acuerdo': respuesta.cumplimiento_acuerdo or 'N/A',
                'Probabilidad Recomendación': respuesta.probabilidad_recomendacion or 'N/A',
                'Categoría NPS': respuesta.get_nps_category(),
                'Categoría Cumplimiento': respuesta.get_cumplimiento_category(),
                'Motivo Cumplimiento Bajo': respuesta.motivo_cumplimiento_bajo or 'N/A',
                'Motivo Recomendación Baja': respuesta.motivo_recomendacion_baja or 'N/A',
                'Problemas Pendientes': respuesta.problemas_pendientes or 'N/A',
                'Comentarios Generales': respuesta.comentarios_generales or 'N/A',
                'Nombre Respondente': respuesta.nombre_respondente or 'N/A',
                'Cargo Respondente': respuesta.cargo_respondente or 'N/A',
            })
    
    df = pd.DataFrame(data)
    
    # Crear archivo Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Encuestas Respondidas', index=False)
        
        # Ajustar ancho de columnas
        worksheet = writer.sheets['Encuestas Respondidas']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    # Crear respuesta HTTP
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="encuestas_respondidas.xlsx"'
    
    return response

def exportar_encuestas_enviadas_excel(encuestas):
    """Exportar encuestas enviadas a Excel"""
    from gestionDeTaller.models import RespuestaEncuesta
    
    # Crear DataFrame
    data = []
    for encuesta in encuestas:
        respuesta = encuesta.respuestas.first()
        data.append({
            'ID': encuesta.id,
            'Fecha de Envío': encuesta.fecha_envio.strftime('%d/%m/%Y %H:%M'),
            'Estado': encuesta.get_estado_display(),
            'Servicio Asociado': encuesta.servicio.id,
            'Cliente': encuesta.servicio.preorden.cliente.razon_social,
            'Técnico Asignado': encuesta.servicio.tecnico.get_full_name() if encuesta.servicio.tecnico else 'N/A',
            'Sucursal': encuesta.servicio.sucursal.nombre if encuesta.servicio.sucursal else 'N/A',
            'Fecha de Respuesta': encuesta.fecha_respuesta.strftime('%d/%m/%Y %H:%M') if encuesta.fecha_respuesta else 'N/A',
            'Cumplimiento Acuerdo': respuesta.cumplimiento_acuerdo if respuesta else 'N/A',
            'Probabilidad Recomendación': respuesta.probabilidad_recomendacion if respuesta else 'N/A',
            'Categoría NPS': respuesta.get_nps_category() if respuesta else 'N/A',
            'Categoría Cumplimiento': respuesta.get_cumplimiento_category() if respuesta else 'N/A',
            'Motivo Cumplimiento Bajo': respuesta.motivo_cumplimiento_bajo if respuesta else 'N/A',
            'Motivo Recomendación Baja': respuesta.motivo_recomendacion_baja if respuesta else 'N/A',
            'Problemas Pendientes': respuesta.problemas_pendientes if respuesta else 'N/A',
            'Comentarios Generales': respuesta.comentarios_generales if respuesta else 'N/A',
            'Nombre Respondente': respuesta.nombre_respondente if respuesta else 'N/A',
            'Cargo Respondente': respuesta.cargo_respondente if respuesta else 'N/A',
        })
    
    df = pd.DataFrame(data)
    
    # Crear archivo Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Encuestas Enviadas', index=False)
        
        # Ajustar ancho de columnas
        worksheet = writer.sheets['Encuestas Enviadas']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    # Crear respuesta HTTP
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="encuestas_enviadas.xlsx"'
    
    return response

def exportar_encuestas_porcentajes_excel(tendencias, distribucion_cumplimiento, distribucion_recomendacion):
    """Exportar reporte de porcentajes de encuestas a Excel"""
    
    # Crear DataFrame para Tendencias
    tendencias_data = []
    for item in tendencias:
        tendencias_data.append({
            'Periodo': item['periodo'],
            'NPS': item['nps'],
            'Total Respuestas': item['total_respuestas'],
            'Promedio Cumplimiento': item['promedio_cumplimiento'],
            'Promedio Recomendación': item['promedio_recomendacion'],
        })
    
    tendencias_df = pd.DataFrame(tendencias_data)
    
    # Crear DataFrame para Distribuciones
    distribucion_cumplimiento_data = []
    for calificacion, count in distribucion_cumplimiento.items():
        distribucion_cumplimiento_data.append({
            'Calificación': calificacion,
            'Cantidad': count,
        })
    
    distribucion_cumplimiento_df = pd.DataFrame(distribucion_cumplimiento_data)
    
    distribucion_recomendacion_data = []
    for calificacion, count in distribucion_recomendacion.items():
        distribucion_recomendacion_data.append({
            'Calificación': calificacion,
            'Cantidad': count,
        })
    
    distribucion_recomendacion_df = pd.DataFrame(distribucion_recomendacion_data)
    
    # Crear archivo Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        tendencias_df.to_excel(writer, sheet_name='Tendencias', index=False)
        distribucion_cumplimiento_df.to_excel(writer, sheet_name='Distribucion Cumplimiento', index=False)
        distribucion_recomendacion_df.to_excel(writer, sheet_name='Distribucion Recomendacion', index=False)
        
        # Ajustar ancho de columnas
        worksheet = writer.sheets['Tendencias']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        worksheet = writer.sheets['Distribucion Cumplimiento']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        worksheet = writer.sheets['Distribucion Recomendacion']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    # Crear respuesta HTTP
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="encuestas_porcentajes.xlsx"'
    
    return response

@login_required
def preordenes_sin_servicio(request):
    """Dashboard de preórdenes sin servicio asignado"""
    
    # Obtener filtros
    sucursal_id = request.GET.get('sucursal', '')
    clasificacion = request.GET.get('clasificacion', '')
    tipo_trabajo = request.GET.get('tipo_trabajo', '')
    exportar = request.GET.get('exportar') == 'true'
    
    # Base queryset de preórdenes sin servicio
    preordenes_sin_servicio = PreOrden.objects.filter(
        activo=True,
        servicio__isnull=True
    ).select_related('cliente', 'equipo', 'sucursal', 'creado_por').prefetch_related('tecnicos')
    
    # Aplicar filtros
    if sucursal_id:
        preordenes_sin_servicio = preordenes_sin_servicio.filter(sucursal_id=sucursal_id)
    
    if clasificacion:
        preordenes_sin_servicio = preordenes_sin_servicio.filter(clasificacion=clasificacion)
    
    if tipo_trabajo:
        preordenes_sin_servicio = preordenes_sin_servicio.filter(tipo_trabajo=tipo_trabajo)
    
    # Calcular días transcurridos y categorizar
    fecha_actual = timezone.now().date()
    oportunidades_por_tiempo = {
        'recientes': [],
        'en_riesgo': [],
        'perdidas': []
    }
    
    for preorden in preordenes_sin_servicio:
        dias_desde_creacion = (fecha_actual - preorden.fecha_creacion.date()).days
        dias_desde_estimada = (fecha_actual - preorden.fecha_estimada).days
        
        # Categorizar por tiempo transcurrido
        if dias_desde_creacion <= 7:
            categoria = 'recientes'
        elif dias_desde_creacion <= 15:
            categoria = 'en_riesgo'
        else:
            categoria = 'perdidas'
        
        oportunidades_por_tiempo[categoria].append({
            'preorden': preorden,
            'dias_desde_creacion': dias_desde_creacion,
            'dias_desde_estimada': dias_desde_estimada,
            'urgente': dias_desde_estimada < 0  # Fecha estimada pasada
        })
    
    # Calcular métricas generales
    total_preordenes = preordenes_sin_servicio.count()
    total_recientes = len(oportunidades_por_tiempo['recientes'])
    total_en_riesgo = len(oportunidades_por_tiempo['en_riesgo'])
    total_perdidas = len(oportunidades_por_tiempo['perdidas'])
    
    # Calcular tasa de conversión (últimos 30 días)
    fecha_limite = timezone.now().date() - timedelta(days=30)
    preordenes_30_dias = PreOrden.objects.filter(
        fecha_creacion__gte=fecha_limite,
        activo=True
    )
    
    # Aplicar filtros adicionales
    if sucursal_id:
        preordenes_30_dias = preordenes_30_dias.filter(sucursal_id=sucursal_id)
    if clasificacion:
        preordenes_30_dias = preordenes_30_dias.filter(clasificacion=clasificacion)
    if tipo_trabajo:
        preordenes_30_dias = preordenes_30_dias.filter(tipo_trabajo=tipo_trabajo)
    
    total_30_dias = preordenes_30_dias.count()
    con_servicio_30_dias = preordenes_30_dias.filter(servicio__isnull=False).count()
    sin_servicio_30_dias = total_30_dias - con_servicio_30_dias
    tasa_conversion = (con_servicio_30_dias / total_30_dias * 100) if total_30_dias > 0 else 0
    
    # Análisis por cliente
    clientes_con_mas_preordenes = preordenes_sin_servicio.values(
        'cliente__razon_social', 'cliente__id'
    ).annotate(
        total=Count('numero'),
        ultima_preorden=Max('fecha_creacion')
    ).order_by('-total')[:10]
    
    # Análisis por sucursal
    sucursales_analisis = preordenes_sin_servicio.values(
        'sucursal__nombre', 'sucursal__id'
    ).annotate(
        total=Count('numero'),
        recientes=Count('numero', filter=Q(fecha_creacion__gte=fecha_actual - timedelta(days=7))),
        en_riesgo=Count('numero', filter=Q(
            fecha_creacion__gte=fecha_actual - timedelta(days=15),
            fecha_creacion__lt=fecha_actual - timedelta(days=7)
        )),
        perdidas=Count('numero', filter=Q(fecha_creacion__lt=fecha_actual - timedelta(days=15)))
    ).order_by('-total')
    
    # Exportar a Excel si se solicita
    if exportar:
        import pandas as pd
        from django.http import HttpResponse
        
        datos = []
        for categoria, preordenes in oportunidades_por_tiempo.items():
            for item in preordenes:
                preorden = item['preorden']
                tecnicos = ', '.join([f"{t.apellido}, {t.nombre}" for t in preorden.tecnicos.all()])
                
                datos.append({
                    'Número': preorden.numero,
                    'Cliente': preorden.cliente.razon_social,
                    'Equipo': f"{preorden.equipo.modelo.nombre} ({preorden.equipo.numero_serie})",
                    'Sucursal': preorden.sucursal.nombre,
                    'Tipo Trabajo': preorden.get_tipo_trabajo_display(),
                    'Clasificación': preorden.get_clasificacion_display(),
                    'Fecha Estimada': preorden.fecha_estimada,
                    'Fecha Creación': preorden.fecha_creacion.date(),
                    'Días desde Creación': item['dias_desde_creacion'],
                    'Días desde Estimada': item['dias_desde_estimada'],
                    'Técnicos Asignados': tecnicos,
                    'Creado por': f"{preorden.creado_por.apellido}, {preorden.creado_por.nombre}",
                    'Categoría': categoria.upper(),
                    'Urgente': 'SÍ' if item['urgente'] else 'NO'
                })
        
        df = pd.DataFrame(datos)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=preordenes_sin_servicio.xlsx'
        df.to_excel(response, index=False)
        return response
    
    # Obtener datos para filtros
    from recursosHumanos.models import Sucursal
    sucursales_filtro = Sucursal.objects.filter(activo=True)
    
    context = {
        'titulo': 'Preórdenes Sin Servicio',
        'oportunidades_por_tiempo': oportunidades_por_tiempo,
        'total_preordenes': total_preordenes,
        'total_recientes': total_recientes,
        'total_en_riesgo': total_en_riesgo,
        'total_perdidas': total_perdidas,
        'tasa_conversion': tasa_conversion,
        'con_servicio_30_dias': con_servicio_30_dias,
        'sin_servicio_30_dias': sin_servicio_30_dias,
        'total_30_dias': total_30_dias,
        'clientes_con_mas_preordenes': clientes_con_mas_preordenes,
        'sucursales_analisis': sucursales_analisis,
        'sucursales_filtro': sucursales_filtro,
        'sucursal_filtro': sucursal_id,
        'clasificacion_filtro': clasificacion,
        'tipo_trabajo_filtro': tipo_trabajo,
        'fecha_actual': fecha_actual,
    }
    
    return render(request, 'reportes/preordenes/sin_servicio.html', context)

@login_required
def metricas_conversion_preordenes(request):
    """Métricas detalladas de conversión de preórdenes a servicios"""
    
    # Parámetros de filtro
    periodo_dias = int(request.GET.get('periodo_dias', 30))
    sucursal_id = request.GET.get('sucursal', '')
    
    fecha_limite = timezone.now().date() - timedelta(days=periodo_dias)
    
    # Base queryset
    preordenes = PreOrden.objects.filter(
        fecha_creacion__gte=fecha_limite
    ).select_related('cliente', 'equipo', 'sucursal', 'servicio')
    
    if sucursal_id:
        preordenes = preordenes.filter(sucursal_id=sucursal_id)
    
    # Métricas generales
    total_preordenes = preordenes.count()
    preordenes_con_servicio = preordenes.filter(servicio__isnull=False).count()
    preordenes_sin_servicio = total_preordenes - preordenes_con_servicio
    
    tasa_conversion = (preordenes_con_servicio / total_preordenes * 100) if total_preordenes > 0 else 0
    
    # Análisis por clasificación
    conversion_por_clasificacion = preordenes.values('clasificacion').annotate(
        total=Count('numero'),
        con_servicio=Count('numero', filter=Q(servicio__isnull=False)),
        sin_servicio=Count('numero', filter=Q(servicio__isnull=True))
    ).annotate(
        tasa_conversion=ExpressionWrapper(
            F('con_servicio') * 100.0 / F('total'),
            output_field=FloatField()
        )
    ).order_by('-total')
    
    # Análisis por tipo de trabajo
    conversion_por_tipo = preordenes.values('tipo_trabajo').annotate(
        total=Count('numero'),
        con_servicio=Count('numero', filter=Q(servicio__isnull=False)),
        sin_servicio=Count('numero', filter=Q(servicio__isnull=True))
    ).annotate(
        tasa_conversion=ExpressionWrapper(
            F('con_servicio') * 100.0 / F('total'),
            output_field=FloatField()
        )
    ).order_by('-total')
    
    # Análisis por sucursal
    conversion_por_sucursal = preordenes.values('sucursal__nombre').annotate(
        total=Count('numero'),
        con_servicio=Count('numero', filter=Q(servicio__isnull=False)),
        sin_servicio=Count('numero', filter=Q(servicio__isnull=True))
    ).annotate(
        tasa_conversion=ExpressionWrapper(
            F('con_servicio') * 100.0 / F('total'),
            output_field=FloatField()
        )
    ).order_by('-tasa_conversion')
    
    # Análisis temporal (últimos 12 meses)
    conversion_mensual = []
    for i in range(12):
        fecha_inicio = timezone.now().date() - timedelta(days=30 * (i + 1))
        fecha_fin = timezone.now().date() - timedelta(days=30 * i)
        
        preordenes_mes = preordenes.filter(
            fecha_creacion__date__range=[fecha_inicio, fecha_fin]
        )
        
        total_mes = preordenes_mes.count()
        con_servicio_mes = preordenes_mes.filter(servicio__isnull=False).count()
        tasa_mes = (con_servicio_mes / total_mes * 100) if total_mes > 0 else 0
        
        conversion_mensual.append({
            'mes': fecha_inicio.strftime('%B %Y'),
            'total': total_mes,
            'con_servicio': con_servicio_mes,
            'sin_servicio': total_mes - con_servicio_mes,
            'tasa_conversion': tasa_mes
        })
    
    conversion_mensual.reverse()  # Ordenar cronológicamente
    
    # Top clientes con mejor/menor conversión
    clientes_conversion = preordenes.values('cliente__razon_social').annotate(
        total=Count('numero'),
        con_servicio=Count('numero', filter=Q(servicio__isnull=False)),
        sin_servicio=Count('numero', filter=Q(servicio__isnull=True))
    ).annotate(
        tasa_conversion=ExpressionWrapper(
            F('con_servicio') * 100.0 / F('total'),
            output_field=FloatField()
        )
    ).filter(total__gte=3).order_by('-tasa_conversion')  # Solo clientes con 3+ preórdenes
    
    # Obtener datos para filtros
    from recursosHumanos.models import Sucursal
    sucursales_filtro = Sucursal.objects.filter(activo=True)
    
    context = {
        'titulo': 'Métricas de Conversión de Preórdenes',
        'periodo_dias': periodo_dias,
        'total_preordenes': total_preordenes,
        'preordenes_con_servicio': preordenes_con_servicio,
        'preordenes_sin_servicio': preordenes_sin_servicio,
        'tasa_conversion': tasa_conversion,
        'conversion_por_clasificacion': conversion_por_clasificacion,
        'conversion_por_tipo': conversion_por_tipo,
        'conversion_por_sucursal': conversion_por_sucursal,
        'conversion_mensual': conversion_mensual,
        'clientes_conversion': clientes_conversion,
        'sucursales_filtro': sucursales_filtro,
        'sucursal_filtro': sucursal_id,
    }
    
    return render(request, 'reportes/preordenes/metricas_conversion.html', context)
