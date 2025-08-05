from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Q, Count, Max, DecimalField, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from clientes.models import Cliente
from gestionDeTaller.models import Servicio
from .models import AnalisisCliente, Campania, PaqueteServicio, ClientePaquete, Contacto, SugerenciaMejora, EmbudoVentas, Campana, ContactoCliente
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from recursosHumanos.models import Sucursal
import csv

# ===== FUNCIONES HELPER PARA ANÁLISIS DE CLIENTES =====

def calcular_comportamiento_cliente(ultimo_servicio):
    """
    Calcula el comportamiento de un cliente basado en su último servicio
    """
    if not ultimo_servicio:
        return 'INACTIVO'
    
    dias_desde_ultimo = (timezone.now().date() - ultimo_servicio).days
    
    if dias_desde_ultimo <= 90:
        return 'ACTIVO'
    elif dias_desde_ultimo <= 365:
        return 'CRECIMIENTO'
    elif dias_desde_ultimo <= 730:
        return 'COMPORTAMIENTO_BAJISTA'
    else:
        return 'INACTIVO'

def calcular_facturacion_cliente(servicios):
    """
    Calcula la facturación total de un cliente usando las funciones helper
    """
    from reportes.views import calcular_gastos_servicios, calcular_repuestos_servicios
    
    facturacion_total = 0
    
    # Calcular mano de obra
    for servicio in servicios:
        valor_mano_obra = servicio.valor_mano_obra or 0
        facturacion_total += valor_mano_obra
    
    # Calcular gastos y repuestos usando las funciones helper
    total_gastos = calcular_gastos_servicios(servicios)
    total_repuestos = calcular_repuestos_servicios(servicios)
    
    return facturacion_total + total_gastos + total_repuestos

def obtener_clientes_analizados(periodo_dias=365, sucursal_id=None, comportamiento=None, solo_activos=True):
    """
    Función helper que obtiene y analiza clientes con comportamiento y facturación
    Retorna: lista de diccionarios con datos de clientes analizados
    """
    fecha_limite = timezone.now().date() - timedelta(days=periodo_dias)
    
    # Base queryset de clientes
    clientes_queryset = Cliente.objects.all()
    
    # Aplicar filtros
    if solo_activos:
        clientes_queryset = clientes_queryset.filter(activo=True)
    
    if sucursal_id:
        clientes_queryset = clientes_queryset.filter(sucursal_id=sucursal_id)
    
    # Anotar con datos básicos
    clientes_con_datos = clientes_queryset.annotate(
        total_servicios=Count(
            'preorden__servicio',
            filter=Q(
                preorden__servicio__fecha_servicio__gte=fecha_limite,
                preorden__servicio__estado='COMPLETADO'
            ),
            distinct=True
        ),
        ultimo_servicio=Max('preorden__servicio__fecha_servicio'),
        equipos_activos=Count('equipos', filter=Q(equipos__activo=True), distinct=True),
        paquetes_activos=Count('paquetes', filter=Q(paquetes__estado='ACTIVO'), distinct=True)
    )
    
    # Analizar cada cliente
    clientes_analizados = []
    for cliente in clientes_con_datos:
        # Calcular comportamiento
        comportamiento_cliente = calcular_comportamiento_cliente(cliente.ultimo_servicio)
        
        # Aplicar filtro de comportamiento si se especifica
        if comportamiento and comportamiento_cliente != comportamiento:
            continue
        
        # Obtener servicios del cliente
        servicios = Servicio.objects.filter(
            preorden__cliente=cliente,
            fecha_servicio__gte=fecha_limite,
            estado='COMPLETADO'
        )
        
        # Calcular facturación
        facturacion_total = calcular_facturacion_cliente(servicios)
        
        # Calcular días desde último servicio
        dias_desde_ultimo = None
        if cliente.ultimo_servicio:
            dias_desde_ultimo = (timezone.now().date() - cliente.ultimo_servicio).days
        
        clientes_analizados.append({
            'cliente': cliente,
            'comportamiento': comportamiento_cliente,
            'dias_desde_ultimo': dias_desde_ultimo,
            'facturacion_total': facturacion_total,
            'total_servicios': cliente.total_servicios,
            'equipos_activos': cliente.equipos_activos,
            'paquetes_activos': cliente.paquetes_activos,
            'ultimo_servicio': cliente.ultimo_servicio
        })
    
    return clientes_analizados

def segmentar_clientes_abc(clientes_analizados):
    """
    Segmenta clientes en ABC basado en su facturación
    Retorna: lista de clientes segmentados con información adicional
    """
    # Filtrar solo clientes con facturación
    clientes_con_facturacion = [c for c in clientes_analizados if c['facturacion_total'] > 0]
    total_facturacion = sum(cliente['facturacion_total'] for cliente in clientes_con_facturacion)
    
    # Segmentar clientes
    clientes_segmentados = []
    acumulado = 0
    
    for cliente_data in clientes_con_facturacion:
        cliente = cliente_data['cliente']
        porcentaje_acumulado = (acumulado / total_facturacion * 100) if total_facturacion > 0 else 0
        
        # Determinar segmento ABC
        if porcentaje_acumulado < 80:
            segmento = 'A'
        elif porcentaje_acumulado < 95:
            segmento = 'B'
        else:
            segmento = 'C'
        
        # Calcular potencial estimado
        potencial_estimado = cliente.equipos_activos * 5000  # USD promedio por equipo por año
        
        clientes_segmentados.append({
            'cliente': cliente,
            'segmento': segmento,
            'comportamiento': cliente_data['comportamiento'],
            'total_facturacion': cliente_data['facturacion_total'],
            'total_servicios': cliente_data['total_servicios'],
            'equipos_activos': cliente_data['equipos_activos'],
            'potencial_estimado': potencial_estimado,
            'porcentaje_acumulado': porcentaje_acumulado,
            'ultimo_servicio': cliente_data['ultimo_servicio'],
            'dias_desde_ultimo': cliente_data['dias_desde_ultimo']
        })
        
        acumulado += cliente_data['facturacion_total']
    
    # Agregar clientes sin facturación como "NUEVO"
    for cliente_data in clientes_analizados:
        if cliente_data['facturacion_total'] == 0:
            clientes_segmentados.append({
                'cliente': cliente_data['cliente'],
                'segmento': 'NUEVO',
                'comportamiento': cliente_data['comportamiento'],
                'total_facturacion': 0,
                'total_servicios': cliente_data['total_servicios'],
                'equipos_activos': cliente_data['equipos_activos'],
                'potencial_estimado': cliente_data['equipos_activos'] * 5000,
                'porcentaje_acumulado': 0,
                'ultimo_servicio': cliente_data['ultimo_servicio'],
                'dias_desde_ultimo': cliente_data['dias_desde_ultimo']
            })
    
    return clientes_segmentados, total_facturacion

def calcular_estadisticas_generales(clientes_analizados):
    """
    Calcula estadísticas generales para los clientes analizados
    """
    total_clientes = len(clientes_analizados)
    clientes_activos = len([c for c in clientes_analizados if c['comportamiento'] == 'ACTIVO'])
    clientes_inactivos = len([c for c in clientes_analizados if c['comportamiento'] == 'INACTIVO'])
    facturacion_total = sum(c['facturacion_total'] for c in clientes_analizados)
    
    # Distribución por comportamiento
    distribucion_comportamiento = {}
    for comportamiento in ['ACTIVO', 'CRECIMIENTO', 'COMPORTAMIENTO_BAJISTA', 'INACTIVO']:
        count = len([c for c in clientes_analizados if c['comportamiento'] == comportamiento])
        distribucion_comportamiento[comportamiento] = count
    
    return {
        'total_clientes': total_clientes,
        'clientes_activos': clientes_activos,
        'clientes_inactivos': clientes_inactivos,
        'facturacion_total': facturacion_total,
        'distribucion_comportamiento': distribucion_comportamiento,
    }

def identificar_oportunidades_venta(clientes_analizados):
    """
    Identifica oportunidades de venta basadas en el análisis de clientes
    """
    oportunidades = []
    
    for cliente_data in clientes_analizados:
        cliente = cliente_data['cliente']
        comportamiento = cliente_data['comportamiento']
        equipos_activos = cliente_data['equipos_activos']
        
        # Oportunidades por comportamiento
        if comportamiento == 'INACTIVO':
            oportunidades.append({
                'cliente': cliente,
                'tipo': 'REACTIVACION',
                'descripcion': 'Cliente inactivo - oportunidad de reactivación',
                'prioridad': 'ALTA',
                'valor_potencial': equipos_activos * 3000,  # USD estimado por reactivación
                'comportamiento': comportamiento
            })
        elif comportamiento == 'COMPORTAMIENTO_BAJISTA':
            oportunidades.append({
                'cliente': cliente,
                'tipo': 'RETENCION',
                'descripcion': 'Cliente con comportamiento bajista - estrategia de retención',
                'prioridad': 'MEDIA',
                'valor_potencial': equipos_activos * 2000,  # USD estimado por retención
                'comportamiento': comportamiento
            })
        
        # Oportunidades por equipos activos
        if equipos_activos > 0 and cliente_data['facturacion_total'] < (equipos_activos * 2000):
            oportunidades.append({
                'cliente': cliente,
                'tipo': 'CRECIMIENTO',
                'descripcion': f'Cliente con {equipos_activos} equipos activos pero baja facturación',
                'prioridad': 'MEDIA',
                'valor_potencial': equipos_activos * 1500,  # USD estimado por crecimiento
                'comportamiento': comportamiento
            })
    
    # Ordenar por prioridad y valor potencial
    oportunidades.sort(key=lambda x: (x['prioridad'] == 'ALTA', x['valor_potencial']), reverse=True)
    
    return oportunidades

# Create your views here.
@login_required
def crm(request):
    # Obtener campañas activas
    campanias = Campania.objects.filter(estado='EN_CURSO')
    
    context = {
        'campanias': campanias,
    }
    return render(request, 'crm/crm.html', context)

