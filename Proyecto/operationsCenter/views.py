from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from datetime import datetime, timedelta
import json
import requests
from urllib.parse import urlencode

from .models import (
    OperationsCenterConfig, Machine, MachineLocation, MachineEngineHours,
    MachineAlert, MachineHoursOfOperation, DeviceStateReport,
    TelemetryReport, TelemetryReportMachine
)
from .services import OperationsCenterSyncService, JohnDeereAPIService
from clientes.models import Cliente, Equipo


@login_required
def dashboard_operations_center(request):
    """Dashboard principal del Operations Center"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('gestionDeTaller:gestion_de_taller')
    
    # Estadísticas generales
    total_machines = Machine.objects.filter(is_active=True).count()
    total_alerts = MachineAlert.objects.filter(status='ACTIVE').count()
    total_clients_with_machines = Cliente.objects.filter(
        equipos__machines_oc__isnull=False
    ).distinct().count()
    
    # Alertas por severidad
    alerts_by_severity = MachineAlert.objects.filter(status='ACTIVE').values('severity').annotate(
        count=Count('id')
    )
    
    # Máquinas con problemas (alertas críticas o altas)
    machines_with_issues = Machine.objects.filter(
        alerts__severity__in=['HIGH', 'CRITICAL'],
        alerts__status='ACTIVE'
    ).distinct().count()
    
    # Últimas alertas
    recent_alerts = MachineAlert.objects.filter(status='ACTIVE').order_by('-timestamp')[:10]
    
    # Máquinas sin sincronización reciente
    stale_machines = Machine.objects.filter(
        is_active=True,
        last_sync__lt=timezone.now() - timedelta(days=1)
    ).count()
    
    context = {
        'total_machines': total_machines,
        'total_alerts': total_alerts,
        'total_clients_with_machines': total_clients_with_machines,
        'alerts_by_severity': alerts_by_severity,
        'machines_with_issues': machines_with_issues,
        'recent_alerts': recent_alerts,
        'stale_machines': stale_machines,
    }
    
    return render(request, 'operationsCenter/dashboard.html', context)


@login_required
def lista_maquinas(request):
    """Lista de máquinas sincronizadas"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('gestionDeTaller:gestion_de_taller')
    
    # Filtros
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    client_filter = request.GET.get('client', '')
    
    machines = Machine.objects.filter(is_active=True)
    
    if search:
        machines = machines.filter(
            Q(serial_number__icontains=search) |
            Q(model_name__icontains=search) |
            Q(make_name__icontains=search) |
            Q(equipo_local__cliente__razon_social__icontains=search)
        )
    
    if status_filter == 'with_alerts':
        machines = machines.filter(alerts__status='ACTIVE').distinct()
    elif status_filter == 'no_alerts':
        machines = machines.exclude(alerts__status='ACTIVE')
    
    if client_filter:
        machines = machines.filter(equipo_local__cliente_id=client_filter)
    
    # Paginación
    paginator = Paginator(machines, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Clientes para filtro
    clients = Cliente.objects.filter(equipos__machines_oc__isnull=False).distinct()
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'client_filter': client_filter,
        'clients': clients,
    }
    
    return render(request, 'operationsCenter/lista_maquinas.html', context)


@login_required
def detalle_maquina(request, machine_id):
    """Detalle de una máquina específica"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('gestionDeTaller:gestion_de_taller')
    
    machine = get_object_or_404(Machine, id=machine_id)
    
    # Obtener datos de telemetría
    recent_locations = machine.locations.order_by('-timestamp')[:50]
    recent_engine_hours = machine.engine_hours.order_by('-timestamp')[:30]
    active_alerts = machine.alerts.filter(status='ACTIVE').order_by('-timestamp')
    recent_alerts = machine.alerts.order_by('-timestamp')[:20]
    
    # Estadísticas de la máquina
    total_hours = machine.engine_hours.order_by('-timestamp').first()
    total_alerts = machine.alerts.count()
    active_alerts_count = machine.alerts.filter(status='ACTIVE').count()
    
    # Servicios relacionados
    related_services = []
    if machine.equipo_local:
        related_services = machine.equipo_local.servicios.all().order_by('-fecha_servicio')[:10]
    
    context = {
        'machine': machine,
        'recent_locations': recent_locations,
        'recent_engine_hours': recent_engine_hours,
        'active_alerts': active_alerts,
        'recent_alerts': recent_alerts,
        'total_hours': total_hours,
        'total_alerts': total_alerts,
        'active_alerts_count': active_alerts_count,
        'related_services': related_services,
    }
    
    return render(request, 'operationsCenter/detalle_maquina.html', context)


@login_required
def lista_alertas(request):
    """Lista de alertas de todas las máquinas"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('gestionDeTaller:gestion_de_taller')
    
    # Filtros
    status_filter = request.GET.get('status', '')
    severity_filter = request.GET.get('severity', '')
    machine_filter = request.GET.get('machine', '')
    
    alerts = MachineAlert.objects.all()
    
    if status_filter:
        alerts = alerts.filter(status=status_filter)
    
    if severity_filter:
        alerts = alerts.filter(severity=severity_filter)
    
    if machine_filter:
        alerts = alerts.filter(machine_id=machine_filter)
    
    # Paginación
    paginator = Paginator(alerts, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Máquinas para filtro
    machines = Machine.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'severity_filter': severity_filter,
        'machine_filter': machine_filter,
        'machines': machines,
    }
    
    return render(request, 'operationsCenter/lista_alertas.html', context)


