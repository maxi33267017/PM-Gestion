from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import AlertaEquipo, LeadJohnDeere, AsignacionAlerta
from clientes.models import Cliente, Equipo
from recursosHumanos.models import Usuario, Sucursal

# Create your views here.

@login_required
def dashboard(request):
    """Vista principal del Centro de Soluciones Conectadas"""
    # Obtener estadísticas según el rol del usuario
    if request.user.rol in ['GERENTE', 'ADMINISTRATIVO']:
        # Para gerentes/administrativos: ver todas las alertas de su sucursal
        alertas_pendientes = AlertaEquipo.objects.filter(
            estado='PENDIENTE',
            sucursal=request.user.sucursal
        ).count()
        alertas_asignadas = AlertaEquipo.objects.filter(
            estado='ASIGNADA',
            sucursal=request.user.sucursal
        ).count()
        leads_nuevos = LeadJohnDeere.objects.filter(
            estado='NUEVO',
            sucursal=request.user.sucursal
        ).count()
    else:
        # Para técnicos: ver solo sus alertas asignadas
        alertas_pendientes = AlertaEquipo.objects.filter(
            tecnico_asignado=request.user,
            estado='ASIGNADA'
        ).count()
        alertas_asignadas = AlertaEquipo.objects.filter(
            tecnico_asignado=request.user,
            estado='EN_PROCESO'
        ).count()
        leads_nuevos = 0  # Los técnicos no ven leads
    
    context = {
        'alertas_pendientes': alertas_pendientes,
        'alertas_asignadas': alertas_asignadas,
        'leads_nuevos': leads_nuevos,
    }
    
    return render(request, 'centroSoluciones/dashboard.html', context)