@login_required
def segmentacion_clientes(request):
    """Vista para mostrar la segmentación ABC de clientes"""
    
    # Obtener filtros
    periodo_dias = int(request.GET.get('periodo_dias', 365))
    sucursal_id = request.GET.get('sucursal', '')
    comportamiento = request.GET.get('comportamiento', '')
    segmento_filtro = request.GET.get('segmento', '')
    solo_activos = request.GET.get('solo_activos', 'true') == 'true'
    
    # Usar la función helper para obtener clientes analizados
    clientes_analizados = obtener_clientes_analizados(
        periodo_dias=periodo_dias,
        sucursal_id=sucursal_id,
        comportamiento=comportamiento,
        solo_activos=solo_activos
    )
    
    # Usar la función helper para segmentar clientes
    clientes_segmentados, total_facturacion = segmentar_clientes_abc(clientes_analizados)
    
    # Aplicar filtro de segmento si se especifica
    if segmento_filtro:
        clientes_segmentados = [c for c in clientes_segmentados if c['segmento'] == segmento_filtro]
    
    # Calcular estadísticas por segmento
    estadisticas_segmentos = {}
    for segmento in ['A', 'B', 'C', 'NUEVO']:
        clientes_segmento = [c for c in clientes_segmentados if c['segmento'] == segmento]
        if clientes_segmento:
            facturacion_total = sum(c['total_facturacion'] for c in clientes_segmento)
            estadisticas_segmentos[segmento] = {
                'cantidad': len(clientes_segmento),
                'facturacion_total': facturacion_total,
                'facturacion_promedio': facturacion_total / len(clientes_segmento) if len(clientes_segmento) > 0 else 0,
                'servicios_promedio': sum(c['total_servicios'] for c in clientes_segmento) / len(clientes_segmento) if len(clientes_segmento) > 0 else 0,
                'porcentaje_del_total': (facturacion_total / total_facturacion * 100) if total_facturacion > 0 else 0,
            }
    
    # Estadísticas por comportamiento
    estadisticas_comportamiento = {}
    for comportamiento in ['ACTIVO', 'CRECIMIENTO', 'COMPORTAMIENTO_BAJISTA', 'INACTIVO']:
        clientes_comportamiento = [c for c in clientes_segmentados if c['comportamiento'] == comportamiento]
        if clientes_comportamiento:
            facturacion_total = sum(c['total_facturacion'] for c in clientes_comportamiento)
            estadisticas_comportamiento[comportamiento] = {
                'cantidad': len(clientes_comportamiento),
                'facturacion_total': facturacion_total,
                'porcentaje_del_total': (facturacion_total / total_facturacion * 100) if total_facturacion > 0 else 0,
            }
    
    # Calcular promedio por cliente
    clientes_con_facturacion = [c for c in clientes_segmentados if c['total_facturacion'] > 0]
    promedio_por_cliente = total_facturacion / len(clientes_con_facturacion) if clientes_con_facturacion else 0
    
    # Obtener todas las sucursales para el filtro
    sucursales = Sucursal.objects.filter(activo=True).order_by('nombre')
    
    # Calcular fecha límite para el contexto
    fecha_limite = timezone.now().date() - timedelta(days=periodo_dias)
    
    context = {
        'clientes_segmentados': clientes_segmentados,
        'estadisticas_segmentos': estadisticas_segmentos,
        'estadisticas_comportamiento': estadisticas_comportamiento,
        'periodo_dias': periodo_dias,
        'fecha_limite': fecha_limite,
        'total_facturacion': total_facturacion,
        'promedio_por_cliente': promedio_por_cliente,
        'sucursal_id': sucursal_id,
        'segmento_filtro': segmento_filtro,
        'solo_activos': solo_activos,
        'sucursales': sucursales,
    }
    return render(request, 'crm/segmentacion_clientes.html', context)

# Vistas para Portfolio de Paquetes
@login_required
def portfolio_paquetes(request):
    """Vista para listar todos los paquetes de servicios"""
    estado = request.GET.get('estado', '')
    
    paquetes = PaqueteServicio.objects.all()
    if estado:
        paquetes = paquetes.filter(estado=estado)
    
    # Anotar con estadísticas
    paquetes = paquetes.annotate(
        clientes_activos=Count('clientes', filter=Q(clientes__estado='ACTIVO')),
        total_ingresos=Sum('clientes__paquete__precio', filter=Q(clientes__estado='ACTIVO'))
    ).order_by('-fecha_creacion')
    
    # Calcular estadísticas adicionales
    paquetes_activos_count = paquetes.filter(estado='ACTIVO').count()
    
    context = {
        'paquetes': paquetes,
        'estado_filtro': estado,
        'paquetes_activos_count': paquetes_activos_count,
    }
    return render(request, 'crm/portfolio_paquetes.html', context)

@login_required
def crear_paquete(request):
    """Vista para crear un nuevo paquete de servicio"""
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        precio = request.POST.get('precio')
        estado = request.POST.get('estado', 'ACTIVO')
        servicios_ids = request.POST.getlist('servicios')
        
        if nombre and precio:
            try:
                paquete = PaqueteServicio.objects.create(
                    nombre=nombre,
                    descripcion=descripcion,
                    precio=precio,
                    estado=estado
                )
                
                # Asignar servicios seleccionados
                if servicios_ids:
                    servicios = Servicio.objects.filter(id__in=servicios_ids)
                    paquete.servicios.set(servicios)
                
                messages.success(request, f'Paquete "{nombre}" creado exitosamente.')
                return redirect('portfolio_paquetes')
            except Exception as e:
                messages.error(request, f'Error al crear el paquete: {str(e)}')
        else:
            messages.error(request, 'Por favor complete todos los campos requeridos.')
    
    # Obtener servicios disponibles para el formulario
    servicios = Servicio.objects.filter(estado='COMPLETADO').order_by('-fecha_servicio')[:50]
    
    context = {
        'servicios': servicios,
    }
    return render(request, 'crm/crear_paquete.html', context)

@login_required
def editar_paquete(request, paquete_id):
    """Vista para editar un paquete existente"""
    paquete = get_object_or_404(PaqueteServicio, id=paquete_id)
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        precio = request.POST.get('precio')
        estado = request.POST.get('estado')
        servicios_ids = request.POST.getlist('servicios')
        
        if nombre and precio:
            try:
                paquete.nombre = nombre
                paquete.descripcion = descripcion
                paquete.precio = precio
                paquete.estado = estado
                paquete.save()
                
                # Actualizar servicios
                if servicios_ids:
                    servicios = Servicio.objects.filter(id__in=servicios_ids)
                    paquete.servicios.set(servicios)
                else:
                    paquete.servicios.clear()
                
                messages.success(request, f'Paquete "{nombre}" actualizado exitosamente.')
                return redirect('portfolio_paquetes')
            except Exception as e:
                messages.error(request, f'Error al actualizar el paquete: {str(e)}')
        else:
            messages.error(request, 'Por favor complete todos los campos requeridos.')
    
    # Obtener servicios disponibles
    servicios = Servicio.objects.filter(estado='COMPLETADO').order_by('-fecha_servicio')[:50]
    
    context = {
        'paquete': paquete,
        'servicios': servicios,
    }
    return render(request, 'crm/editar_paquete.html', context)

@login_required
def asignar_paquete_cliente(request):
    """Vista para asignar un paquete a un cliente"""
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente')
        paquete_id = request.POST.get('paquete')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        
        if cliente_id and paquete_id and fecha_inicio:
            try:
                cliente = Cliente.objects.get(id=cliente_id)
                paquete = PaqueteServicio.objects.get(id=paquete_id)
                
                # Verificar si ya existe una asignación activa
                asignacion_existente = ClientePaquete.objects.filter(
                    cliente=cliente,
                    paquete=paquete,
                    estado='ACTIVO'
                ).first()
                
                if asignacion_existente:
                    messages.warning(request, f'El cliente ya tiene asignado este paquete activo.')
                else:
                    ClientePaquete.objects.create(
                        cliente=cliente,
                        paquete=paquete,
                        fecha_inicio=fecha_inicio,
                        fecha_fin=fecha_fin if fecha_fin else None,
                        estado='ACTIVO'
                    )
                    messages.success(request, f'Paquete "{paquete.nombre}" asignado a "{cliente.razon_social}" exitosamente.')
                
                return redirect('portfolio_paquetes')
            except Exception as e:
                messages.error(request, f'Error al asignar el paquete: {str(e)}')
        else:
            messages.error(request, 'Por favor complete todos los campos requeridos.')
    
    # Obtener datos para el formulario
    clientes = Cliente.objects.filter(activo=True).order_by('razon_social')
    paquetes = PaqueteServicio.objects.filter(estado='ACTIVO').order_by('nombre')
    
    context = {
        'clientes': clientes,
        'paquetes': paquetes,
    }
    return render(request, 'crm/asignar_paquete.html', context)

@login_required
def clientes_por_paquete(request, paquete_id):
    """Vista para ver qué clientes tienen asignado un paquete específico"""
    paquete = get_object_or_404(PaqueteServicio, id=paquete_id)
    asignaciones = ClientePaquete.objects.filter(paquete=paquete).select_related('cliente').order_by('-fecha_inicio')
    
    # Calcular estadísticas
    asignaciones_activas_count = asignaciones.filter(estado='ACTIVO').count()
    ingresos_potenciales = paquete.precio * asignaciones_activas_count
    
    context = {
        'paquete': paquete,
        'asignaciones': asignaciones,
        'asignaciones_activas_count': asignaciones_activas_count,
        'ingresos_potenciales': ingresos_potenciales,
    }
    return render(request, 'crm/clientes_por_paquete.html', context)

# Vistas para Campañas de Marketing
@login_required
def campanias_marketing(request):
    """Vista para listar todas las campañas de marketing"""
    estado = request.GET.get('estado', '')
    
    campanias = Campania.objects.all()
    if estado:
        campanias = campanias.filter(estado=estado)
    
    # Anotar con estadísticas
    campanias = campanias.annotate(
        contactos_count=Count('contactos'),
        ventas_exitosas=Count('contactos', filter=Q(contactos__resultado='VENTA_EXITOSA')),
        ventas_perdidas=Count('contactos', filter=Q(contactos__resultado='VENTA_PERDIDA')),
        pendientes=Count('contactos', filter=Q(contactos__resultado='PENDIENTE'))
    ).order_by('-fecha_inicio')
    
    # Calcular estadísticas adicionales
    campanias_activas_count = campanias.filter(estado='EN_CURSO').count()
    
    context = {
        'campanias': campanias,
        'estado_filtro': estado,
        'campanias_activas_count': campanias_activas_count,
    }
    return render(request, 'crm/campanias_marketing.html', context)