@login_required
def detalle_alerta(request, alert_id):
    """Detalle de una alerta específica"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('gestionDeTaller:gestion_de_taller')
    
    alert = get_object_or_404(MachineAlert, id=alert_id)
    
    # Servicios relacionados
    related_services = []
    if alert.machine.equipo_local:
        related_services = alert.machine.equipo_local.servicios.all().order_by('-fecha_servicio')[:5]
    
    context = {
        'alert': alert,
        'related_services': related_services,
    }
    
    return render(request, 'operationsCenter/detalle_alerta.html', context)


@login_required
def sincronizar_datos(request):
    """Sincronizar datos desde Operations Center"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return redirect('gestionDeTaller:gestion_de_taller')
    
    if request.method == 'POST':
        try:
            sync_service = OperationsCenterSyncService()
            days_back = int(request.POST.get('days_back', 7))
            
            results = sync_service.sync_all_machine_data(days_back)
            
            # Contar resultados
            success_count = sum(1 for _, success, _ in results if success)
            total_count = len(results)
            
            if success_count == total_count:
                messages.success(request, f'Sincronización completada exitosamente. {success_count}/{total_count} operaciones exitosas.')
            else:
                messages.warning(request, f'Sincronización completada con algunos errores. {success_count}/{total_count} operaciones exitosas.')
            
            # Mostrar detalles de errores si los hay
            for operation, success, message in results:
                if not success:
                    messages.error(request, f'{operation}: {message}')
            
        except Exception as e:
            messages.error(request, f'Error durante la sincronización: {str(e)}')
    
    return redirect('operationsCenter:dashboard_operations_center')


@login_required
def sincronizar_maquina(request, machine_id):
    """Sincronizar datos de una máquina específica"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return redirect('operationsCenter:lista_maquinas')
    
    machine = get_object_or_404(Machine, id=machine_id)
    
    if request.method == 'POST':
        try:
            sync_service = OperationsCenterSyncService()
            days_back = int(request.POST.get('days_back', 7))
            
            # Sincronizar diferentes tipos de datos
            results = []
            
            success, message = sync_service.sync_machine_location(machine.machine_id, days_back)
            results.append(('Ubicaciones', success, message))
            
            success, message = sync_service.sync_machine_engine_hours(machine.machine_id, days_back)
            results.append(('Horas de motor', success, message))
            
            success, message = sync_service.sync_machine_alerts(machine.machine_id, 30)
            results.append(('Alertas', success, message))
            
            # Mostrar resultados
            success_count = sum(1 for _, success, _ in results if success)
            for operation, success, message in results:
                if success:
                    messages.success(request, f'{operation}: {message}')
                else:
                    messages.error(request, f'{operation}: {message}')
            
        except Exception as e:
            messages.error(request, f'Error durante la sincronización: {str(e)}')
    
    return redirect('operationsCenter:detalle_maquina', machine_id=machine_id)


@login_required
def configuracion_oc(request):
    """Configuración del Operations Center"""
    if request.user.rol not in ['GERENTE']:
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('operationsCenter:dashboard_operations_center')
    
    config = OperationsCenterConfig.objects.filter(is_active=True).first()
    
    if request.method == 'POST':
        if not config:
            config = OperationsCenterConfig()
        
        config.client_id = request.POST.get('client_id')
        config.client_secret = request.POST.get('client_secret')
        config.redirect_uri = request.POST.get('redirect_uri')
        config.organization_id = request.POST.get('organization_id')
        config.access_token = request.POST.get('access_token')
        config.refresh_token = request.POST.get('refresh_token')
        
        if request.POST.get('token_expires_at'):
            config.token_expires_at = datetime.fromisoformat(request.POST.get('token_expires_at'))
        
        config.save()
        messages.success(request, 'Configuración guardada exitosamente.')
        return redirect('operationsCenter:configuracion_oc')
    
    context = {
        'config': config,
    }
    
    return render(request, 'operationsCenter/configuracion.html', context)


@login_required
def lista_reportes_telemetria(request):
    """Lista de reportes de telemetría generados"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('operationsCenter:dashboard_operations_center')
    
    reports = TelemetryReport.objects.all()
    
    # Filtros
    status_filter = request.GET.get('status', '')
    client_filter = request.GET.get('client', '')
    
    if status_filter:
        reports = reports.filter(status=status_filter)
    
    if client_filter:
        reports = reports.filter(cliente_id=client_filter)
    
    # Paginación
    paginator = Paginator(reports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Clientes para filtro
    clients = Cliente.objects.filter(equipos__machines_oc__isnull=False).distinct()
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'client_filter': client_filter,
        'clients': clients,
    }
    
    return render(request, 'operationsCenter/lista_reportes.html', context)