@login_required
def alertas_list(request):
    """Lista de alertas con filtros según el rol del usuario"""
    
    # Filtrar alertas según el rol
    if request.user.rol in ['GERENTE', 'ADMINISTRATIVO']:
        # Gerentes/Administrativos ven todas las alertas de su sucursal
        alertas = AlertaEquipo.objects.filter(sucursal=request.user.sucursal)
    else:
        # Técnicos ven solo sus alertas asignadas
        alertas = AlertaEquipo.objects.filter(tecnico_asignado=request.user)
    
    # Aplicar filtros
    estado = request.GET.get('estado')
    clasificacion = request.GET.get('clasificacion')
    search = request.GET.get('search')
    
    if estado:
        alertas = alertas.filter(estado=estado)
    if clasificacion:
        alertas = alertas.filter(clasificacion=clasificacion)
    if search:
        alertas = alertas.filter(
            Q(cliente__razon_social__icontains=search) |
            Q(pin_equipo__icontains=search) |
            Q(codigo__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    # Ordenar por fecha (más recientes primero)
    alertas = alertas.order_by('-fecha')
    
    # Paginación
    paginator = Paginator(alertas, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'estado_filtro': estado,
        'clasificacion_filtro': clasificacion,
        'search_filtro': search,
        'es_admin': request.user.rol in ['GERENTE', 'ADMINISTRATIVO'],
    }
    
    return render(request, 'centroSoluciones/alertas_list.html', context)

@login_required
def alerta_detail(request, alerta_id):
    """Detalle de una alerta específica"""
    
    # Obtener la alerta
    if request.user.rol in ['GERENTE', 'ADMINISTRATIVO']:
        alerta = get_object_or_404(AlertaEquipo, id=alerta_id, sucursal=request.user.sucursal)
    else:
        alerta = get_object_or_404(AlertaEquipo, id=alerta_id, tecnico_asignado=request.user)
    
    context = {
        'alerta': alerta,
        'es_admin': request.user.rol in ['GERENTE', 'ADMINISTRATIVO'],
    }
    
    return render(request, 'centroSoluciones/alerta_detail.html', context)

@login_required
def procesar_alerta(request, alerta_id):
    """Vista para que los técnicos procesen sus alertas asignadas"""
    
    if request.user.rol not in ['TECNICO']:
        messages.error(request, 'Solo los técnicos pueden procesar alertas.')
        return redirect('centroSoluciones:alertas_list')
    
    alerta = get_object_or_404(AlertaEquipo, id=alerta_id, tecnico_asignado=request.user)
    
    if request.method == 'POST':
        # Procesar el formulario
        estado = request.POST.get('estado')
        observaciones = request.POST.get('observaciones_tecnico')
        
        if estado in ['EN_PROCESO', 'RESUELTA']:
            alerta.estado = estado
            alerta.observaciones_tecnico = observaciones
            alerta.save()
            
            messages.success(request, f'Alerta {alerta.codigo} actualizada correctamente.')
            return redirect('centroSoluciones:alertas_list')
    
    context = {
        'alerta': alerta,
    }
    
    return render(request, 'centroSoluciones/procesar_alerta.html', context)

@login_required
@require_http_methods(["POST"])
def crear_alerta(request):
    """Vista para crear una nueva alerta desde un modal"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        return JsonResponse({'success': False, 'message': 'No tienes permisos para crear alertas'})
    
    try:
        # Obtener datos del formulario
        cliente_id = request.POST.get('cliente')
        pin_equipo = request.POST.get('pin_equipo')
        clasificacion = request.POST.get('clasificacion')
        codigo = request.POST.get('codigo')
        descripcion = request.POST.get('descripcion')
        tecnico_id = request.POST.get('tecnico_asignado')
        
        # Validar datos requeridos
        if not all([cliente_id, pin_equipo, clasificacion, codigo, descripcion]):
            return JsonResponse({'success': False, 'message': 'Todos los campos son obligatorios'})
        
        # Obtener objetos relacionados
        cliente = get_object_or_404(Cliente, id=cliente_id)
        tecnico = None
        if tecnico_id:
            tecnico = get_object_or_404(Usuario, id=tecnico_id, rol='TECNICO')
        
        # Crear la alerta
        alerta = AlertaEquipo.objects.create(
            cliente=cliente,
            pin_equipo=pin_equipo,
            clasificacion=clasificacion,
            codigo=codigo,
            descripcion=descripcion,
            sucursal=request.user.sucursal,
            tecnico_asignado=tecnico,
            creado_por=request.user
        )
        
        # Si se asignó un técnico, actualizar estado
        if tecnico:
            alerta.estado = 'ASIGNADA'
            alerta.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Alerta {alerta.codigo} creada exitosamente',
            'alerta_id': alerta.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al crear la alerta: {str(e)}'})

@login_required
@require_http_methods(["POST"])
def crear_lead(request):
    """Vista para crear un nuevo lead desde un modal"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        return JsonResponse({'success': False, 'message': 'No tienes permisos para crear leads'})
    
    try:
        # Obtener datos del formulario
        cliente_id = request.POST.get('cliente')
        equipo_id = request.POST.get('equipo')
        clasificacion = request.POST.get('clasificacion')
        descripcion = request.POST.get('descripcion')
        valor_estimado = request.POST.get('valor_estimado')
        
        # Validar datos requeridos
        if not all([cliente_id, equipo_id, clasificacion, descripcion]):
            return JsonResponse({'success': False, 'message': 'Todos los campos son obligatorios'})
        
        # Obtener objetos relacionados
        cliente = get_object_or_404(Cliente, id=cliente_id)
        equipo = get_object_or_404(Equipo, id=equipo_id)
        
        # Convertir valor estimado
        valor = None
        if valor_estimado:
            try:
                valor = float(valor_estimado)
            except ValueError:
                return JsonResponse({'success': False, 'message': 'El valor estimado debe ser un número válido'})
        
        # Crear el lead
        lead = LeadJohnDeere.objects.create(
            cliente=cliente,
            equipo=equipo,
            clasificacion=clasificacion,
            descripcion=descripcion,
            valor_estimado=valor,
            sucursal=request.user.sucursal,
            creado_por=request.user
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Lead creado exitosamente para {cliente.razon_social}',
            'lead_id': lead.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al crear el lead: {str(e)}'})

@login_required
def obtener_equipos_cliente(request):
    """Vista para obtener equipos de un cliente específico (AJAX)"""
    cliente_id = request.GET.get('cliente_id')
    if not cliente_id:
        return JsonResponse({'success': False, 'message': 'ID de cliente requerido'})
    
    try:
        equipos = Equipo.objects.filter(cliente_id=cliente_id).values('id', 'numero_serie', 'modelo__nombre')
        return JsonResponse({
            'success': True,
            'equipos': list(equipos)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al obtener equipos: {str(e)}'})

@login_required
def obtener_pins_equipos_cliente(request):
    """Vista para obtener PINs de equipos de un cliente específico (AJAX)"""
    cliente_id = request.GET.get('cliente_id')
    if not cliente_id:
        return JsonResponse({'success': False, 'message': 'ID de cliente requerido'})
    
    try:
        equipos = Equipo.objects.filter(cliente_id=cliente_id).values('numero_serie')
        pins = [{'pin': equipo['numero_serie']} for equipo in equipos]
        return JsonResponse({
            'success': True,
            'pins': pins
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al obtener PINs: {str(e)}'})

@login_required
def obtener_tecnicos(request):
    """Vista para obtener técnicos disponibles (AJAX)"""
    try:
        tecnicos = Usuario.objects.filter(
            rol='TECNICO',
            sucursal=request.user.sucursal,
            is_active=True
        ).values('id', 'first_name', 'last_name')
        return JsonResponse({
            'success': True,
            'tecnicos': list(tecnicos)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al obtener técnicos: {str(e)}'})

@login_required
def obtener_clientes(request):
    """Vista para obtener clientes disponibles (AJAX)"""
    try:
        clientes = Cliente.objects.filter(
            sucursal=request.user.sucursal
        ).values('id', 'razon_social', 'cuit')
        return JsonResponse({
            'success': True,
            'clientes': list(clientes)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al obtener clientes: {str(e)}'})

@login_required
def leads_list(request):
    """Lista de leads con filtros según el rol del usuario"""
    
    # Solo gerentes y administrativos pueden ver leads
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para ver leads.')
        return redirect('centroSoluciones:centro_soluciones_dashboard')
    
    # Filtrar leads por sucursal
    leads = LeadJohnDeere.objects.filter(sucursal=request.user.sucursal)
    
    # Aplicar filtros
    estado = request.GET.get('estado')
    clasificacion = request.GET.get('clasificacion')
    search = request.GET.get('search')
    
    if estado:
        leads = leads.filter(estado=estado)
    if clasificacion:
        leads = leads.filter(clasificacion=clasificacion)
    if search:
        leads = leads.filter(
            Q(cliente__razon_social__icontains=search) |
            Q(equipo__numero_serie__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    # Ordenar por fecha (más recientes primero)
    leads = leads.order_by('-fecha')
    
    # Paginación
    paginator = Paginator(leads, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'estado_filtro': estado,
        'clasificacion_filtro': clasificacion,
        'search_filtro': search,
    }
    
    return render(request, 'centroSoluciones/leads_list.html', context)