@login_required
def crear_campania(request):
    """Vista para crear una nueva campaña de marketing"""
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        valor_paquete = request.POST.get('valor_paquete')
        objetivo_paquetes = request.POST.get('objetivo_paquetes')
        estado = request.POST.get('estado', 'PLANIFICADA')
        
        if nombre and fecha_inicio and fecha_fin and valor_paquete and objetivo_paquetes:
            try:
                campania = Campania.objects.create(
                    nombre=nombre,
                    descripcion=descripcion,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    valor_paquete=valor_paquete,
                    objetivo_paquetes=objetivo_paquetes,
                    estado=estado
                )
                
                messages.success(request, f'Campaña "{nombre}" creada exitosamente.')
                return redirect('campanias_marketing')
            except Exception as e:
                messages.error(request, f'Error al crear la campaña: {str(e)}')
        else:
            messages.error(request, 'Por favor complete todos los campos requeridos.')
    
    context = {}
    return render(request, 'crm/crear_campania.html', context)

@login_required
def editar_campania(request, campania_id):
    """Vista para editar una campaña existente"""
    campania = get_object_or_404(Campania, id=campania_id)
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        valor_paquete = request.POST.get('valor_paquete')
        objetivo_paquetes = request.POST.get('objetivo_paquetes')
        estado = request.POST.get('estado')
        
        if nombre and fecha_inicio and fecha_fin and valor_paquete and objetivo_paquetes:
            try:
                campania.nombre = nombre
                campania.descripcion = descripcion
                campania.fecha_inicio = fecha_inicio
                campania.fecha_fin = fecha_fin
                campania.valor_paquete = valor_paquete
                campania.objetivo_paquetes = objetivo_paquetes
                campania.estado = estado
                campania.save()
                
                messages.success(request, f'Campaña "{nombre}" actualizada exitosamente.')
                return redirect('campanias_marketing')
            except Exception as e:
                messages.error(request, f'Error al actualizar la campaña: {str(e)}')
        else:
            messages.error(request, 'Por favor complete todos los campos requeridos.')
    
    context = {
        'campania': campania,
    }
    return render(request, 'crm/editar_campania.html', context)

@login_required
def gestionar_contactos(request, campania_id):
    """Vista para gestionar contactos de una campaña"""
    campania = get_object_or_404(Campania, id=campania_id)
    
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente')
        fecha_contacto = request.POST.get('fecha_contacto')
        responsable_id = request.POST.get('responsable')
        resultado = request.POST.get('resultado')
        observaciones = request.POST.get('observaciones')
        fecha_seguimiento = request.POST.get('fecha_seguimiento')
        valor_venta = request.POST.get('valor_venta')
        
        if cliente_id and fecha_contacto and responsable_id and resultado:
            try:
                from recursosHumanos.models import Usuario
                cliente = Cliente.objects.get(id=cliente_id)
                responsable = Usuario.objects.get(id=responsable_id)
                
                Contacto.objects.create(
                    campania=campania,
                    cliente=cliente,
                    fecha_contacto=fecha_contacto,
                    responsable=responsable,
                    resultado=resultado,
                    observaciones=observaciones,
                    fecha_seguimiento=fecha_seguimiento if fecha_seguimiento else None,
                    valor_venta=valor_venta if valor_venta else None
                )
                
                messages.success(request, f'Contacto registrado exitosamente para {cliente.razon_social}.')
                return redirect('gestionar_contactos', campania_id=campania_id)
            except Exception as e:
                messages.error(request, f'Error al registrar el contacto: {str(e)}')
        else:
            messages.error(request, 'Por favor complete todos los campos requeridos.')
    
    # Obtener contactos de la campaña
    contactos = Contacto.objects.filter(campania=campania).select_related('cliente', 'responsable').order_by('-fecha_contacto')
    
    # Obtener datos para el formulario
    clientes = Cliente.objects.filter(activo=True).order_by('razon_social')
    from recursosHumanos.models import Usuario
    responsables = Usuario.objects.filter(is_active=True).order_by('nombre')
    
    # Estadísticas de la campaña
    total_contactos = contactos.count()
    ventas_exitosas = contactos.filter(resultado='VENTA_EXITOSA').count()
    ventas_perdidas = contactos.filter(resultado='VENTA_PERDIDA').count()
    pendientes = contactos.filter(resultado='PENDIENTE').count()
    valor_total_ventas = contactos.filter(resultado='VENTA_EXITOSA').aggregate(
        total=Sum('valor_venta')
    )['total'] or 0
    
    context = {
        'campania': campania,
        'contactos': contactos,
        'clientes': clientes,
        'responsables': responsables,
        'total_contactos': total_contactos,
        'ventas_exitosas': ventas_exitosas,
        'ventas_perdidas': ventas_perdidas,
        'pendientes': pendientes,
        'valor_total_ventas': valor_total_ventas,
    }
    return render(request, 'crm/gestionar_contactos.html', context)

@login_required
def dashboard_campania(request, campania_id):
    """Vista para mostrar el dashboard de resultados de una campaña"""
    campania = get_object_or_404(Campania, id=campania_id)
    contactos = Contacto.objects.filter(campania=campania).select_related('cliente', 'responsable')
    
    # Estadísticas detalladas
    total_contactos = contactos.count()
    ventas_exitosas = contactos.filter(resultado='VENTA_EXITOSA').count()
    ventas_perdidas = contactos.filter(resultado='VENTA_PERDIDA').count()
    pendientes = contactos.filter(resultado='PENDIENTE').count()
    reprogramados = contactos.filter(resultado='REPROGRAMADO').count()
    
    valor_total_ventas = contactos.filter(resultado='VENTA_EXITOSA').aggregate(
        total=Sum('valor_venta')
    )['total'] or 0
    
    # Calcular métricas
    tasa_conversion = (ventas_exitosas / total_contactos * 100) if total_contactos > 0 else 0
    cumplimiento_objetivo = (ventas_exitosas / campania.objetivo_paquetes * 100) if campania.objetivo_paquetes > 0 else 0
    
    # Contactos por responsable
    contactos_por_responsable = contactos.values('responsable__nombre').annotate(
        total=Count('id', distinct=True),
        exitosas=Count('id', filter=Q(resultado='VENTA_EXITOSA'), distinct=True),
        perdidas=Count('id', filter=Q(resultado='VENTA_PERDIDA'), distinct=True)
    )
    
    # Contactos por resultado
    contactos_por_resultado = contactos.values('resultado').annotate(
        total=Count('id', distinct=True)
    )
    
    context = {
        'campania': campania,
        'total_contactos': total_contactos,
        'ventas_exitosas': ventas_exitosas,
        'ventas_perdidas': ventas_perdidas,
        'pendientes': pendientes,
        'reprogramados': reprogramados,
        'valor_total_ventas': valor_total_ventas,
        'tasa_conversion': tasa_conversion,
        'cumplimiento_objetivo': cumplimiento_objetivo,
        'contactos_por_responsable': contactos_por_responsable,
        'contactos_por_resultado': contactos_por_resultado,
    }
    return render(request, 'crm/dashboard_campania.html', context)

# Vistas para Análisis de Clientes
@login_required
def analisis_clientes(request):
    """Vista para el dashboard general de análisis de clientes"""
    
    # Parámetros de filtro
    periodo_dias = request.GET.get('periodo', 365)
    segmento = request.GET.get('segmento', '')
    comportamiento = request.GET.get('comportamiento', '')
    solo_activos = request.GET.get('solo_activos', 'true') == 'true'
    
    try:
        periodo_dias = int(periodo_dias)
    except ValueError:
        periodo_dias = 365
    
    # Usar la función helper para obtener clientes analizados
    clientes_analizados = obtener_clientes_analizados(
        periodo_dias=periodo_dias,
        comportamiento=comportamiento,
        solo_activos=solo_activos
    )
    
    # Aplicar filtro de segmento si se especifica
    if segmento:
        # Obtener clientes segmentados para aplicar el filtro
        clientes_segmentados, _ = segmentar_clientes_abc(clientes_analizados)
        clientes_filtrados = [c for c in clientes_segmentados if c['segmento'] == segmento]
        # Extraer solo los datos de cliente de los segmentados
        clientes_analizados = [c for c in clientes_analizados if any(c['cliente'].id == seg['cliente'].id for seg in clientes_filtrados)]
    
    # Usar la función helper para calcular estadísticas
    estadisticas = calcular_estadisticas_generales(clientes_analizados)

    # Top 10 clientes por facturación
    top_clientes = sorted(clientes_analizados, key=lambda x: x['facturacion_total'], reverse=True)[:10]

    # Identificar oportunidades de venta
    oportunidades_venta = identificar_oportunidades_venta(clientes_analizados)

    # Calcular fecha límite para el contexto
    fecha_limite = timezone.now().date() - timedelta(days=periodo_dias)

    context = {
        'clientes_analizados': clientes_analizados,
        'total_clientes': estadisticas['total_clientes'],
        'clientes_activos': estadisticas['clientes_activos'],
        'clientes_inactivos': estadisticas['clientes_inactivos'],
        'facturacion_total': estadisticas['facturacion_total'],
        'distribucion_comportamiento': estadisticas['distribucion_comportamiento'],
        'top_clientes': top_clientes,
        'oportunidades_venta': oportunidades_venta,
        'periodo_dias': periodo_dias,
        'fecha_limite': fecha_limite,
        'segmento_filtro': segmento,
        'comportamiento_filtro': comportamiento,
        'solo_activos': solo_activos,
    }
    return render(request, 'crm/analisis_clientes.html', context)