@login_required
def crear_reporte_telemetria(request):
    """Crear un nuevo reporte de telemetría"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('operationsCenter:lista_reportes_telemetria')
    
    if request.method == 'POST':
        try:
            cliente_id = request.POST.get('cliente')
            report_type = request.POST.get('report_type')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            machines = request.POST.getlist('machines')  # Lista de máquinas seleccionadas
            
            if not machines:
                messages.error(request, 'Debes seleccionar al menos un equipo.')
                return redirect('operationsCenter:crear_reporte_telemetria')
            
            cliente = Cliente.objects.get(id=cliente_id)
            
            report = TelemetryReport.objects.create(
                cliente=cliente,
                report_type=report_type,
                start_date=start_date,
                end_date=end_date,
                include_location=request.POST.get('include_location') == 'on',
                include_hours=request.POST.get('include_hours') == 'on',
                include_alerts=request.POST.get('include_alerts') == 'on',
                include_usage=request.POST.get('include_usage') == 'on',
            )
            
            # Agregar máquinas al reporte
            for machine_id in machines:
                machine = Machine.objects.get(id=machine_id)
                TelemetryReportMachine.objects.create(
                    report=report,
                    machine=machine
                )
            
            messages.success(request, 'Reporte creado exitosamente.')
            return redirect('operationsCenter:detalle_reporte_telemetria', report_id=report.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear el reporte: {str(e)}')
    
    # Clientes con máquinas
    clients = Cliente.objects.filter(equipos__machines_oc__isnull=False).distinct()
    
    context = {
        'clients': clients,
    }
    
    return render(request, 'operationsCenter/crear_reporte.html', context)


@login_required
def detalle_reporte_telemetria(request, report_id):
    """Detalle de un reporte de telemetría"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('operationsCenter:lista_reportes_telemetria')
    
    report = get_object_or_404(TelemetryReport, id=report_id)
    
    context = {
        'report': report,
    }
    
    return render(request, 'operationsCenter/detalle_reporte.html', context)


@login_required
def api_test_connection(request):
    """Probar conexión con la API de John Deere"""
    if request.user.rol not in ['GERENTE']:
        return JsonResponse({'success': False, 'message': 'No tienes permisos'})
    
    try:
        api_service = JohnDeereAPIService()
        organizations = api_service.get_organizations()
        
        return JsonResponse({
            'success': True,
            'message': 'Conexión exitosa',
            'organizations': organizations.get('values', [])
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error de conexión: {str(e)}'
        })


@login_required
def iniciar_oauth(request):
    """Iniciar el flujo OAuth de John Deere"""
    if request.user.rol not in ['GERENTE']:
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return redirect('operationsCenter:configuracion_oc')
    
    config = OperationsCenterConfig.objects.filter(is_active=True).first()
    if not config:
        messages.error(request, 'No hay configuración activa.')
        return redirect('operationsCenter:configuracion_oc')
    
    # Verificar que tenemos los datos básicos
    if not config.client_id or not config.client_secret or not config.redirect_uri:
        messages.error(request, 'Faltan datos básicos de configuración (Client ID, Secret o Redirect URI).')
        return redirect('operationsCenter:configuracion_oc')
    
    # Parámetros para la autorización OAuth (nueva URL)
    params = {
        'response_type': 'code',
        'client_id': config.client_id,
        'redirect_uri': config.redirect_uri,
        'scope': 'eq1 ag1 org1 offline_access',  # Scopes básicos según la documentación
        'state': 'operations_center_auth',
        'prompt': 'consent'  # Forzar consentimiento
    }
    
    # URL de autorización de John Deere (nueva URL)
    auth_url = f"https://signin.johndeere.com/oauth2/aus78tnlaysMraFhC1t7/v1/authorize?{urlencode(params)}"
    
    # Guardar la URL en la sesión para debugging
    request.session['oauth_auth_url'] = auth_url
    
    print(f"URL de autorización: {auth_url}")  # Para debugging
    
    return redirect(auth_url)


