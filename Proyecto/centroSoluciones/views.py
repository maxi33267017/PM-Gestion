from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import AlertaEquipo, LeadJohnDeere, AsignacionAlerta, CodigoAlerta, ReporteCSC, DatosReporteCSC
from clientes.models import Cliente, Equipo, ModeloEquipo
from recursosHumanos.models import Usuario, Sucursal
from crm.models import EmbudoVentas, ContactoCliente

# Importaciones para Reportes CSC
import pandas as pd
import os
from datetime import datetime
from django.core.files.storage import default_storage
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import io

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
            estado__in=['ASIGNADA', 'EN_PROCESO'],
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
    
    # Contar reportes CSC (solo para gerentes/administrativos)
    reportes_csc = 0
    if request.user.rol in ['GERENTE', 'ADMINISTRATIVO']:
        reportes_csc = ReporteCSC.objects.count()
    
    context = {
        'alertas_pendientes': alertas_pendientes,
        'alertas_asignadas': alertas_asignadas,
        'leads_nuevos': leads_nuevos,
        'reportes_csc': reportes_csc,
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
        # Manejar múltiples estados separados por comas
        estados = [e.strip() for e in estado.split(',')]
        if len(estados) == 1:
            alertas = alertas.filter(estado=estado)
        else:
            alertas = alertas.filter(estado__in=estados)
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
    
    # Calcular horas para los tiempos
    tiempo_pendiente_horas = 0
    tiempo_resolucion_horas = 0
    
    if alerta.tiempo_pendiente:
        tiempo_pendiente_horas = round(alerta.tiempo_pendiente.seconds / 3600, 1)
    
    if alerta.tiempo_resolucion:
        tiempo_resolucion_horas = round(alerta.tiempo_resolucion.seconds / 3600, 1)
    
    context = {
        'alerta': alerta,
        'es_admin': request.user.rol in ['GERENTE', 'ADMINISTRATIVO'],
        'tiempo_pendiente_horas': tiempo_pendiente_horas,
        'tiempo_resolucion_horas': tiempo_resolucion_horas,
    }
    
    return render(request, 'centroSoluciones/alerta_detail.html', context)

@login_required
def procesar_alerta(request, alerta_id):
    """Vista para que los técnicos y gerentes procesen alertas con conexión SAR y oportunidades CRM"""
    
    if request.user.rol not in ['TECNICO', 'GERENTE']:
        messages.error(request, 'Solo los técnicos y gerentes pueden procesar alertas.')
        return redirect('centroSoluciones:alertas_list')
    
    # Los técnicos solo pueden procesar sus alertas asignadas, los gerentes pueden procesar cualquier alerta
    if request.user.rol == 'TECNICO':
        alerta = get_object_or_404(AlertaEquipo, id=alerta_id, tecnico_asignado=request.user)
    else:
        alerta = get_object_or_404(AlertaEquipo, id=alerta_id)
    
    if request.method == 'POST':
        # Procesar el formulario
        estado = request.POST.get('estado')
        observaciones = request.POST.get('observaciones_tecnico')
        conexion_sar_realizada = request.POST.get('conexion_sar_realizada') == 'on'
        resultado_conexion_sar = request.POST.get('resultado_conexion_sar', '')
        crear_oportunidad = request.POST.get('crear_oportunidad') == 'on'
        tipo_oportunidad = request.POST.get('tipo_oportunidad', '')
        descripcion_oportunidad = request.POST.get('descripcion_oportunidad', '')
        valor_estimado = request.POST.get('valor_estimado', '')
        
        # Actualizar alerta
        alerta.estado = estado
        alerta.observaciones_tecnico = observaciones
        alerta.conexion_sar_realizada = conexion_sar_realizada
        alerta.resultado_conexion_sar = resultado_conexion_sar
        
        # Crear oportunidad CRM si se solicita
        if crear_oportunidad and tipo_oportunidad and descripcion_oportunidad:
            try:
                # Crear embudo de ventas
                embudo = EmbudoVentas.objects.create(
                    cliente=alerta.cliente,
                    etapa='CONTACTO_INICIAL',
                    valor_estimado=float(valor_estimado) if valor_estimado else None,
                    origen='ALERTA_EQUIPO',
                    alerta_equipo=alerta,
                    descripcion_negocio=descripcion_oportunidad,
                    observaciones=f"Oportunidad creada desde alerta {alerta.codigo}. Tipo: {tipo_oportunidad}",
                    creado_por=request.user
                )
                
                # Crear contacto inicial
                ContactoCliente.objects.create(
                    cliente=alerta.cliente,
                    tipo_contacto='VISITA',
                    descripcion=f"Contacto inicial por alerta {alerta.codigo}. {descripcion_oportunidad}",
                    resultado='EXITOSO',
                    observaciones=f"Técnico realizó conexión SAR y identificó oportunidad de {tipo_oportunidad}",
                    responsable=request.user,
                    embudo_ventas=embudo
                )
                
                alerta.oportunidad_crm_creada = True
                messages.success(request, f'Oportunidad CRM creada exitosamente para {tipo_oportunidad}.')
                
            except Exception as e:
                messages.error(request, f'Error al crear oportunidad CRM: {str(e)}')
        
        alerta.save()
        
        messages.success(request, f'Alerta {alerta.codigo} procesada correctamente.')
        return redirect('centroSoluciones:alerta_detail', alerta_id=alerta.id)
    
    # Calcular horas del tiempo pendiente para el template
    tiempo_pendiente_seconds_hours = 0
    if alerta.tiempo_pendiente:
        tiempo_pendiente_seconds_hours = int(alerta.tiempo_pendiente.total_seconds() // 3600)
    
    context = {
        'alerta': alerta,
        'alerta_tiempo_pendiente_seconds_hours': tiempo_pendiente_seconds_hours,
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
        
        # Crear embudo de ventas automáticamente
        try:
            embudo = EmbudoVentas.objects.create(
                cliente=cliente,
                etapa='CONTACTO_INICIAL',
                origen='LEAD_JD',
                valor_estimado=valor,
                # Sin probabilidad de cierre
                descripcion_negocio=f"Lead John Deere: {descripcion}",
                observaciones=f"Lead creado automáticamente desde Centro de Soluciones. Clasificación: {dict(LeadJohnDeere.CLASIFICACION_CHOICES)[clasificacion]}",
                lead_jd=lead,
                creado_por=request.user
            )
            
            # Crear contacto inicial automático
            ContactoCliente.objects.create(
                cliente=cliente,
                tipo_contacto='VISITA',
                descripcion=f"Lead John Deere recibido: {descripcion}",
                resultado='EXITOSO',
                observaciones=f"Lead automático creado desde Centro de Soluciones. Equipo: {equipo.numero_serie}",
                responsable=request.user,
                embudo_ventas=embudo
            )
            
        except Exception as e:
            # Si falla la creación del embudo, no fallar el lead
            print(f"Error al crear embudo de ventas: {str(e)}")
        
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

@login_required
def lead_detail(request, lead_id):
    """Detalle de un lead específico"""
    
    # Solo gerentes y administrativos pueden ver leads
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para ver leads.')
        return redirect('centroSoluciones:centro_soluciones_dashboard')
    
    # Obtener el lead
    lead = get_object_or_404(LeadJohnDeere, id=lead_id, sucursal=request.user.sucursal)
    
    # Obtener embudo de ventas asociado
    embudo = None
    try:
        embudo = EmbudoVentas.objects.filter(lead_jd=lead).first()
    except:
        pass
    
    context = {
        'lead': lead,
        'embudo': embudo,
    }
    
    return render(request, 'centroSoluciones/lead_detail.html', context)

@login_required
def lead_edit(request, lead_id):
    """Vista para editar un lead"""
    
    # Solo gerentes y administrativos pueden editar leads
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para editar leads.')
        return redirect('centroSoluciones:leads_list')
    
    # Obtener el lead
    lead = get_object_or_404(LeadJohnDeere, id=lead_id, sucursal=request.user.sucursal)
    
    if request.method == 'POST':
        # Procesar el formulario
        estado = request.POST.get('estado')
        clasificacion = request.POST.get('clasificacion')
        descripcion = request.POST.get('descripcion')
        observaciones_contacto = request.POST.get('observaciones_contacto', '')
        valor_estimado = request.POST.get('valor_estimado', '')
        
        # Actualizar lead
        lead.estado = estado
        lead.clasificacion = clasificacion
        lead.descripcion = descripcion
        lead.observaciones_contacto = observaciones_contacto
        
        # Convertir valor estimado
        if valor_estimado:
            try:
                lead.valor_estimado = float(valor_estimado)
            except ValueError:
                messages.error(request, 'El valor estimado debe ser un número válido.')
                return redirect('centroSoluciones:lead_edit', lead_id=lead.id)
        else:
            lead.valor_estimado = None
        
        lead.save()
        
        # Actualizar embudo de ventas asociado si existe
        try:
            embudo = EmbudoVentas.objects.filter(lead_jd=lead).first()
            if embudo:
                embudo.valor_estimado = lead.valor_estimado
                embudo.descripcion_negocio = f"Lead John Deere: {lead.descripcion}"
                embudo.observaciones = f"Lead actualizado desde Centro de Soluciones. Clasificación: {lead.get_clasificacion_display()}"
                embudo.save()
        except Exception as e:
            print(f"Error al actualizar embudo de ventas: {str(e)}")
        
        messages.success(request, f'Lead actualizado correctamente.')
        return redirect('centroSoluciones:lead_detail', lead_id=lead.id)
    
    context = {
        'lead': lead,
    }
    
    return render(request, 'centroSoluciones/lead_edit.html', context)

@login_required
def obtener_codigo_alerta(request):
    """Vista para obtener información de un código de alerta específico (AJAX)"""
    codigo = request.GET.get('codigo')
    modelo_equipo = request.GET.get('modelo_equipo')
    
    if not codigo:
        return JsonResponse({'success': False, 'message': 'Código de alerta requerido'})
    
    try:
        # Buscar el código de alerta
        codigo_alerta = CodigoAlerta.objects.filter(
            codigo=codigo,
            activo=True
        ).first()
        
        if codigo_alerta:
            # Si se especifica modelo, verificar que coincida
            if modelo_equipo and codigo_alerta.modelo_equipo != modelo_equipo:
                # Buscar una versión específica para ese modelo
                codigo_especifico = CodigoAlerta.objects.filter(
                    codigo=codigo,
                    modelo_equipo=modelo_equipo,
                    activo=True
                ).first()
                if codigo_especifico:
                    codigo_alerta = codigo_especifico
            
            return JsonResponse({
                'success': True,
                'codigo_alerta': {
                    'codigo': codigo_alerta.codigo,
                    'modelo_equipo': codigo_alerta.modelo_equipo,
                    'descripcion': codigo_alerta.descripcion,
                    'clasificacion': codigo_alerta.clasificacion,
                    'instrucciones_resolucion': codigo_alerta.instrucciones_resolucion,
                    'repuestos_comunes': codigo_alerta.repuestos_comunes,
                    'tiempo_estimado_resolucion': codigo_alerta.tiempo_estimado_resolucion,
                }
            })
        else:
            return JsonResponse({
                'success': False, 
                'message': f'Código de alerta {codigo} no encontrado en la base de datos'
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al buscar código de alerta: {str(e)}'})

@login_required
def obtener_modelos_equipos(request):
    """Vista para obtener modelos de equipos disponibles (AJAX)"""
    try:
        from clientes.models import ModeloEquipo
        modelos = ModeloEquipo.objects.values('id', 'nombre').order_by('nombre')
        return JsonResponse({
            'success': True,
            'modelos': list(modelos)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al obtener modelos: {str(e)}'})

@login_required
def gestionar_codigos_alerta(request):
    """Vista para gestionar códigos de alerta"""
    
    # Solo gerentes y administrativos pueden gestionar códigos
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permisos para gestionar códigos de alerta.')
        return redirect('centroSoluciones:centro_soluciones_dashboard')
    
    # Obtener códigos con filtros
    codigos = CodigoAlerta.objects.all()
    
    # Aplicar filtros
    search = request.GET.get('search')
    clasificacion = request.GET.get('clasificacion')
    modelo = request.GET.get('modelo')
    activo = request.GET.get('activo')
    
    if search:
        codigos = codigos.filter(
            Q(codigo__icontains=search) |
            Q(descripcion__icontains=search) |
            Q(modelo_equipo__icontains=search)
        )
    
    if clasificacion:
        codigos = codigos.filter(clasificacion=clasificacion)
    
    if modelo:
        codigos = codigos.filter(modelo_equipo__icontains=modelo)
    
    if activo is not None:
        codigos = codigos.filter(activo=activo == 'true')
    
    # Ordenar por código
    codigos = codigos.order_by('codigo')
    
    # Paginación
    paginator = Paginator(codigos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener modelos únicos para el filtro
    modelos_unicos = CodigoAlerta.objects.values_list('modelo_equipo', flat=True).distinct().order_by('modelo_equipo')
    
    context = {
        'page_obj': page_obj,
        'search_filtro': search,
        'clasificacion_filtro': clasificacion,
        'modelo_filtro': modelo,
        'activo_filtro': activo,
        'modelos_unicos': modelos_unicos,
        'clasificaciones': CodigoAlerta.CLASIFICACION_CHOICES,
    }
    
    return render(request, 'centroSoluciones/gestionar_codigos_alerta.html', context)

@login_required
def crear_codigo_alerta(request):
    """Vista para crear un nuevo código de alerta"""
    
    # Solo gerentes y administrativos pueden crear códigos
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        return JsonResponse({'success': False, 'message': 'No tienes permisos para crear códigos de alerta.'})
    
    if request.method == 'POST':
        try:
            codigo = request.POST.get('codigo')
            modelo_equipo = request.POST.get('modelo_equipo')
            descripcion = request.POST.get('descripcion')
            clasificacion = request.POST.get('clasificacion')
            instrucciones = request.POST.get('instrucciones_resolucion', '')
            repuestos = request.POST.get('repuestos_comunes', '')
            tiempo_estimado = request.POST.get('tiempo_estimado_resolucion')
            
            # Validaciones
            if not all([codigo, modelo_equipo, descripcion, clasificacion]):
                return JsonResponse({'success': False, 'message': 'Todos los campos obligatorios deben estar completos.'})
            
            # Verificar si el código ya existe
            if CodigoAlerta.objects.filter(codigo=codigo).exists():
                return JsonResponse({'success': False, 'message': f'El código {codigo} ya existe en la base de datos.'})
            
            # Crear el código
            nuevo_codigo = CodigoAlerta(
                codigo=codigo,
                modelo_equipo=modelo_equipo,
                descripcion=descripcion,
                clasificacion=clasificacion,
                instrucciones_resolucion=instrucciones,
                repuestos_comunes=repuestos,
                tiempo_estimado_resolucion=tiempo_estimado if tiempo_estimado else None,
                creado_por=request.user
            )
            nuevo_codigo.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Código {codigo} creado exitosamente.',
                'codigo_id': nuevo_codigo.id
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error al crear el código: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'})

@login_required
def obtener_lista_codigos_alerta(request):
    """Vista API para obtener lista de códigos de alerta (AJAX)"""
    try:
        codigos = CodigoAlerta.objects.filter(activo=True).values(
            'codigo', 'modelo_equipo', 'descripcion', 'clasificacion'
        ).order_by('codigo')
        
        return JsonResponse({
            'success': True,
            'codigos': list(codigos)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al obtener códigos: {str(e)}'})

# Vistas para Reportes CSC
@login_required
def lista_reportes_csc(request):
    """Lista de todos los reportes CSC"""
    reportes = ReporteCSC.objects.select_related('equipo', 'equipo__cliente', 'creado_por').all()
    
    # Filtros
    equipo_id = request.GET.get('equipo')
    if equipo_id:
        reportes = reportes.filter(equipo_id=equipo_id)
    
    estado = request.GET.get('estado')
    if estado:
        reportes = reportes.filter(estado=estado)
    
    context = {
        'reportes': reportes,
        'equipos': Equipo.objects.filter(activo=True).select_related('cliente'),
    }
    return render(request, 'centroSoluciones/lista_reportes_csc.html', context)

@login_required
def importar_reporte_csc(request):
    """Importar archivo CSV y crear reporte CSC"""
    if request.method == 'POST':
        archivo = request.FILES.get('archivo_csv')
        cliente_id = request.POST.get('cliente')
        equipo_id = request.POST.get('equipo')
        
        if not archivo:
            messages.error(request, 'Debe seleccionar un archivo CSV.')
            return redirect('centroSoluciones:lista_reportes_csc')
        
        if not cliente_id:
            messages.error(request, 'Debe seleccionar un cliente.')
            return redirect('centroSoluciones:lista_reportes_csc')
        
        if not equipo_id:
            messages.error(request, 'Debe seleccionar un equipo.')
            return redirect('centroSoluciones:lista_reportes_csc')
        
        try:
            # Obtener cliente y equipo seleccionados
            cliente = get_object_or_404(Cliente, id=cliente_id)
            equipo = get_object_or_404(Equipo, id=equipo_id, cliente=cliente)
            
            # Extraer fecha del nombre del archivo
            nombre_archivo = archivo.name
            print(f"DEBUG: Procesando archivo: {nombre_archivo}")
            
            fecha_reporte = extraer_fecha_desde_nombre(nombre_archivo)
            print(f"DEBUG: Fecha extraída: {fecha_reporte}")
            
            if not fecha_reporte:
                messages.error(request, 'No se pudo extraer la fecha del reporte del nombre del archivo.')
                return redirect('centroSoluciones:lista_reportes_csc')
            
            # Calcular período analizado (mes completo)
            from datetime import datetime, timedelta
            import calendar
            
            # Si la fecha es el día 8, asumimos que es el reporte del mes anterior
            if fecha_reporte.day <= 15:
                # Es reporte del mes anterior
                primer_dia = fecha_reporte.replace(day=1)
                ultimo_dia = fecha_reporte.replace(day=calendar.monthrange(fecha_reporte.year, fecha_reporte.month)[1])
            else:
                # Es reporte del mes actual
                primer_dia = fecha_reporte.replace(day=1)
                ultimo_dia = fecha_reporte.replace(day=calendar.monthrange(fecha_reporte.year, fecha_reporte.month)[1])
            
            periodo_analizado = f"{primer_dia.strftime('%d/%m/%Y')} - {ultimo_dia.strftime('%d/%m/%Y')}"
            print(f"DEBUG: Período analizado: {periodo_analizado}")
            
            # Crear reporte
            print("DEBUG: Creando reporte en la base de datos...")
            reporte = ReporteCSC.objects.create(
                equipo=equipo,
                fecha_reporte=fecha_reporte,
                archivo_csv=archivo,
                creado_por=request.user
            )
            
            # Guardar período analizado en comentarios manuales temporalmente
            reporte.comentarios_manuales = f"Período analizado: {periodo_analizado}"
            reporte.save()
            print(f"DEBUG: Reporte creado con ID: {reporte.id}")
            
            # Procesar CSV
            print("DEBUG: Procesando CSV...")
            procesar_csv_reporte(reporte)
            print("DEBUG: CSV procesado exitosamente")
            
            # Generar recomendaciones automáticas
            print("DEBUG: Generando recomendaciones...")
            generar_recomendaciones_automaticas(reporte)
            print("DEBUG: Recomendaciones generadas")
            
            messages.success(request, f'Reporte CSC importado exitosamente para el equipo {equipo.numero_serie}')
            return redirect('centroSoluciones:detalle_reporte_csc', reporte_id=reporte.id)
            
        except Exception as e:
            print(f"ERROR general procesando CSV: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Error al procesar el archivo: {str(e)}')
            return redirect('centroSoluciones:lista_reportes_csc')
    
    # Para GET, mostrar formulario con selects
    clientes = Cliente.objects.filter(activo=True).order_by('razon_social')
    context = {
        'clientes': clientes,
    }
    return render(request, 'centroSoluciones/importar_reporte_csc.html', context)

@login_required
def detalle_reporte_csc(request, reporte_id):
    """Ver detalles de un reporte CSC"""
    reporte = get_object_or_404(
        ReporteCSC.objects.select_related('equipo', 'equipo__cliente', 'creado_por'),
        id=reporte_id
    )
    
    # Analizar categorías disponibles dinámicamente
    categorias_disponibles = analizar_categorias_disponibles(reporte)
    
    # Ordenar categorías por prioridad
    categorias_ordenadas = sorted(
        categorias_disponibles.items(), 
        key=lambda x: x[1]['prioridad']
    )
    
    # Convertir a formato para template
    categorias_lista = []
    datos_por_categoria_js = {}
    
    for categoria, config in categorias_ordenadas:
        # Solo incluir categorías con datos
        if config['datos']:
            # Preparar datos para la tabla
            datos_tabla = []
            for dato in config['datos']:
                datos_tabla.append({
                    'serie': dato.serie,
                    'valor': float(dato.valor),
                    'unidad': dato.unidad
                })
            
            categorias_lista.append({
                'nombre': categoria,
                'datos_tabla': datos_tabla,
                'tipo_grafico': config['tipo_grafico'],
                'prioridad': config['prioridad'],
                'total_valor': float(config['total_valor']),
                'unidades': config['unidades']
            })
            
            # Preparar datos para JavaScript
            datos_por_categoria_js[categoria] = {
                'labels': [d.serie for d in config['datos']],
                'data': [float(d.valor) for d in config['datos']],
                'tipo_grafico': config['tipo_grafico']
            }
    
    print(f"DEBUG: Categorías para template: {[c['nombre'] for c in categorias_lista]}")
    
    context = {
        'reporte': reporte,
        'categorias': categorias_lista,
        'datos_por_categoria_js': datos_por_categoria_js,
    }
    return render(request, 'centroSoluciones/detalle_reporte_csc.html', context)

@login_required
def generar_pdf_reporte_csc(request, reporte_id):
    """Generar PDF del reporte CSC usando el template principal con estilos de print"""
    reporte = get_object_or_404(
        ReporteCSC.objects.select_related('equipo', 'equipo__cliente', 'creado_por'),
        id=reporte_id
    )
    
    # Usar la misma lógica que detalle_reporte_csc para preparar los datos
    datos_por_categoria = {}
    for dato in reporte.datos.all():
        if dato.categoria not in datos_por_categoria:
            datos_por_categoria[dato.categoria] = []
        datos_por_categoria[dato.categoria].append(dato)
    
    # Analizar categorías disponibles
    categorias = analizar_categorias_disponibles(datos_por_categoria)
    
    # Preparar datos para gráficos
    datos_por_categoria_js = {}
    for categoria in categorias:
        datos_por_categoria_js[categoria['nombre']] = {
            'labels': [dato['serie'] for dato in categoria['datos_tabla']],
            'data': [float(dato['valor']) for dato in categoria['datos_tabla']],
            'tipo_grafico': categoria['tipo_grafico']
        }
    
    # Rutas de logos para el PDF
    logo_jd_horizontal_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'JDLOGOHORIZONTAL.png')
    logo_pm_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo_pm_fondo_blanco.png')
    
    context = {
        'reporte': reporte,
        'categorias': categorias,
        'datos_por_categoria_js': datos_por_categoria_js,
        'logo_jd_horizontal_path': logo_jd_horizontal_path,
        'logo_pm_path': logo_pm_path,
    }
    
    # Generar HTML usando el template PDF específico
    html = render_to_string('centroSoluciones/reporte_csc_pdf.html', context)
    
    # Crear respuesta PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_csc_{reporte.equipo.numero_serie}_{reporte.fecha_reporte}.pdf"'
    
    # Convertir HTML a PDF
    pisa_status = pisa.CreatePDF(io.StringIO(html), dest=response, link_callback=link_callback)
    
    if pisa_status.err:
        return HttpResponse("Hubo un error al generar el PDF", status=400)
    
    return response

@login_required
@require_http_methods(["POST"])
def actualizar_comentarios_csc(request, reporte_id):
    """Actualizar comentarios manuales del reporte CSC"""
    reporte = get_object_or_404(ReporteCSC, id=reporte_id)
    
    comentarios = request.POST.get('comentarios', '').strip()
    reporte.comentarios_manuales = comentarios
    reporte.save()
    
    messages.success(request, 'Comentarios actualizados correctamente.')
    return redirect('centroSoluciones:detalle_reporte_csc', reporte_id=reporte.id)

@login_required
def obtener_equipos_cliente_csc(request):
    """Obtener equipos de un cliente para el formulario de importación CSC"""
    cliente_id = request.GET.get('cliente_id')
    if cliente_id:
        equipos = Equipo.objects.filter(
            cliente_id=cliente_id, 
            activo=True
        ).values('id', 'numero_serie', 'modelo__nombre')
        return JsonResponse({'equipos': list(equipos)})
    return JsonResponse({'equipos': []})

@login_required
def regenerar_recomendaciones_csc(request, reporte_id):
    """Regenerar recomendaciones automáticas para un reporte CSC"""
    reporte = get_object_or_404(ReporteCSC, id=reporte_id)
    
    try:
        generar_recomendaciones_automaticas(reporte)
        messages.success(request, 'Recomendaciones regeneradas correctamente.')
    except Exception as e:
        messages.error(request, f'Error al regenerar recomendaciones: {str(e)}')
    
    return redirect('centroSoluciones:detalle_reporte_csc', reporte_id=reporte_id)

# Funciones auxiliares
def extraer_pin_desde_nombre(nombre_archivo):
    """Extraer PIN del equipo del nombre del archivo CSV"""
    try:
        # Formato esperado: 1BZ310LAANA008321_08_11_2025.csv
        # El PIN es la primera parte antes del primer guión bajo
        partes = nombre_archivo.replace('.csv', '').split('_')
        if len(partes) >= 1:
            pin = partes[0]
            # Validar que el PIN tenga el formato correcto (al menos 10 caracteres)
            if len(pin) >= 10:
                return pin
    except:
        pass
    
    return None

def extraer_fecha_desde_nombre(nombre_archivo):
    """Extraer fecha del nombre del archivo CSV"""
    try:
        # Formato esperado: 1BZ310LAANA008321_08_11_2025.csv
        partes = nombre_archivo.replace('.csv', '').split('_')
        if len(partes) >= 4:
            dia = int(partes[-3])
            mes = int(partes[-2])
            año = int(partes[-1])
            return datetime(año, mes, dia).date()
    except:
        pass
    
    # Si no se puede extraer, usar fecha actual
    return datetime.now().date()

def buscar_o_crear_equipo(pin_equipo, usuario):
    """Buscar un equipo por PIN o crearlo si no existe"""
    try:
        # Buscar si el equipo ya existe
        equipo = Equipo.objects.get(numero_serie=pin_equipo)
        return equipo, False  # False = no fue creado
    except Equipo.DoesNotExist:
        # Para equipos nuevos que no existen en la base de datos, usar "SinCliente"
        cliente_por_defecto = Cliente.objects.filter(
            razon_social__icontains='SinCliente',
            activo=True
        ).first()
        print(f"DEBUG: Cliente SinCliente encontrado: {cliente_por_defecto.razon_social if cliente_por_defecto else 'No encontrado'}")
        
        # Si no hay SinCliente, usar el primer cliente activo como último recurso
        if not cliente_por_defecto:
            cliente_por_defecto = Cliente.objects.filter(activo=True).first()
            print(f"DEBUG: Usando primer cliente activo como último recurso: {cliente_por_defecto.razon_social if cliente_por_defecto else 'No hay clientes activos'}")
        
        # Mostrar todos los clientes activos para referencia
        clientes_activos = Cliente.objects.filter(activo=True).values_list('razon_social', flat=True)[:5]
        print(f"DEBUG: Primeros 5 clientes activos: {list(clientes_activos)}")
        
        # Buscar un modelo de equipo por defecto (310L si existe)
        modelo_por_defecto = None
        try:
            modelo_por_defecto = ModeloEquipo.objects.filter(
                nombre__icontains='310L',
                activo=True
            ).first()
        except:
            pass
        
        # Si no hay modelo 310L, usar el primer modelo activo
        if not modelo_por_defecto:
            modelo_por_defecto = ModeloEquipo.objects.filter(activo=True).first()
        
        # Crear el equipo con cliente y modelo por defecto
        equipo = Equipo.objects.create(
            numero_serie=pin_equipo,
            cliente=cliente_por_defecto,
            modelo=modelo_por_defecto,
            activo=True
        )
        
        print(f"DEBUG: Equipo creado con cliente: {cliente_por_defecto.razon_social if cliente_por_defecto else 'Sin cliente'}")
        print(f"DEBUG: Equipo creado con modelo: {modelo_por_defecto.nombre if modelo_por_defecto else 'Sin modelo'}")
        
        return equipo, True  # True = fue creado

def procesar_csv_reporte(reporte):
    """Procesar archivo CSV y guardar datos"""
    try:
        # Leer CSV usando el archivo directamente
        with reporte.archivo_csv.open('r') as file:
            df = pd.read_csv(file)
        
        # Debug: imprimir información del CSV
        print(f"DEBUG: CSV cargado - {len(df)} filas, columnas: {list(df.columns)}")
        print(f"DEBUG: Primeras 3 filas:")
        print(df.head(3))
        print(f"DEBUG: Tipos de datos:")
        print(df.dtypes)
        print(f"DEBUG: Valores únicos en columnas:")
        for col in df.columns:
            print(f"  {col}: {df[col].nunique()} valores únicos")
            if df[col].nunique() < 10:
                print(f"    Valores: {df[col].unique()}")
        
        # Mapear nombres de columnas (flexible)
        column_mapping = {
            'categoria': ['Categoría', 'Category', 'categoria', 'category'],
            'serie': ['Serie', 'Series', 'serie', 'series'],
            'valor': ['Valor', 'Value', 'valor', 'value'],
            'unidad': ['Unidades de medida', 'Unit', 'Units', 'unidad', 'unit', 'units'],
            'fecha_inicio': ['Fecha de inicio', 'Start Date', 'Start date', 'fecha_inicio', 'start_date'],
            'fecha_fin': ['Fecha de terminación', 'End Date', 'End date', 'fecha_fin', 'end_date']
        }
        
        # Encontrar las columnas correctas
        actual_columns = {}
        for key, possible_names in column_mapping.items():
            for name in possible_names:
                if name in df.columns:
                    actual_columns[key] = name
                    break
            if key not in actual_columns:
                print(f"ERROR: No se encontró columna para {key}. Columnas disponibles: {list(df.columns)}")
                raise Exception(f"No se encontró columna para {key}")
        
        print(f"DEBUG: Mapeo de columnas: {actual_columns}")
        
        # Procesar cada fila
        for index, row in df.iterrows():
            try:
                # Extraer valores con manejo de errores
                categoria = str(row[actual_columns['categoria']]).strip()
                serie = str(row[actual_columns['serie']]).strip()
                valor = float(row[actual_columns['valor']])
                unidad = str(row[actual_columns['unidad']]).strip()
                
                # Procesar fechas con múltiples formatos
                fecha_inicio_str = str(row[actual_columns['fecha_inicio']]).strip()
                fecha_fin_str = str(row[actual_columns['fecha_fin']]).strip()
                
                # Intentar diferentes formatos de fecha
                fecha_inicio = None
                fecha_fin = None
                
                date_formats = ['%d %b %Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']
                
                for fmt in date_formats:
                    try:
                        fecha_inicio = datetime.strptime(fecha_inicio_str, fmt).date()
                        break
                    except:
                        continue
                
                for fmt in date_formats:
                    try:
                        fecha_fin = datetime.strptime(fecha_fin_str, fmt).date()
                        break
                    except:
                        continue
                
                if fecha_inicio is None or fecha_fin is None:
                    print(f"ERROR: No se pudo parsear fecha en fila {index}: inicio='{fecha_inicio_str}', fin='{fecha_fin_str}'")
                    continue
                
                # Crear registro
                DatosReporteCSC.objects.create(
                    reporte=reporte,
                    categoria=categoria,
                    serie=serie,
                    valor=valor,
                    unidad=unidad,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                )
                
                print(f"DEBUG: Procesada fila {index}: {categoria} - {serie} = {valor} {unidad}")
                
            except Exception as row_error:
                print(f"ERROR procesando fila {index}: {row_error}")
                continue
        
        # Calcular total de horas utilizadas del equipo
        datos_guardados = reporte.datos.all()
        print(f"DEBUG: Datos guardados: {datos_guardados.count()} registros")
        
        # Buscar categorías de motor/engine (diferentes variaciones)
        categorias_motor = []
        for dato in datos_guardados:
            categoria_lower = dato.categoria.lower()
            if any(palabra in categoria_lower for palabra in ['motor', 'engine', 'utilización']):
                if dato.categoria not in categorias_motor:
                    categorias_motor.append(dato.categoria)
        
        print(f"DEBUG: Categorías de motor encontradas: {categorias_motor}")
        
        # ELEGIR SOLO UNA CATEGORÍA como referencia para el total de horas
        # Prioridad: 1. "Utilización del motor", 2. Primera categoría de motor encontrada
        categoria_referencia = None
        if 'Utilización del motor' in categorias_motor:
            categoria_referencia = 'Utilización del motor'
        elif categorias_motor:
            categoria_referencia = categorias_motor[0]
        
        print(f"DEBUG: Categoría de referencia seleccionada: {categoria_referencia}")
        
        # Sumar horas SOLO de la categoría de referencia
        total_horas = 0
        if categoria_referencia:
            motor_data = datos_guardados.filter(categoria=categoria_referencia)
            total_horas = sum([d.valor for d in motor_data])
            print(f"DEBUG: Total horas de {categoria_referencia}: {total_horas}")
        else:
            # Fallback: buscar cualquier categoría con horas
            categorias_con_horas = []
            for dato in datos_guardados:
                if 'hr' in dato.unidad.lower() and dato.categoria not in categorias_con_horas:
                    categorias_con_horas.append(dato.categoria)
            
            if categorias_con_horas:
                categoria_referencia = categorias_con_horas[0]
                motor_data = datos_guardados.filter(categoria=categoria_referencia)
                total_horas = sum([d.valor for d in motor_data])
                print(f"DEBUG: Total horas de {categoria_referencia} (fallback): {total_horas}")
        
        reporte.total_horas_analizadas = total_horas
        
        # Calcular eficiencia
        if datos_guardados.filter(categoria__icontains='motor').exists():
            motor_data = datos_guardados.filter(categoria__icontains='motor')
            
            # Buscar diferentes tipos de carga
            carga_alta = motor_data.filter(serie__icontains='alta').first()
            carga_mediana = motor_data.filter(serie__icontains='mediana').first()
            carga_baja = motor_data.filter(serie__icontains='baja').first()
            en_reposo = motor_data.filter(serie__icontains='reposo').first()
            
            carga_alta_valor = carga_alta.valor if carga_alta else 0
            carga_mediana_valor = carga_mediana.valor if carga_mediana else 0
            carga_baja_valor = carga_baja.valor if carga_baja else 0
            en_reposo_valor = en_reposo.valor if en_reposo else 0
            
                    # Calcular eficiencia: (carga alta + carga mediana) / total horas
        tiempo_productivo = carga_alta_valor + carga_mediana_valor
        eficiencia = (tiempo_productivo / total_horas) * 100 if total_horas > 0 else 0
        
        # Calcular horas utilizadas (tiempo total de uso del equipo)
        horas_utilizadas = total_horas  # El total ya incluye todas las horas de uso
        
        print(f"DEBUG: Cálculo de eficiencia:")
        print(f"  - Carga alta: {carga_alta_valor} hr")
        print(f"  - Carga mediana: {carga_mediana_valor} hr")
        print(f"  - Carga baja: {carga_baja_valor} hr")
        print(f"  - En reposo: {en_reposo_valor} hr")
        print(f"  - Tiempo productivo: {tiempo_productivo} hr")
        print(f"  - Total horas: {total_horas} hr")
        print(f"  - Horas utilizadas (tiempo total): {horas_utilizadas} hr")
        print(f"  - Eficiencia: {eficiencia:.2f}%")
        
        reporte.eficiencia_general = eficiencia
        # Guardar horas utilizadas en comentarios_manuales temporalmente
        if reporte.comentarios_manuales:
            reporte.comentarios_manuales += f"\nHoras utilizadas: {horas_utilizadas:.1f} hr"
        else:
            reporte.comentarios_manuales = f"Horas utilizadas: {horas_utilizadas:.1f} hr"
        
        # Analizar categorías disponibles para gráficos dinámicos
        categorias_disponibles = analizar_categorias_disponibles(reporte)
        reporte.comentarios_manuales += f"\nCategorías detectadas: {', '.join(categorias_disponibles.keys())}"
        
        reporte.save()
        print(f"DEBUG: Reporte guardado exitosamente")
        print(f"DEBUG: Categorías detectadas: {list(categorias_disponibles.keys())}")
        
    except Exception as e:
        print(f"ERROR general procesando CSV: {str(e)}")
        print(f"ERROR tipo: {type(e).__name__}")
        import traceback
        print(f"ERROR traceback: {traceback.format_exc()}")
        raise Exception(f"Error procesando CSV: {str(e)}")

def analizar_categorias_disponibles(reporte):
    """Analizar las categorías disponibles en el reporte y determinar tipos de gráficos"""
    categorias = {}
    
    # Agrupar datos por categoría
    datos_por_categoria = {}
    for dato in reporte.datos.all():
        if dato.categoria not in datos_por_categoria:
            datos_por_categoria[dato.categoria] = []
        datos_por_categoria[dato.categoria].append(dato)
    
    print(f"DEBUG: Analizando {len(datos_por_categoria)} categorías")
    
    for categoria, datos in datos_por_categoria.items():
        # Determinar tipo de gráfico basado en la categoría y datos
        tipo_grafico = determinar_tipo_grafico(categoria, datos)
        prioridad = calcular_prioridad_categoria(categoria)
        
        categorias[categoria] = {
            'tipo_grafico': tipo_grafico,
            'prioridad': prioridad,
            'datos': datos,
            'total_valor': sum(d.valor for d in datos),
            'unidades': datos[0].unidad if datos else 'hr'
        }
        
        print(f"DEBUG: Categoría '{categoria}' - Tipo: {tipo_grafico}, Prioridad: {prioridad}")
    
    return categorias

def determinar_tipo_grafico(categoria, datos):
    """Determinar el tipo de gráfico más apropiado para una categoría"""
    categoria_lower = categoria.lower()
    
    # Gráficos de torta para distribución de tiempo/uso
    if any(palabra in categoria_lower for palabra in ['utilización', 'uso', 'modos', 'tiempo']):
        return 'pie'
    
    # Gráficos de barras para comparaciones
    elif any(palabra in categoria_lower for palabra in ['marcha', 'gear', 'velocidad', 'carga']):
        return 'bar'
    
    # Gráficos de líneas para tendencias
    elif any(palabra in categoria_lower for palabra in ['temperatura', 'presión', 'consumo']):
        return 'line'
    
    # Por defecto, gráfico de barras
    return 'bar'

def calcular_prioridad_categoria(categoria):
    """Calcular la prioridad de una categoría para mostrar en el reporte"""
    categoria_lower = categoria.lower()
    
    # Alta prioridad: métricas principales
    if any(palabra in categoria_lower for palabra in ['motor', 'combustible', 'utilización']):
        return 1
    
    # Media prioridad: métricas específicas del equipo
    elif any(palabra in categoria_lower for palabra in ['marcha', 'gear', 'modos', 'tiempo']):
        return 2
    
    # Baja prioridad: métricas secundarias
    else:
        return 3

def generar_recomendaciones_automaticas(reporte):
    """Generar recomendaciones automáticas basadas en los datos"""
    recomendaciones = []
    
    print(f"DEBUG: Generando recomendaciones para reporte {reporte.id}")
    print(f"DEBUG: Total horas analizadas: {reporte.total_horas_analizadas}")
    
    # Obtener datos principales
    datos = {}
    for dato in reporte.datos.all():
        if dato.categoria not in datos:
            datos[dato.categoria] = {}
        datos[dato.categoria][dato.serie] = dato.valor
    
    print(f"DEBUG: Categorías disponibles: {list(datos.keys())}")
    
    # Análisis de utilización del motor
    if 'Utilización del motor' in datos:
        motor = datos['Utilización del motor']
        print(f"DEBUG: Datos de motor: {motor}")
        
        # Buscar diferentes variaciones del nombre "En reposo"
        en_reposo = 0
        for key in motor.keys():
            if 'reposo' in key.lower():
                en_reposo = motor[key]
                print(f"DEBUG: Encontrado tiempo en reposo en '{key}': {en_reposo}")
                break
        
        carga_alta = motor.get('Carga alta', 0)
        carga_mediana = motor.get('Carga mediana', 0)
        carga_baja = motor.get('Carga baja', 0)
        
        print(f"DEBUG: En reposo: {en_reposo}, Carga alta: {carga_alta}, Carga mediana: {carga_mediana}")
        
        # Recomendación por tiempo en reposo (umbral del 15% como máximo aceptable)
        if en_reposo > 0:
            porcentaje_reposo = (en_reposo / reporte.total_horas_analizadas) * 100 if reporte.total_horas_analizadas > 0 else 0
            print(f"DEBUG: Porcentaje en reposo: {porcentaje_reposo:.1f}%")
            
            if porcentaje_reposo > 50:
                recomendaciones.append(f"🚨 CRÍTICO: Tiempo excesivo en reposo ({en_reposo:.1f} hr, {porcentaje_reposo:.1f}%). Máximo aceptable: 15%. Urgente optimización de horarios de trabajo.")
            elif porcentaje_reposo > 30:
                recomendaciones.append(f"⚠️ Alto tiempo en reposo ({en_reposo:.1f} hr, {porcentaje_reposo:.1f}%). Máximo aceptable: 15%. Considerar optimizar horarios de trabajo.")
            elif porcentaje_reposo > 15:
                recomendaciones.append(f"⚠️ Tiempo en reposo superior al recomendado ({en_reposo:.1f} hr, {porcentaje_reposo:.1f}%). Máximo aceptable: 15%. Revisar eficiencia operativa.")
            else:
                recomendaciones.append(f"✅ Tiempo en reposo dentro de parámetros aceptables ({en_reposo:.1f} hr, {porcentaje_reposo:.1f}%).")
        
        # Recomendación por eficiencia
        tiempo_productivo = carga_alta + carga_mediana
        eficiencia = (tiempo_productivo / reporte.total_horas_analizadas) * 100 if reporte.total_horas_analizadas > 0 else 0
        
        if eficiencia < 30:
            recomendaciones.append(f"⚠️ Eficiencia muy baja ({eficiencia:.1f}%). Urgente optimización de operaciones.")
        elif eficiencia < 50:
            recomendaciones.append(f"⚠️ Eficiencia baja ({eficiencia:.1f}%). Considerar optimización de operaciones.")
        elif eficiencia < 70:
            recomendaciones.append(f"⚠️ Eficiencia moderada ({eficiencia:.1f}%). Hay espacio para mejoras.")
        else:
            recomendaciones.append(f"✅ Buena eficiencia del motor ({eficiencia:.1f}%).")
    
    # Análisis de modos de potencia de motor
    if 'Utilización de modos de potencia de motor' in datos:
        modos = datos['Utilización de modos de potencia de motor']
        print(f"DEBUG: Datos de modos de potencia: {modos}")
        
        modo_economico = modos.get('E', 0)
        modo_power = modos.get('P', 0)
        modo_high_power = modos.get('HP', 0)
        
        if modo_economico > 0:
            porcentaje_economico = (modo_economico / reporte.total_horas_analizadas) * 100
            if porcentaje_economico > 70:
                recomendaciones.append(f"✅ Excelente uso del modo económico ({modo_economico:.1f} hr, {porcentaje_economico:.1f}%).")
            elif porcentaje_economico < 30:
                recomendaciones.append(f"💡 Bajo uso del modo económico ({modo_economico:.1f} hr, {porcentaje_economico:.1f}%). Considerar mayor uso para ahorro de combustible.")
    
    # Análisis de utilización de excavadora
    if 'Utilización de excavadora' in datos:
        excavadora = datos['Utilización de excavadora']
        print(f"DEBUG: Datos de excavadora: {excavadora}")
        
        sin_actividad = excavadora.get('Sin actividad', 0)
        if sin_actividad > 0:
            porcentaje_inactividad = (sin_actividad / reporte.total_horas_analizadas) * 100
            if porcentaje_inactividad > 40:
                recomendaciones.append(f"⚠️ Alta inactividad de excavadora ({sin_actividad:.1f} hr, {porcentaje_inactividad:.1f}%). Revisar planificación de tareas.")
    
    # Si no hay recomendaciones específicas, agregar una general
    if not recomendaciones:
        recomendaciones.append("📊 Análisis completado. Los datos muestran un uso estándar del equipo.")
    
    print(f"DEBUG: Recomendaciones generadas: {len(recomendaciones)}")
    for i, rec in enumerate(recomendaciones, 1):
        print(f"  {i}. {rec}")
    
    # Guardar recomendaciones
    reporte.recomendaciones_automaticas = '\n'.join(recomendaciones)
    reporte.save()
    print(f"DEBUG: Recomendaciones guardadas en el reporte")

def link_callback(uri, rel):
    """Callback para manejar archivos estáticos en PDF"""
    if uri.startswith('/static/'):
        static_path = uri.replace('/static/', '')
        path = os.path.join(settings.BASE_DIR, 'static', static_path)
    elif uri.startswith('/media/'):
        media_path = uri.replace('/media/', '')
        path = os.path.join(settings.MEDIA_ROOT, media_path)
    else:
        return uri
    
    if not os.path.isfile(path):
        print(f"ADVERTENCIA: Archivo no encontrado: {path}")
        return uri
    
    return path