@login_required
def dashboard_cliente(request, cliente_id):
    """Vista para el dashboard individual de un cliente"""
    cliente = get_object_or_404(Cliente, id=cliente_id)
    
    # Obtener servicios del cliente a través de la relación correcta
    servicios = Servicio.objects.filter(
        preorden__cliente=cliente
    ).select_related('preorden').prefetch_related('gastos', 'repuestos').order_by('-fecha_servicio')
    
    # Calcular total de cada servicio usando las funciones helper
    from reportes.views import calcular_gastos_servicios, calcular_repuestos_servicios
    
    servicios_con_total = []
    for servicio in servicios:
        valor_mano_obra = servicio.valor_mano_obra or 0  # Manejar None como 0
        
        # Calcular gastos y repuestos usando las funciones helper
        servicios_individual = Servicio.objects.filter(id=servicio.id)
        total_gastos = calcular_gastos_servicios(servicios_individual)
        total_repuestos = calcular_repuestos_servicios(servicios_individual)
        
        total_servicio = valor_mano_obra + total_gastos + total_repuestos
        servicios_con_total.append({
            'servicio': servicio,
            'total': total_servicio
        })
    
    # Estadísticas de servicios
    total_servicios = len(servicios_con_total)
    fecha_limite_ano = timezone.now().date() - timedelta(days=365)
    servicios_ultimo_ano = len([s for s in servicios_con_total if s['servicio'].fecha_servicio >= fecha_limite_ano])
    facturacion_total = sum(s['total'] for s in servicios_con_total)
    
    # Análisis de comportamiento
    ultimo_servicio = servicios_con_total[0]['servicio'] if servicios_con_total else None
    if ultimo_servicio:
        # Asegurar que ambos sean date para la comparación
        fecha_actual = timezone.now().date()
        fecha_servicio = ultimo_servicio.fecha_servicio
        if hasattr(fecha_servicio, 'date'):
            fecha_servicio = fecha_servicio.date()
        
        dias_desde_ultimo = (fecha_actual - fecha_servicio).days
        if dias_desde_ultimo <= 90:
            comportamiento = 'ACTIVO'
        elif dias_desde_ultimo <= 365:
            comportamiento = 'CRECIMIENTO'
        elif dias_desde_ultimo <= 730:
            comportamiento = 'COMPORTAMIENTO_BAJISTA'
        else:
            comportamiento = 'INACTIVO'
    else:
        comportamiento = 'INACTIVO'
        dias_desde_ultimo = None
    
    # Equipos del cliente
    equipos = cliente.equipos.filter(activo=True).select_related('modelo')
    
    # Paquetes activos
    paquetes_activos = ClientePaquete.objects.filter(
        cliente=cliente,
        estado='ACTIVO'
    ).select_related('paquete')
    
    # Contactos de campañas
    contactos = Contacto.objects.filter(
        cliente=cliente
    ).select_related('campania', 'responsable').order_by('-fecha_contacto')
    
    # Oportunidades (clientes inactivos o con comportamiento bajista)
    oportunidades = []
    if comportamiento in ['INACTIVO', 'COMPORTAMIENTO_BAJISTA']:
        oportunidades.append({
            'tipo': 'REACTIVACION',
            'descripcion': 'Cliente inactivo - oportunidad de reactivación',
            'prioridad': 'ALTA' if comportamiento == 'INACTIVO' else 'MEDIA'
        })
    
    if not paquetes_activos.exists():
        oportunidades.append({
            'tipo': 'PAQUETE',
            'descripcion': 'Cliente sin paquetes activos - oportunidad de venta',
            'prioridad': 'ALTA'
        })
    
    # Historial de facturación por mes (últimos 12 meses)
    historial_facturacion = []
    for i in range(12):
        fecha = timezone.now() - timedelta(days=30*i)
        servicios_mes = [s for s in servicios_con_total if s['servicio'].fecha_servicio.year == fecha.year and s['servicio'].fecha_servicio.month == fecha.month]
        facturacion_mes = sum(s['total'] for s in servicios_mes)
        
        historial_facturacion.append({
            'mes': fecha.strftime('%b %Y'),
            'facturacion': facturacion_mes
        })
    
    historial_facturacion.reverse()
    
    context = {
        'cliente': cliente,
        'servicios': servicios_con_total[:10],  # Últimos 10 servicios con total
        'total_servicios': total_servicios,
        'servicios_ultimo_ano': servicios_ultimo_ano,
        'facturacion_total': facturacion_total,
        'comportamiento': comportamiento,
        'dias_desde_ultimo': dias_desde_ultimo,
        'equipos': equipos,
        'paquetes_activos': paquetes_activos,
        'contactos': contactos[:5],  # Últimos 5 contactos
        'oportunidades': oportunidades,
        'historial_facturacion': historial_facturacion,
    }
    return render(request, 'crm/dashboard_cliente.html', context)

@login_required
def oportunidades_venta(request):
    """Vista para mostrar oportunidades de venta"""
    
    # Clientes inactivos (sin servicios en más de 1 año)
    fecha_limite_inactivos = timezone.now() - timedelta(days=365)
    clientes_inactivos = Cliente.objects.filter(
        activo=True,
        preorden__servicio__fecha_servicio__lt=fecha_limite_inactivos
    ).distinct().annotate(
        ultimo_servicio=Max('preorden__servicio__fecha_servicio'),
        equipos_activos=Count('equipos', filter=Q(equipos__activo=True))
    )
    
    # Clientes sin paquetes activos
    clientes_sin_paquetes = Cliente.objects.filter(
        activo=True
    ).exclude(
        paquetes__estado='ACTIVO'
    ).annotate(
        equipos_activos=Count('equipos', filter=Q(equipos__activo=True)),
        ultimo_servicio=Max('preorden__servicio__fecha_servicio')
    )
    
    # Clientes con comportamiento bajista (sin servicios en 6-12 meses)
    fecha_limite_bajista = timezone.now() - timedelta(days=180)
    clientes_bajistas = Cliente.objects.filter(
        activo=True,
        preorden__servicio__fecha_servicio__lt=fecha_limite_bajista,
        preorden__servicio__fecha_servicio__gte=fecha_limite_inactivos
    ).distinct().annotate(
        ultimo_servicio=Max('preorden__servicio__fecha_servicio'),
        equipos_activos=Count('equipos', filter=Q(equipos__activo=True))
    )
    
    # Oportunidades por segmento
    oportunidades_segmento_a = []
    oportunidades_segmento_b = []
    oportunidades_segmento_c = []
    
    for cliente in clientes_inactivos:
        try:
            categoria = cliente.analisiscliente.categoria
            if categoria == 'A':
                oportunidades_segmento_a.append(cliente)
            elif categoria == 'B':
                oportunidades_segmento_b.append(cliente)
            else:
                oportunidades_segmento_c.append(cliente)
        except:
            oportunidades_segmento_c.append(cliente)
    
    context = {
        'clientes_inactivos': clientes_inactivos,
        'clientes_sin_paquetes': clientes_sin_paquetes,
        'clientes_bajistas': clientes_bajistas,
        'oportunidades_segmento_a': oportunidades_segmento_a,
        'oportunidades_segmento_b': oportunidades_segmento_b,
        'oportunidades_segmento_c': oportunidades_segmento_c,
    }
    return render(request, 'crm/oportunidades_venta.html', context)