@login_required
def oauth_callback(request):
    """Callback del flujo OAuth de John Deere"""
    if request.user.rol not in ['GERENTE']:
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return redirect('operationsCenter:configuracion_oc')
    
    error = request.GET.get('error')
    if error:
        messages.error(request, f'Error en autorización: {error}')
        return redirect('operationsCenter:configuracion_oc')
    
    code = request.GET.get('code')
    if not code:
        messages.error(request, 'No se recibió código de autorización.')
        return redirect('operationsCenter:configuracion_oc')
    
    config = OperationsCenterConfig.objects.filter(is_active=True).first()
    if not config:
        messages.error(request, 'No hay configuración activa.')
        return redirect('operationsCenter:configuracion_oc')
    
    try:
        # Intercambiar código por tokens (nueva URL)
        token_url = "https://signin.johndeere.com/oauth2/aus78tnlaysMraFhC1t7/v1/token"
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': config.client_id,
            'client_secret': config.client_secret,
            'redirect_uri': config.redirect_uri
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        response = requests.post(token_url, data=token_data, headers=headers)
        
        if response.status_code == 200:
            tokens = response.json()
            
            # Guardar tokens en la configuración
            config.access_token = tokens['access_token']
            config.refresh_token = tokens.get('refresh_token')
            config.token_expires_at = timezone.now() + timedelta(seconds=tokens.get('expires_in', 43200))  # 12 horas
            config.save()
            
            messages.success(request, 'Autenticación exitosa. Tokens guardados.')
            
            # Intentar obtener organizaciones
            try:
                api_service = JohnDeereAPIService()
                organizations = api_service.get_organizations()
                if organizations.get('values'):
                    # Guardar la primera organización
                    org = organizations['values'][0]
                    config.organization_id = org['id']
                    config.save()
                    messages.success(request, f'Organización configurada: {org.get("name", org["id"])}')
            except Exception as e:
                messages.warning(request, f'Autenticación exitosa pero no se pudo obtener organizaciones: {str(e)}')
            
        else:
            messages.error(request, f'Error al obtener tokens: {response.text}')
            
    except Exception as e:
        messages.error(request, f'Error en el proceso de autenticación: {str(e)}')
    
    return redirect('operationsCenter:configuracion_oc')


@login_required
def debug_oauth_config(request):
    """Vista de debugging para verificar la configuración OAuth"""
    if request.user.rol not in ['GERENTE']:
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('operationsCenter:configuracion_oc')
    
    config = OperationsCenterConfig.objects.filter(is_active=True).first()
    
    if request.method == 'POST':
        # Probar la URL de autorización manualmente
        if not config:
            messages.error(request, 'No hay configuración activa.')
            return redirect('operationsCenter:debug_oauth_config')
        
        params = {
            'response_type': 'code',
            'client_id': config.client_id,
            'redirect_uri': config.redirect_uri,
            'scope': 'eq1 ag1 org1 offline_access',
            'state': 'operations_center_auth',
            'prompt': 'consent'
        }
        
        auth_url = f"https://signin.johndeere.com/oauth2/aus78tnlaysMraFhC1t7/v1/authorize?{urlencode(params)}"
        
        # Probar la URL con requests
        try:
            import requests
            response = requests.get(auth_url, allow_redirects=False)
            
            if response.status_code == 302:
                messages.success(request, f'URL válida. Redirección a: {response.headers.get("Location", "No especificada")}')
            elif response.status_code == 200:
                messages.info(request, 'URL válida. Página de autorización cargada correctamente.')
            else:
                messages.error(request, f'Error en URL. Status: {response.status_code}, Response: {response.text[:200]}')
                
        except Exception as e:
            messages.error(request, f'Error al probar URL: {str(e)}')
    
    context = {
        'config': config,
        'auth_url': request.session.get('oauth_auth_url', ''),
    }
    
    return render(request, 'operationsCenter/debug_oauth.html', context)


