from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Avg, Q, F, ExpressionWrapper, DurationField
from django.utils import timezone
from datetime import datetime, timedelta
import json
import pandas as pd
from decimal import Decimal
from django.core.paginator import Paginator
import io

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
    
    # Agregar gastos y repuestos
    total_gastos = servicios_completados.aggregate(
        total=Sum('gastos__monto')
    )['total'] or 0
    
    total_repuestos = servicios_completados.aggregate(
        total=Sum(F('repuestos__precio_unitario') * F('repuestos__cantidad'))
    )['total'] or 0
    
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
        
        total_gastos = servicios_tecnico.aggregate(
            total=Sum('gastos__monto')
        )['total'] or 0
        
        total_repuestos = servicios_tecnico.aggregate(
            total=Sum(F('repuestos__precio_unitario') * F('repuestos__cantidad'))
        )['total'] or 0
        
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
        
        facturacion_por_tecnico.append({
            'tecnico': tecnico,
            'total_facturacion': total_facturacion,
            'mano_obra': total_mano_obra,
            'gastos': total_gastos,
            'repuestos': total_repuestos,
            'horas_trabajadas': horas_decimal,
            'servicios_completados': servicios_completados,
            'promedio_por_servicio': total_facturacion / servicios_completados if servicios_completados > 0 else 0
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
                'Promedio por Servicio': float(item['promedio_por_servicio'])
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
        
        total_gastos = servicios_sucursal.aggregate(
            total=Sum('gastos__monto')
        )['total'] or 0
        
        total_repuestos = servicios_sucursal.aggregate(
            total=Sum(F('repuestos__precio_unitario') * F('repuestos__cantidad'))
        )['total'] or 0
        
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
            
            # Calcular facturación del mes
            total_mano_obra = servicios_mes.aggregate(
                total=Sum('valor_mano_obra')
            )['total'] or 0
            
            total_gastos = servicios_mes.aggregate(
                total=Sum('gastos__monto')
            )['total'] or 0
            
            total_repuestos = servicios_mes.aggregate(
                total=Sum(F('repuestos__precio_unitario') * F('repuestos__cantidad'))
            )['total'] or 0
            
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
            total_gastos = servicios_mes.aggregate(total=Sum('gastos__monto'))['total'] or 0
            total_repuestos = servicios_mes.aggregate(
                total=Sum(F('repuestos__precio_unitario') * F('repuestos__cantidad'))
            )['total'] or 0
            
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
            
            # Calcular facturación del mes
            total_mano_obra = servicios_mes.aggregate(
                total=Sum('valor_mano_obra')
            )['total'] or 0
            
            total_gastos = servicios_mes.aggregate(
                total=Sum('gastos__monto')
            )['total'] or 0
            
            total_repuestos = servicios_mes.aggregate(
                total=Sum(F('repuestos__precio_unitario') * F('repuestos__cantidad'))
            )['total'] or 0
            
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
            total_gastos = servicios_mes.aggregate(total=Sum('gastos__monto'))['total'] or 0
            total_repuestos = servicios_mes.aggregate(
                total=Sum(F('repuestos__precio_unitario') * F('repuestos__cantidad'))
            )['total'] or 0
            
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
        
        # Calcular facturación del mes
        total_mano_obra = servicios_mes.aggregate(
            total=Sum('valor_mano_obra')
        )['total'] or 0
        
        total_gastos = servicios_mes.aggregate(
            total=Sum('gastos__monto')
        )['total'] or 0
        
        total_repuestos = servicios_mes.aggregate(
            total=Sum(F('repuestos__precio_unitario') * F('repuestos__cantidad'))
        )['total'] or 0
        
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
        total_gastos = servicios_mes.aggregate(total=Sum('gastos__monto'))['total'] or 0
        total_repuestos = servicios_mes.aggregate(
            total=Sum(F('repuestos__precio_unitario') * F('repuestos__cantidad'))
        )['total'] or 0
        
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