# Vistas para Panel Admin
@login_required
def panel_admin(request):
    """Vista principal del Panel Admin"""
    from recursosHumanos.models import AlertaCronometro, SesionCronometro, Usuario
    
    # Si el usuario es técnico, solo mostrar el buzón de sugerencias
    if request.user.rol == 'TECNICO':
        context = {
            'is_tecnico': True,
            'total_sugerencias': SugerenciaMejora.objects.count(),
            'sugerencias_pendientes': SugerenciaMejora.objects.filter(estado='PENDIENTE').count(),
            'sugerencias_implementadas': SugerenciaMejora.objects.filter(estado='IMPLEMENTADA').count(),
        }
        return render(request, 'crm/panel_admin_tecnico.html', context)
    
    # Para gerentes y administrativos, mostrar el panel completo
    # Estadísticas adicionales
    alertas_activas = AlertaCronometro.objects.filter(
        estado='ENVIADA',
        fecha_envio__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    total_usuarios = Usuario.objects.filter(is_active=True).count()
    
    context = {
        'is_tecnico': False,
        'total_sugerencias': SugerenciaMejora.objects.count(),
        'sugerencias_pendientes': SugerenciaMejora.objects.filter(estado='PENDIENTE').count(),
        'sugerencias_implementadas': SugerenciaMejora.objects.filter(estado='IMPLEMENTADA').count(),
        'alertas_activas': alertas_activas,
        'total_usuarios': total_usuarios,
    }
    return render(request, 'crm/panel_admin.html', context)

@login_required
def buzon_sugerencias(request):
    """Vista para que cualquier usuario pueda enviar sugerencias anónimas"""
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')
        categoria = request.POST.get('categoria')
        impacto_estimado = request.POST.get('impacto_estimado')
        prioridad = request.POST.get('prioridad')
        beneficios_esperados = request.POST.get('beneficios_esperados')
        recursos_necesarios = request.POST.get('recursos_necesarios')
        tiempo_estimado = request.POST.get('tiempo_estimado_implementacion')
        
        if titulo and descripcion:
            try:
                SugerenciaMejora.objects.create(
                    titulo=titulo,
                    descripcion=descripcion,
                    categoria=categoria,
                    impacto_estimado=impacto_estimado,
                    prioridad=prioridad,
                    beneficios_esperados=beneficios_esperados,
                    recursos_necesarios=recursos_necesarios,
                    tiempo_estimado_implementacion=tiempo_estimado
                )
                messages.success(request, '¡Tu sugerencia ha sido enviada exitosamente! Gracias por contribuir a mejorar nuestro taller.')
                return redirect('buzon_sugerencias')
            except Exception as e:
                messages.error(request, f'Error al enviar la sugerencia: {str(e)}')
        else:
            messages.error(request, 'Por favor complete el título y descripción de la sugerencia.')
    
    # Mostrar sugerencias recientes (solo las aprobadas e implementadas)
    sugerencias_recientes = SugerenciaMejora.objects.filter(
        estado__in=['APROBADA', 'IMPLEMENTADA']
    ).order_by('-fecha_sugerencia')[:5]
    
    context = {
        'sugerencias_recientes': sugerencias_recientes,
    }
    return render(request, 'crm/buzon_sugerencias.html', context)

@login_required
@login_required
def gestionar_sugerencias(request):
    """Vista para que gerentes y administradores gestionen las sugerencias"""
    # Debug: imprimir información del usuario
    print(f"Usuario: {request.user.email}, Rol: {request.user.rol}, Staff: {request.user.is_staff}")
    
    # Verificar permisos (solo gerentes y administrativos)
    if not request.user.is_staff and request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('crm:panel_admin')
    
    # Filtros
    estado = request.GET.get('estado', '')
    categoria = request.GET.get('categoria', '')
    prioridad = request.GET.get('prioridad', '')
    
    sugerencias = SugerenciaMejora.objects.all()
    
    if estado:
        sugerencias = sugerencias.filter(estado=estado)
    if categoria:
        sugerencias = sugerencias.filter(categoria=categoria)
    if prioridad:
        sugerencias = sugerencias.filter(prioridad=prioridad)
    
    # Estadísticas
    total_sugerencias = SugerenciaMejora.objects.count()
    pendientes = SugerenciaMejora.objects.filter(estado='PENDIENTE').count()
    en_analisis = SugerenciaMejora.objects.filter(estado='EN_ANALISIS').count()
    aprobadas = SugerenciaMejora.objects.filter(estado='APROBADA').count()
    implementadas = SugerenciaMejora.objects.filter(estado='IMPLEMENTADA').count()
    
    context = {
        'sugerencias': sugerencias,
        'estado_filtro': estado,
        'categoria_filtro': categoria,
        'prioridad_filtro': prioridad,
        'total_sugerencias': total_sugerencias,
        'pendientes': pendientes,
        'en_analisis': en_analisis,
        'aprobadas': aprobadas,
        'implementadas': implementadas,
    }
    return render(request, 'crm/gestionar_sugerencias.html', context)

@login_required
def revisar_sugerencia(request, sugerencia_id):
    """Vista para revisar y responder una sugerencia específica"""
    # Verificar permisos
    if not request.user.is_staff and request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('crm:panel_admin')
    
    sugerencia = get_object_or_404(SugerenciaMejora, id=sugerencia_id)
    
    if request.method == 'POST':
        estado = request.POST.get('estado')
        respuesta_gerencia = request.POST.get('respuesta_gerencia')
        accion_especifica = request.POST.get('accion_especifica')
        responsable_implementacion = request.POST.get('responsable_implementacion')
        fecha_implementacion = request.POST.get('fecha_implementacion')
        
        try:
            sugerencia.estado = estado
            sugerencia.respuesta_gerencia = respuesta_gerencia
            sugerencia.accion_especifica = accion_especifica
            sugerencia.responsable_implementacion = responsable_implementacion
            sugerencia.revisor = request.user
            sugerencia.fecha_revision = timezone.now()
            
            if fecha_implementacion:
                sugerencia.fecha_implementacion = fecha_implementacion
            
            sugerencia.save()
            
            messages.success(request, f'Sugerencia "{sugerencia.titulo}" actualizada exitosamente.')
            return redirect('crm:gestionar_sugerencias')
        except Exception as e:
            messages.error(request, f'Error al actualizar la sugerencia: {str(e)}')
    
    context = {
        'sugerencia': sugerencia,
    }
    return render(request, 'crm/revisar_sugerencia.html', context)

@login_required
def embudo_ventas(request):
    """Vista principal del embudo de ventas - Redirige al dashboard"""
    return redirect('crm:embudo_ventas_dashboard')

@login_required
def crear_embudo(request):
    """Vista para crear un nuevo embudo de ventas"""
    
    if request.method == 'POST':
        # Procesar formulario de creación
        cliente_id = request.POST.get('cliente')
        campana_id = request.POST.get('campana')
        etapa = request.POST.get('etapa')
        origen = request.POST.get('origen')
        valor_estimado = request.POST.get('valor_estimado')
        descripcion = request.POST.get('descripcion_negocio')
        
        try:
            cliente = Cliente.objects.get(id=cliente_id)
            campana = None
            if campana_id:
                campana = Campana.objects.get(id=campana_id)
            
            embudo = EmbudoVentas.objects.create(
                cliente=cliente,
                campana=campana,
                etapa=etapa,
                origen=origen,
                valor_estimado=valor_estimado if valor_estimado else None,
                descripcion_negocio=descripcion,
                creado_por=request.user
            )
            
            messages.success(request, f'Embudo de ventas creado para {cliente.razon_social}')
            return redirect('crm:embudo_ventas_dashboard')
            
        except Exception as e:
            messages.error(request, f'Error al crear el embudo: {str(e)}')
    
    # Obtener datos para el formulario
    clientes = Cliente.objects.filter(activo=True).order_by('razon_social')
    campanas = Campana.objects.filter(activa=True).order_by('-fecha_inicio')
    
    context = {
        'clientes': clientes,
        'campanas': campanas,
    }
    
    return render(request, 'crm/crear_embudo.html', context)

@login_required
def detalle_embudo(request, embudo_id):
    """Vista de detalle de un embudo de ventas - Redirige a la vista unificada"""
    return redirect('crm:embudo_ventas_detalle', embudo_id=embudo_id)

@login_required
def embudo_ventas_dashboard(request):
    """Dashboard principal del embudo de ventas con gráficos"""
    
    # Obtener estadísticas generales del embudo
    embudos = EmbudoVentas.objects.all()
    
    # Estadísticas por etapa
    etapas_stats = embudos.values('etapa').annotate(
        total=Count('id', distinct=True),
        valor_total=Sum('valor_estimado')
    ).order_by('etapa')
    
    # Estadísticas por origen
    origenes_stats = embudos.values('origen').annotate(
        total=Count('id', distinct=True),
        valor_total=Sum('valor_estimado')
    ).order_by('-total')
    
    # Estadísticas por campaña
    campanas_stats = embudos.filter(
        campana__isnull=False,
        campana__sucursal=request.user.sucursal
    ).values('campana__nombre', 'campana__id').annotate(
        total=Count('id', distinct=True),
        valor_total=Sum('valor_estimado')
    ).order_by('-total')
    
    # Datos para el gráfico de embudo
    etapas_orden = ['CONTACTO_INICIAL', 'CALIFICACION', 'PROPUESTA', 'NEGOCIACION', 'CIERRE', 'PERDIDO']
    embudo_data = []
    
    for etapa in etapas_orden:
        etapa_stats = next((s for s in etapas_stats if s['etapa'] == etapa), None)
        if etapa_stats:
            embudo_data.append({
                'etapa': dict(EmbudoVentas.ETAPA_CHOICES)[etapa],
                'total': etapa_stats['total'],
                'valor_total': float(etapa_stats['valor_total'] or 0),
                'color': get_etapa_color(etapa)
            })
        else:
            embudo_data.append({
                'etapa': dict(EmbudoVentas.ETAPA_CHOICES)[etapa],
                'total': 0,
                'valor_total': 0,
                'color': get_etapa_color(etapa)
            })
    
    # KPIs principales
    total_embudos = embudos.count()
    total_valor_estimado = embudos.aggregate(total=Sum('valor_estimado'))['total'] or 0
    tasa_conversion = calcular_tasa_conversion(embudos)
    total_valor_cierre = embudos.aggregate(total=Sum("valor_cierre"))["total"] or 0
    
    # Embudos recientes (últimos 10)
    embudos_recientes = embudos.order_by('-fecha_ultima_actividad')[:10]
    
    # Asignar colores a los embudos recientes
    for embudo in embudos_recientes:
        embudo.color = get_etapa_color(embudo.etapa)
    
    context = {
        'embudo_data': embudo_data,
        'origenes_stats': origenes_stats,
        'campanas_stats': campanas_stats,
        'total_embudos': total_embudos,
        'total_valor_estimado': total_valor_estimado,
        "total_valor_cierre": total_valor_cierre,
        'tasa_conversion': tasa_conversion,
        'etapas_orden': etapas_orden,
        'embudos_recientes': embudos_recientes,
    }
    
    return render(request, 'crm/embudo_ventas_dashboard.html', context)

@login_required
def embudo_ventas_campana(request, campana_id=None):
    """Embudo de ventas filtrado por campaña específica"""
    
    if campana_id:
        campana = get_object_or_404(Campana, id=campana_id, sucursal=request.user.sucursal)
        embudos = EmbudoVentas.objects.filter(campana=campana)
        titulo = f"Embudo de Ventas - {campana.nombre}"
    else:
        campana = None
        embudos = EmbudoVentas.objects.filter(campana__isnull=True)
        titulo = "Embudo de Ventas - Sin Campaña"
    
    # Generar datos del embudo
    embudo_data = generar_datos_embudo(embudos)
    
    # KPIs de la campaña
    total_embudos = embudos.count()
    total_valor_estimado = embudos.aggregate(total=Sum('valor_estimado'))['total'] or 0
    tasa_conversion = calcular_tasa_conversion(embudos)
    
    context = {
        'campana': campana,
        'embudo_data': embudo_data,
        'titulo': titulo,
        'total_embudos': total_embudos,
        'total_valor_estimado': total_valor_estimado,
        'tasa_conversion': tasa_conversion,
    }
    
    return render(request, 'crm/embudo_ventas_campana.html', context)

@login_required
def embudo_ventas_origen(request, origen):
    """Embudo de ventas filtrado por origen (alertas, leads, etc.)"""
    
    # Validar origen
    origenes_validos = [choice[0] for choice in EmbudoVentas._meta.get_field('origen').choices]
    if origen not in origenes_validos:
        messages.error(request, 'Origen no válido')
        return redirect('crm:embudo_ventas_dashboard')
    
    embudos = EmbudoVentas.objects.filter(origen=origen)
    
    # Generar datos del embudo
    embudo_data = generar_datos_embudo(embudos)
    
    # KPIs del origen
    total_embudos = embudos.count()
    total_valor_estimado = embudos.aggregate(total=Sum('valor_estimado'))['total'] or 0
    tasa_conversion = calcular_tasa_conversion(embudos)
    
    # Obtener origen display name
    origen_display = dict(EmbudoVentas._meta.get_field('origen').choices)[origen]
    
    context = {
        'origen': origen,
        'origen_display': origen_display,
        'embudo_data': embudo_data,
        'total_embudos': total_embudos,
        'total_valor_estimado': total_valor_estimado,
        'tasa_conversion': tasa_conversion,
        'embudos': embudos,  # <--- AGREGADO
    }
    
    return render(request, 'crm/embudo_ventas_origen.html', context)

@login_required
def embudo_ventas_detalle(request, embudo_id):
    """Detalle de un embudo de ventas específico"""
    
    embudo = get_object_or_404(EmbudoVentas, id=embudo_id)
    
    # Manejar cambios del embudo
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'cambiar_etapa':
            nueva_etapa = request.POST.get('etapa')
            if nueva_etapa and nueva_etapa != embudo.etapa:
                embudo.etapa = nueva_etapa
                embudo.save()
                messages.success(request, f'Etapa actualizada a {embudo.get_etapa_display()}')
                return redirect('crm:embudo_ventas_detalle', embudo_id=embudo.id)
        
        elif action == 'actualizar_valores':
            try:
                # Actualizar valor estimado
                nuevo_valor_estimado = request.POST.get('valor_estimado')
                if nuevo_valor_estimado:
                    embudo.valor_estimado = Decimal(nuevo_valor_estimado)
                
                # Actualizar valor de cierre
                nuevo_valor_cierre = request.POST.get('valor_cierre')
                if nuevo_valor_cierre:
                    embudo.valor_cierre = Decimal(nuevo_valor_cierre)
                elif nuevo_valor_cierre == '':  # Campo vacío
                    embudo.valor_cierre = None
                
                embudo.save()
                messages.success(request, 'Valores actualizados correctamente')
                return redirect('crm:embudo_ventas_detalle', embudo_id=embudo.id)
                
            except (ValueError, TypeError) as e:
                messages.error(request, f'Error al actualizar valores: {str(e)}')
                return redirect('crm:embudo_ventas_detalle', embudo_id=embudo.id)
    
    # Obtener contactos relacionados
    contactos = ContactoCliente.objects.filter(embudo_ventas=embudo).order_by('-fecha_contacto')
    
    context = {
        'embudo': embudo,
        'contactos': contactos,
    }
    
    return render(request, 'crm/embudo_ventas_detalle.html', context)

@login_required
def crear_contacto(request):
    """Crear un nuevo contacto para un embudo de ventas"""
    if request.method == 'POST':
        embudo_id = request.POST.get('embudo_id')
        tipo_contacto = request.POST.get('tipo_contacto')
        descripcion = request.POST.get('descripcion')
        resultado = request.POST.get('resultado')
        observaciones = request.POST.get('observaciones', '')
        proximo_seguimiento = request.POST.get('proximo_seguimiento')
        
        try:
            embudo = EmbudoVentas.objects.get(id=embudo_id)
            
            # Crear el contacto
            contacto = ContactoCliente.objects.create(
                cliente=embudo.cliente,
                tipo_contacto=tipo_contacto,
                descripcion=descripcion,
                resultado=resultado,
                observaciones=observaciones,
                proximo_seguimiento=proximo_seguimiento if proximo_seguimiento else None,
                responsable=request.user,
                embudo_ventas=embudo
            )
            
            messages.success(request, 'Contacto creado exitosamente')
            return redirect('crm:embudo_ventas_detalle', embudo_id=embudo.id)
            
        except EmbudoVentas.DoesNotExist:
            messages.error(request, 'Embudo de ventas no encontrado')
            return redirect('crm:embudo_ventas_dashboard')
        except Exception as e:
            messages.error(request, f'Error al crear el contacto: {str(e)}')
            return redirect('crm:embudo_ventas_dashboard')
    
    return redirect('crm:embudo_ventas_dashboard')

# Funciones auxiliares
def get_etapa_color(etapa):
    """Retorna el color CSS para cada etapa del embudo"""
    colors = {
        'CONTACTO_INICIAL': '#007bff',  # Azul
        'CALIFICACION': '#17a2b8',      # Cyan
        'PROPUESTA': '#ffc107',         # Amarillo
        'NEGOCIACION': '#fd7e14',       # Naranja
        'CIERRE': '#28a745',            # Verde
        'PERDIDO': '#dc3545',           # Rojo
    }
    return colors.get(etapa, '#6c757d')

def generar_datos_embudo(embudos):
    """Genera los datos para el gráfico del embudo"""
    etapas_orden = ['CONTACTO_INICIAL', 'CALIFICACION', 'PROPUESTA', 'NEGOCIACION', 'CIERRE', 'PERDIDO']
    
    # Obtener estadísticas por etapa
    etapas_stats = embudos.values('etapa').annotate(
        total=Count('id', distinct=True),
        valor_total=Sum('valor_estimado')
    )
    
    # Crear diccionario para acceso rápido
    stats_dict = {s['etapa']: s for s in etapas_stats}
    
    embudo_data = []
    for etapa in etapas_orden:
        etapa_stats = stats_dict.get(etapa, {
            'total': 0,
            'valor_total': 0
        })
        
        embudo_data.append({
            'etapa': dict(EmbudoVentas.ETAPA_CHOICES)[etapa],
            'etapa_key': etapa,
            'total': etapa_stats['total'],
            'valor_total': float(etapa_stats['valor_total'] or 0),
            'color': get_etapa_color(etapa),
            'porcentaje': 0  # Se calculará en el template
        })
    
    # Calcular porcentajes
    total_general = sum(item['total'] for item in embudo_data)
    if total_general > 0:
        for item in embudo_data:
            item['porcentaje'] = round((item['total'] / total_general) * 100, 1)
    
    return embudo_data

def calcular_tasa_conversion(embudos):
    """Calcula la tasa de conversión del embudo"""
    total_embudos = embudos.count()
    if total_embudos == 0:
        return 0
    
    embudos_cierre = embudos.filter(etapa='CIERRE').count()
    return round((embudos_cierre / total_embudos) * 100, 1)

@login_required
def reporte_facturacion(request):
    """Vista para generar reportes de facturación detallados"""
    
    # Obtener parámetros del reporte
    tipo_reporte = request.GET.get('tipo_reporte', 'anual')
    año = int(request.GET.get('año', timezone.now().year))
    periodo_especifico = request.GET.get('periodo_especifico', '')
    nivel_detalle = request.GET.get('nivel_detalle', 'resumen')
    top_clientes = request.GET.get('top_clientes', '')
    
    # Definir rangos de fechas según el tipo de reporte
    if tipo_reporte == 'anual':
        fecha_inicio = timezone.datetime(año, 1, 1).date()
        fecha_fin = timezone.datetime(año, 12, 31).date()
        titulo_periodo = f"Año {año}"
    elif tipo_reporte == 'semestral':
        if periodo_especifico == 'S1':
            fecha_inicio = timezone.datetime(año, 1, 1).date()
            fecha_fin = timezone.datetime(año, 6, 30).date()
            titulo_periodo = f"Primer Semestre {año}"
        elif periodo_especifico == 'S2':
            fecha_inicio = timezone.datetime(año, 7, 1).date()
            fecha_fin = timezone.datetime(año, 12, 31).date()
            titulo_periodo = f"Segundo Semestre {año}"
        else:
            fecha_inicio = timezone.datetime(año, 1, 1).date()
            fecha_fin = timezone.datetime(año, 12, 31).date()
            titulo_periodo = f"Ambos Semestres {año}"
    elif tipo_reporte == 'trimestral':
        if periodo_especifico == 'Q1':
            fecha_inicio = timezone.datetime(año, 1, 1).date()
            fecha_fin = timezone.datetime(año, 3, 31).date()
            titulo_periodo = f"Q1 {año} (Enero-Marzo)"
        elif periodo_especifico == 'Q2':
            fecha_inicio = timezone.datetime(año, 4, 1).date()
            fecha_fin = timezone.datetime(año, 6, 30).date()
            titulo_periodo = f"Q2 {año} (Abril-Junio)"
        elif periodo_especifico == 'Q3':
            fecha_inicio = timezone.datetime(año, 7, 1).date()
            fecha_fin = timezone.datetime(año, 9, 30).date()
            titulo_periodo = f"Q3 {año} (Julio-Septiembre)"
        elif periodo_especifico == 'Q4':
            fecha_inicio = timezone.datetime(año, 10, 1).date()
            fecha_fin = timezone.datetime(año, 12, 31).date()
            titulo_periodo = f"Q4 {año} (Octubre-Diciembre)"
        else:
            fecha_inicio = timezone.datetime(año, 1, 1).date()
            fecha_fin = timezone.datetime(año, 12, 31).date()
            titulo_periodo = f"Todos los Trimestres {año}"
    elif tipo_reporte == 'mensual':
        fecha_inicio = timezone.datetime(año, 1, 1).date()
        fecha_fin = timezone.datetime(año, 12, 31).date()
        titulo_periodo = f"Análisis Mensual {año}"
    else:
        fecha_inicio = timezone.datetime(año, 1, 1).date()
        fecha_fin = timezone.datetime(año, 12, 31).date()
        titulo_periodo = f"Año {año}"
    
    # Obtener servicios en el período
    servicios = Servicio.objects.filter(
        fecha_servicio__gte=fecha_inicio,
        fecha_servicio__lte=fecha_fin,
        estado='COMPLETADO'
    ).select_related('preorden__cliente')
    
    # Calcular facturación por cliente
    facturacion_por_cliente = {}
    total_facturacion = 0
    total_servicios = 0
    
    for servicio in servicios:
        cliente = servicio.preorden.cliente
        
        if cliente not in facturacion_por_cliente:
                    facturacion_por_cliente[cliente] = {
            'cliente': cliente,
            'facturacion_total': 0,
            'servicios': [],
            'cantidad_servicios': 0,
            'mano_obra_total': 0,
            'gastos_total': 0,
            'repuestos_total': 0,
            'promedio_por_servicio': 0
        }
        
        # Calcular facturación del servicio
        mano_obra = servicio.valor_mano_obra or 0
        gastos = sum(g.monto for g in servicio.gastos.all())
        repuestos = sum(r.precio_unitario * r.cantidad for r in servicio.repuestos.all())
        facturacion_servicio = mano_obra + gastos + repuestos
        
        facturacion_por_cliente[cliente]['facturacion_total'] += facturacion_servicio
        facturacion_por_cliente[cliente]['cantidad_servicios'] += 1
        facturacion_por_cliente[cliente]['mano_obra_total'] += mano_obra
        facturacion_por_cliente[cliente]['gastos_total'] += gastos
        facturacion_por_cliente[cliente]['repuestos_total'] += repuestos
        
        # Calcular promedio por servicio
        if facturacion_por_cliente[cliente]['cantidad_servicios'] > 0:
            facturacion_por_cliente[cliente]['promedio_por_servicio'] = facturacion_por_cliente[cliente]['facturacion_total'] / facturacion_por_cliente[cliente]['cantidad_servicios']
        
        if nivel_detalle in ['detallado', 'completo']:
            facturacion_por_cliente[cliente]['servicios'].append({
                'servicio': servicio,
                'fecha': servicio.fecha_servicio,
                'mano_obra': mano_obra,
                'gastos': gastos,
                'repuestos': repuestos,
                'total': facturacion_servicio
            })
        
        total_facturacion += facturacion_servicio
        total_servicios += 1
    
    # Ordenar por facturación y aplicar límite de top clientes
    clientes_ordenados = sorted(
        facturacion_por_cliente.values(),
        key=lambda x: x['facturacion_total'],
        reverse=True
    )
    
    if top_clientes:
        clientes_ordenados = clientes_ordenados[:int(top_clientes)]
    
    # Calcular estadísticas mensuales para reportes anuales y mensuales
    estadisticas_mensuales = {}
    if tipo_reporte in ['mensual', 'anual']:
        for mes in range(1, 13):
            fecha_mes_inicio = timezone.datetime(año, mes, 1).date()
            if mes == 12:
                fecha_mes_fin = timezone.datetime(año, mes, 31).date()
            else:
                fecha_mes_fin = timezone.datetime(año, mes + 1, 1).date() - timedelta(days=1)
            
            servicios_mes = servicios.filter(
                fecha_servicio__gte=fecha_mes_inicio,
                fecha_servicio__lte=fecha_mes_fin
            )
            
            facturacion_mes = 0
            for servicio in servicios_mes:
                mano_obra = servicio.valor_mano_obra or 0
                gastos = sum(g.monto for g in servicio.gastos.all())
                repuestos = sum(r.precio_unitario * r.cantidad for r in servicio.repuestos.all())
                facturacion_mes += mano_obra + gastos + repuestos
            
            estadisticas_mensuales[mes] = {
                'nombre': timezone.datetime(año, mes, 1).strftime('%B'),
                'facturacion': facturacion_mes,
                'servicios': servicios_mes.count()
            }
    
    # Calcular estadísticas por segmento
    estadisticas_segmento = {'A': 0, 'B': 0, 'C': 0, 'NUEVO': 0}
    for cliente_data in clientes_ordenados:
        cliente = cliente_data['cliente']
        if hasattr(cliente, 'analisiscliente') and cliente.analisiscliente:
            segmento = cliente.analisiscliente.categoria
        else:
            segmento = 'NUEVO'
        
        if segmento in estadisticas_segmento:
            estadisticas_segmento[segmento] += cliente_data['facturacion_total']
    
    # Calcular promedio por servicio
    promedio_por_servicio = total_facturacion / total_servicios if total_servicios > 0 else 0
    
    context = {
        'tipo_reporte': tipo_reporte,
        'titulo_periodo': titulo_periodo,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'clientes_ordenados': clientes_ordenados,
        'total_facturacion': total_facturacion,
        'total_servicios': total_servicios,
        'promedio_por_servicio': promedio_por_servicio,
        'nivel_detalle': nivel_detalle,
        'estadisticas_mensuales': estadisticas_mensuales,
        'estadisticas_segmento': estadisticas_segmento,
        'top_clientes': top_clientes,
        'periodo_especifico': periodo_especifico,
        'año': año,
        'fecha_generacion': timezone.now()
    }
    
    return render(request, 'crm/reporte_facturacion.html', context)

@login_required
def exportar_reporte_excel(request):
    """Exportar reporte de facturación a Excel (CSV)"""
    
    # Obtener parámetros del reporte
    tipo_reporte = request.GET.get('tipo_reporte', 'anual')
    año = int(request.GET.get('año', timezone.now().year))
    periodo_especifico = request.GET.get('periodo_especifico', '')
    nivel_detalle = request.GET.get('nivel_detalle', 'resumen')
    top_clientes = request.GET.get('top_clientes', '')
    
    # Definir rangos de fechas según el tipo de reporte
    if tipo_reporte == 'anual':
        fecha_inicio = timezone.datetime(año, 1, 1).date()
        fecha_fin = timezone.datetime(año, 12, 31).date()
        titulo_periodo = f"Año {año}"
    elif tipo_reporte == 'semestral':
        if periodo_especifico == 'S1':
            fecha_inicio = timezone.datetime(año, 1, 1).date()
            fecha_fin = timezone.datetime(año, 6, 30).date()
            titulo_periodo = f"Primer Semestre {año}"
        elif periodo_especifico == 'S2':
            fecha_inicio = timezone.datetime(año, 7, 1).date()
            fecha_fin = timezone.datetime(año, 12, 31).date()
            titulo_periodo = f"Segundo Semestre {año}"
        else:
            fecha_inicio = timezone.datetime(año, 1, 1).date()
            fecha_fin = timezone.datetime(año, 12, 31).date()
            titulo_periodo = f"Ambos Semestres {año}"
    elif tipo_reporte == 'trimestral':
        if periodo_especifico == 'Q1':
            fecha_inicio = timezone.datetime(año, 1, 1).date()
            fecha_fin = timezone.datetime(año, 3, 31).date()
            titulo_periodo = f"Q1 {año} (Enero-Marzo)"
        elif periodo_especifico == 'Q2':
            fecha_inicio = timezone.datetime(año, 4, 1).date()
            fecha_fin = timezone.datetime(año, 6, 30).date()
            titulo_periodo = f"Q2 {año} (Abril-Junio)"
        elif periodo_especifico == 'Q3':
            fecha_inicio = timezone.datetime(año, 7, 1).date()
            fecha_fin = timezone.datetime(año, 9, 30).date()
            titulo_periodo = f"Q3 {año} (Julio-Septiembre)"
        elif periodo_especifico == 'Q4':
            fecha_inicio = timezone.datetime(año, 10, 1).date()
            fecha_fin = timezone.datetime(año, 12, 31).date()
            titulo_periodo = f"Q4 {año} (Octubre-Diciembre)"
        else:
            fecha_inicio = timezone.datetime(año, 1, 1).date()
            fecha_fin = timezone.datetime(año, 12, 31).date()
            titulo_periodo = f"Todos los Trimestres {año}"
    elif tipo_reporte == 'mensual':
        fecha_inicio = timezone.datetime(año, 1, 1).date()
        fecha_fin = timezone.datetime(año, 12, 31).date()
        titulo_periodo = f"Análisis Mensual {año}"
    else:
        fecha_inicio = timezone.datetime(año, 1, 1).date()
        fecha_fin = timezone.datetime(año, 12, 31).date()
        titulo_periodo = f"Año {año}"
    
    # Obtener servicios en el período
    servicios = Servicio.objects.filter(
        fecha_servicio__gte=fecha_inicio,
        fecha_servicio__lte=fecha_fin,
        estado='COMPLETADO'
    ).select_related('preorden__cliente')
    
    # Calcular facturación por cliente
    facturacion_por_cliente = {}
    total_facturacion = 0
    total_servicios = 0
    
    for servicio in servicios:
        cliente = servicio.preorden.cliente
        
        if cliente not in facturacion_por_cliente:
            facturacion_por_cliente[cliente] = {
                'cliente': cliente,
                'facturacion_total': 0,
                'servicios': [],
                'cantidad_servicios': 0,
                'mano_obra_total': 0,
                'gastos_total': 0,
                'repuestos_total': 0,
                'promedio_por_servicio': 0
            }
        
        # Calcular facturación del servicio
        mano_obra = servicio.valor_mano_obra or 0
        gastos = sum(g.monto for g in servicio.gastos.all())
        repuestos = sum(r.precio_unitario * r.cantidad for r in servicio.repuestos.all())
        facturacion_servicio = mano_obra + gastos + repuestos
        
        facturacion_por_cliente[cliente]['facturacion_total'] += facturacion_servicio
        facturacion_por_cliente[cliente]['cantidad_servicios'] += 1
        facturacion_por_cliente[cliente]['mano_obra_total'] += mano_obra
        facturacion_por_cliente[cliente]['gastos_total'] += gastos
        facturacion_por_cliente[cliente]['repuestos_total'] += repuestos
        
        # Calcular promedio por servicio
        if facturacion_por_cliente[cliente]['cantidad_servicios'] > 0:
            facturacion_por_cliente[cliente]['promedio_por_servicio'] = facturacion_por_cliente[cliente]['facturacion_total'] / facturacion_por_cliente[cliente]['cantidad_servicios']
        
        if nivel_detalle in ['detallado', 'completo']:
            facturacion_por_cliente[cliente]['servicios'].append({
                'servicio': servicio,
                'fecha': servicio.fecha_servicio,
                'mano_obra': mano_obra,
                'gastos': gastos,
                'repuestos': repuestos,
                'total': facturacion_servicio
            })
        
        total_facturacion += facturacion_servicio
        total_servicios += 1
    
    # Ordenar por facturación y aplicar límite de top clientes
    clientes_ordenados = sorted(
        facturacion_por_cliente.values(),
        key=lambda x: x['facturacion_total'],
        reverse=True
    )
    
    if top_clientes:
        clientes_ordenados = clientes_ordenados[:int(top_clientes)]
    
    # Crear respuesta CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="reporte_facturacion_{tipo_reporte}_{año}.csv"'
    
    # Crear writer CSV
    writer = csv.writer(response)
    writer.writerow(['REPORTE DE FACTURACIÓN'])
    writer.writerow([f'Período: {titulo_periodo}'])
    writer.writerow([f'Fecha de Generación: {timezone.now().strftime("%d/%m/%Y %H:%M")}'])
    writer.writerow([])
    
    # Resumen ejecutivo
    writer.writerow(['RESUMEN EJECUTIVO'])
    writer.writerow(['Facturación Total', f'${total_facturacion:,.0f}'])
    writer.writerow(['Total de Servicios', total_servicios])
    writer.writerow(['Promedio por Servicio', f'${total_facturacion/total_servicios:,.0f}' if total_servicios > 0 else '$0'])
    writer.writerow(['Total de Clientes', len(clientes_ordenados)])
    writer.writerow([])
    
    # Tabla de clientes
    writer.writerow(['FACTURACIÓN POR CLIENTE'])
    writer.writerow(['#', 'Cliente', 'Email', 'Segmento', 'Facturación Total', 'Servicios', 'Mano de Obra', 'Gastos', 'Repuestos', 'Promedio/Servicio'])
    
    for i, cliente_data in enumerate(clientes_ordenados, 1):
        cliente = cliente_data['cliente']
        segmento = 'Nuevo'
        if hasattr(cliente, 'analisiscliente') and cliente.analisiscliente:
            segmento = f'Segmento {cliente.analisiscliente.categoria}'
        
        writer.writerow([
            i,
            cliente.razon_social,
            cliente.email or 'Sin email',
            segmento,
            f'${cliente_data["facturacion_total"]:,.0f}',
            cliente_data['cantidad_servicios'],
            f'${cliente_data["mano_obra_total"]:,.0f}',
            f'${cliente_data["gastos_total"]:,.0f}',
            f'${cliente_data["repuestos_total"]:,.0f}',
            f'${cliente_data["promedio_por_servicio"]:,.0f}'
        ])
    
    # Si es detallado, agregar servicios
    if nivel_detalle in ['detallado', 'completo']:
        writer.writerow([])
        writer.writerow(['DETALLE DE SERVICIOS'])
        writer.writerow(['Cliente', 'Fecha', 'Descripción', 'Mano de Obra', 'Gastos', 'Repuestos', 'Total'])
        
        for cliente_data in clientes_ordenados:
            cliente = cliente_data['cliente']
            for servicio_data in cliente_data['servicios']:
                writer.writerow([
                    cliente.razon_social,
                    servicio_data['fecha'].strftime('%d/%m/%Y'),
                    servicio_data['servicio'].descripcion[:50],
                    f'${servicio_data["mano_obra"]:,.0f}',
                    f'${servicio_data["gastos"]:,.0f}',
                    f'${servicio_data["repuestos"]:,.0f}',
                    f'${servicio_data["total"]:,.0f}'
                ])
    
    return response

# ===== EMBUDO DE CHECKLIST ADICIONALES =====

@login_required
def embudo_checklist_dashboard(request):
    """Dashboard principal del embudo de checklist adicionales"""
    
    # Obtener filtros
    etapa_filtro = request.GET.get('etapa', '')
    prioridad_filtro = request.GET.get('prioridad', '')
    tipo_filtro = request.GET.get('tipo', '')
    responsable_filtro = request.GET.get('responsable', '')
    
    # Base queryset
    from .models import EmbudoChecklistAdicional
    checklists = EmbudoChecklistAdicional.objects.select_related(
        'servicio', 'equipo', 'cliente', 'identificado_por', 'responsable_implementacion'
    ).prefetch_related('servicio__preorden__sucursal')
    
    # Aplicar filtros
    if etapa_filtro:
        checklists = checklists.filter(etapa=etapa_filtro)
    if prioridad_filtro:
        checklists = checklists.filter(prioridad=prioridad_filtro)
    if tipo_filtro:
        checklists = checklists.filter(tipo=tipo_filtro)
    if responsable_filtro:
        checklists = checklists.filter(responsable_implementacion_id=responsable_filtro)
    
    # Calcular métricas generales
    total_checklists = checklists.count()
    checklists_pendientes = checklists.exclude(etapa__in=['IMPLEMENTADO', 'VERIFICADO', 'CERRADO']).count()
    checklists_vencidos = sum(1 for c in checklists if c.esta_vencido)
    checklists_criticos = checklists.filter(prioridad='CRITICA').exclude(etapa__in=['IMPLEMENTADO', 'VERIFICADO', 'CERRADO']).count()
    
    # Análisis por etapa
    etapas_stats = checklists.values('etapa').annotate(
        total=Count('id'),
        criticos=Count('id', filter=Q(prioridad='CRITICA')),
        vencidos=Count('id', filter=Q(fecha_limite__lt=timezone.now().date()))
    ).order_by('etapa')
    
    # Análisis por prioridad
    prioridades_stats = checklists.values('prioridad').annotate(
        total=Count('id'),
        pendientes=Count('id', filter=~Q(etapa__in=['IMPLEMENTADO', 'VERIFICADO', 'CERRADO']))
    ).order_by('prioridad')
    
    # Análisis por tipo
    tipos_stats = checklists.values('tipo').annotate(
        total=Count('id'),
        completados=Count('id', filter=Q(etapa__in=['IMPLEMENTADO', 'VERIFICADO', 'CERRADO']))
    ).order_by('-total')
    
    # Top responsables
    responsables_stats = checklists.values(
        'responsable_implementacion__nombre', 
        'responsable_implementacion__apellido',
        'responsable_implementacion__id'
    ).annotate(
        total=Count('id'),
        pendientes=Count('id', filter=~Q(etapa__in=['IMPLEMENTADO', 'VERIFICADO', 'CERRADO'])),
        vencidos=Count('id', filter=Q(fecha_limite__lt=timezone.now().date()))
    ).filter(responsable_implementacion__isnull=False).order_by('-total')
    
    # Checklists recientes
    checklists_recientes = checklists.order_by('-fecha_identificacion')[:10]
    
    # Obtener datos para filtros
    from recursosHumanos.models import Usuario
    responsables_filtro = Usuario.objects.filter(is_active=True).order_by('apellido', 'nombre')
    
    context = {
        'titulo': 'Embudo de Checklist Adicionales',
        'total_checklists': total_checklists,
        'checklists_pendientes': checklists_pendientes,
        'checklists_vencidos': checklists_vencidos,
        'checklists_criticos': checklists_criticos,
        'etapas_stats': etapas_stats,
        'prioridades_stats': prioridades_stats,
        'tipos_stats': tipos_stats,
        'responsables_stats': responsables_stats,
        'checklists_recientes': checklists_recientes,
        'responsables_filtro': responsables_filtro,
        'etapa_filtro': etapa_filtro,
        'prioridad_filtro': prioridad_filtro,
        'tipo_filtro': tipo_filtro,
        'responsable_filtro': responsable_filtro,
    }
    
    return render(request, 'crm/embudo_checklist_dashboard.html', context)

@login_required
def crear_checklist_adicional(request):
    """Crear un nuevo checklist adicional"""
    
    if request.method == 'POST':
        from .models import EmbudoChecklistAdicional
        from gestionDeTaller.models import Servicio
        from clientes.models import Equipo
        
        try:
            # Obtener datos del formulario
            servicio_id = request.POST.get('servicio')
            titulo = request.POST.get('titulo')
            descripcion = request.POST.get('descripcion')
            tipo = request.POST.get('tipo')
            prioridad = request.POST.get('prioridad')
            responsable_id = request.POST.get('responsable')
            fecha_limite = request.POST.get('fecha_limite')
            costo_estimado = request.POST.get('costo_estimado')
            tiempo_estimado = request.POST.get('tiempo_estimado')
            recursos_necesarios = request.POST.get('recursos_necesarios')
            observaciones = request.POST.get('observaciones')
            
            # Validar datos requeridos
            if not all([servicio_id, titulo, descripcion, tipo, prioridad]):
                messages.error(request, 'Todos los campos obligatorios deben estar completos.')
                return redirect('crm:embudo_checklist_dashboard')
            
            # Obtener objetos relacionados
            servicio = get_object_or_404(Servicio, id=servicio_id)
            responsable = None
            if responsable_id:
                responsable = get_object_or_404(Usuario, id=responsable_id)
            
            # Crear el checklist
            checklist = EmbudoChecklistAdicional.objects.create(
                titulo=titulo,
                descripcion=descripcion,
                tipo=tipo,
                prioridad=prioridad,
                servicio=servicio,
                equipo=servicio.preorden.equipo,
                cliente=servicio.preorden.cliente,
                identificado_por=request.user,
                responsable_implementacion=responsable,
                fecha_limite=fecha_limite if fecha_limite else None,
                costo_estimado=costo_estimado if costo_estimado else None,
                tiempo_estimado_horas=tiempo_estimado if tiempo_estimado else None,
                recursos_necesarios=recursos_necesarios,
                observaciones=observaciones,
            )
            
            messages.success(request, f'Checklist "{titulo}" creado exitosamente.')
            return redirect('crm:detalle_checklist', checklist_id=checklist.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear el checklist: {str(e)}')
            return redirect('crm:embudo_checklist_dashboard')
    
    # GET request - mostrar formulario
    from gestionDeTaller.models import Servicio
    servicios = Servicio.objects.filter(
        estado__in=['COMPLETADO', 'EN_PROCESO']
    ).select_related('preorden__cliente', 'preorden__equipo').order_by('-fecha_servicio')
    
    from recursosHumanos.models import Usuario
    responsables = Usuario.objects.filter(is_active=True).order_by('apellido', 'nombre')
    
    context = {
        'titulo': 'Crear Checklist Adicional',
        'servicios': servicios,
        'responsables': responsables,
    }
    
    return render(request, 'crm/crear_checklist_adicional.html', context)

@login_required
def detalle_checklist(request, checklist_id):
    """Detalle de un checklist específico"""
    
    from .models import EmbudoChecklistAdicional
    checklist = get_object_or_404(
        EmbudoChecklistAdicional.objects.select_related(
            'servicio', 'equipo', 'cliente', 'identificado_por', 'responsable_implementacion'
        ),
        id=checklist_id
    )
    
    if request.method == 'POST':
        # Procesar cambio de etapa
        nueva_etapa = request.POST.get('nueva_etapa')
        if nueva_etapa and nueva_etapa in dict(EmbudoChecklistAdicional.ETAPA_CHOICES):
            if checklist.avanzar_etapa(nueva_etapa, request.user):
                messages.success(request, f'Checklist avanzado a etapa: {checklist.get_etapa_display()}')
            else:
                messages.error(request, 'No se pudo avanzar la etapa.')
        
        # Actualizar otros campos
        checklist.titulo = request.POST.get('titulo', checklist.titulo)
        checklist.descripcion = request.POST.get('descripcion', checklist.descripcion)
        checklist.prioridad = request.POST.get('prioridad', checklist.prioridad)
        checklist.observaciones = request.POST.get('observaciones', checklist.observaciones)
        
        responsable_id = request.POST.get('responsable')
        if responsable_id:
            checklist.responsable_implementacion = get_object_or_404(Usuario, id=responsable_id)
        
        fecha_limite = request.POST.get('fecha_limite')
        if fecha_limite:
            checklist.fecha_limite = fecha_limite
        
        checklist.save()
        messages.success(request, 'Checklist actualizado exitosamente.')
        return redirect('crm:detalle_checklist', checklist_id=checklist.id)
    
    # Obtener datos para el formulario
    from recursosHumanos.models import Usuario
    responsables = Usuario.objects.filter(is_active=True).order_by('apellido', 'nombre')
    
    context = {
        'checklist': checklist,
        'responsables': responsables,
    }
    
    return render(request, 'crm/detalle_checklist.html', context)

@login_required
def checklist_por_etapa(request, etapa):
    """Mostrar checklists por etapa específica"""
    
    from .models import EmbudoChecklistAdicional
    
    if etapa not in dict(EmbudoChecklistAdicional.ETAPA_CHOICES):
        messages.error(request, 'Etapa no válida.')
        return redirect('crm:embudo_checklist_dashboard')
    
    checklists = EmbudoChecklistAdicional.objects.filter(
        etapa=etapa
    ).select_related(
        'servicio', 'equipo', 'cliente', 'identificado_por', 'responsable_implementacion'
    ).order_by('-fecha_identificacion')
    
    context = {
        'titulo': f'Checklists - {dict(EmbudoChecklistAdicional.ETAPA_CHOICES)[etapa]}',
        'checklists': checklists,
        'etapa_actual': etapa,
        'total_checklists': checklists.count(),
    }
    
    return render(request, 'crm/checklist_por_etapa.html', context)

@login_required
def checklist_por_prioridad(request, prioridad):
    """Mostrar checklists por prioridad específica"""
    
    from .models import EmbudoChecklistAdicional
    
    if prioridad not in dict(EmbudoChecklistAdicional.PRIORIDAD_CHOICES):
        messages.error(request, 'Prioridad no válida.')
        return redirect('crm:embudo_checklist_dashboard')
    
    checklists = EmbudoChecklistAdicional.objects.filter(
        prioridad=prioridad
    ).select_related(
        'servicio', 'equipo', 'cliente', 'identificado_por', 'responsable_implementacion'
    ).order_by('-fecha_identificacion')
    
    context = {
        'titulo': f'Checklists - Prioridad {dict(EmbudoChecklistAdicional.PRIORIDAD_CHOICES)[prioridad]}',
        'checklists': checklists,
        'prioridad_actual': prioridad,
        'total_checklists': checklists.count(),
    }
    
    return render(request, 'crm/checklist_por_prioridad.html', context)