@login_required
def habilitar_conexiones_organizaciones(request):
    """Habilitar conexiones con organizaciones en Operations Center"""
    if request.user.rol not in ['GERENTE']:
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return redirect('operationsCenter:configuracion_oc')
    
    config = OperationsCenterConfig.objects.filter(is_active=True).first()
    if not config:
        messages.error(request, 'No hay configuración activa.')
        return redirect('operationsCenter:configuracion_oc')
    
    try:
        # Obtener organizaciones
        api_service = JohnDeereAPIService()
        organizations = api_service.get_organizations()
        
        # Buscar organizaciones que necesitan conexión
        orgs_needing_connection = []
        for org in organizations.get('values', []):
            links = org.get('links', [])
            has_connections_link = any(link.get('rel') == 'connections' for link in links)
            if has_connections_link:
                orgs_needing_connection.append(org)
        
        if orgs_needing_connection:
            # Construir URL de conexión
            redirect_uri = 'http://localhost:8000/operations-center/callback/'
            encoded_redirect = requests.utils.quote(redirect_uri, safe='')
            connection_url = f"https://connections.deere.com/connections/{config.client_id}/select-organizations?redirect_uri={encoded_redirect}"
            
            messages.info(request, f'Se encontraron {len(orgs_needing_connection)} organizaciones que necesitan conexión.')
            return redirect(connection_url)
        else:
            messages.success(request, 'Todas las organizaciones ya están conectadas.')
            return redirect('operationsCenter:configuracion_oc')
            
    except Exception as e:
        messages.error(request, f'Error al verificar organizaciones: {str(e)}')
        return redirect('operationsCenter:configuracion_oc')


@login_required
def verificar_estado_conexiones(request):
    """Verificar el estado de las conexiones con organizaciones"""
    if request.user.rol not in ['GERENTE']:
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('operationsCenter:configuracion_oc')
    
    config = OperationsCenterConfig.objects.filter(is_active=True).first()
    if not config:
        messages.error(request, 'No hay configuración activa.')
        return redirect('operationsCenter:configuracion_oc')
    
    try:
        # Obtener organizaciones
        api_service = JohnDeereAPIService()
        organizations = api_service.get_organizations()
        
        # Analizar el estado de las conexiones
        orgs_status = []
        total_orgs = len(organizations.get('values', []))
        connected_orgs = 0
        pending_orgs = 0
        
        for org in organizations.get('values', []):
            links = org.get('links', [])
            has_connections_link = any(link.get('rel') == 'connections' for link in links)
            has_manage_connections_link = any(link.get('rel') == 'manage_connections' for link in links)
            
            if has_manage_connections_link:
                status = 'Conectada'
                connected_orgs += 1
            elif has_connections_link:
                status = 'Pendiente'
                pending_orgs += 1
            else:
                status = 'Desconocido'
            
            orgs_status.append({
                'name': org.get('name', 'Sin nombre'),
                'id': org.get('id', 'Sin ID'),
                'status': status,
                'type': org.get('type', 'Desconocido')
            })
        
        context = {
            'config': config,
            'organizations': orgs_status,
            'total_orgs': total_orgs,
            'connected_orgs': connected_orgs,
            'pending_orgs': pending_orgs,
            'connection_percentage': (connected_orgs / total_orgs * 100) if total_orgs > 0 else 0
        }
        
        return render(request, 'operationsCenter/estado_conexiones.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al verificar conexiones: {str(e)}')
        return redirect('operationsCenter:configuracion_oc')


@login_required
def api_machines_by_client(request, client_id):
    """API para obtener máquinas de un cliente específico"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        return JsonResponse({'success': False, 'message': 'No tienes permisos'})
    
    try:
        machines = Machine.objects.filter(
            equipo_local__cliente_id=client_id,
            is_active=True
        ).select_related('equipo_local__cliente')
        
        machines_data = []
        for machine in machines:
            machines_data.append({
                'id': machine.id,
                'machine_id': machine.machine_id,
                'serial_number': machine.serial_number,
                'make_name': machine.make_name,
                'model_name': machine.model_name,
                'is_active': machine.is_active,
                'has_active_alerts': machine.has_active_alerts(),
                'equipo_local': {
                    'cliente': {
                        'razon_social': machine.equipo_local.cliente.razon_social
                    }
                } if machine.equipo_local else None
            })
        
        return JsonResponse({
            'success': True,
            'machines': machines_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
