from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import AlertaEquipo, LeadJohnDeere, AsignacionAlerta, CodigoAlerta
from clientes.models import Cliente, Equipo
from recursosHumanos.models import Usuario, Sucursal
from crm.models import EmbudoVentas, ContactoCliente

# Importaciones para Reportes CSC
import pandas as pd
import os
from datetime import datetime
from django.core.files.storage import default_storage
from django.contrib import messages
from django.http import JsonResponse
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
        equipo_id = request.POST.get('equipo')
        
        if not archivo or not equipo_id:
            messages.error(request, 'Debe seleccionar un archivo CSV y un equipo.')
            return redirect('centroSoluciones:lista_reportes_csc')
        
        try:
            equipo = Equipo.objects.get(id=equipo_id)
            
            # Extraer fecha del nombre del archivo
            nombre_archivo = archivo.name
            fecha_reporte = extraer_fecha_desde_nombre(nombre_archivo)
            
            # Crear reporte
            reporte = ReporteCSC.objects.create(
                equipo=equipo,
                fecha_reporte=fecha_reporte,
                archivo_csv=archivo,
                creado_por=request.user
            )
            
            # Procesar CSV
            procesar_csv_reporte(reporte)
            
            # Generar recomendaciones automáticas
            generar_recomendaciones_automaticas(reporte)
            
            messages.success(request, f'Reporte CSC importado exitosamente para {equipo.numero_serie}')
            return redirect('centroSoluciones:detalle_reporte_csc', reporte_id=reporte.id)
            
        except Exception as e:
            messages.error(request, f'Error al importar reporte: {str(e)}')
            return redirect('centroSoluciones:lista_reportes_csc')
    
    context = {
        'equipos': Equipo.objects.filter(activo=True).select_related('cliente'),
    }
    return render(request, 'centroSoluciones/importar_reporte_csc.html', context)

@login_required
def detalle_reporte_csc(request, reporte_id):
    """Ver detalles de un reporte CSC"""
    reporte = get_object_or_404(
        ReporteCSC.objects.select_related('equipo', 'equipo__cliente', 'creado_por'),
        id=reporte_id
    )
    
    # Agrupar datos por categoría
    datos_por_categoria = {}
    for dato in reporte.datos.all():
        if dato.categoria not in datos_por_categoria:
            datos_por_categoria[dato.categoria] = []
        datos_por_categoria[dato.categoria].append(dato)
    
    context = {
        'reporte': reporte,
        'datos_por_categoria': datos_por_categoria,
    }
    return render(request, 'centroSoluciones/detalle_reporte_csc.html', context)

@login_required
def generar_pdf_reporte_csc(request, reporte_id):
    """Generar PDF del reporte CSC"""
    reporte = get_object_or_404(
        ReporteCSC.objects.select_related('equipo', 'equipo__cliente', 'creado_por'),
        id=reporte_id
    )
    
    # Agrupar datos por categoría
    datos_por_categoria = {}
    for dato in reporte.datos.all():
        if dato.categoria not in datos_por_categoria:
            datos_por_categoria[dato.categoria] = []
        datos_por_categoria[dato.categoria].append(dato)
    
    context = {
        'reporte': reporte,
        'datos_por_categoria': datos_por_categoria,
    }
    
    # Generar HTML
    html = render_to_string('centroSoluciones/reporte_csc_pdf.html', context)
    
    # Crear respuesta PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_csc_{reporte.equipo.numero_serie}_{reporte.fecha_reporte}.pdf"'
    
    # Convertir HTML a PDF
    pisa_status = pisa.CreatePDF(io.StringIO(html), dest=response, link_callback=link_callback)
    
    if pisa_status.err:
        return HttpResponse("Hubo un error al generar el PDF", status=400)
    
    return response

# Funciones auxiliares
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

def procesar_csv_reporte(reporte):
    """Procesar archivo CSV y guardar datos"""
    try:
        # Leer CSV
        df = pd.read_csv(reporte.archivo_csv.path)
        
        # Procesar cada fila
        for _, row in df.iterrows():
            DatosReporteCSC.objects.create(
                reporte=reporte,
                categoria=row['Categoría'],
                serie=row['Serie'],
                valor=float(row['Valor']),
                unidad=row['Unidades de medida'],
                fecha_inicio=datetime.strptime(row['Fecha de inicio'], '%d %b %Y').date(),
                fecha_fin=datetime.strptime(row['Fecha de terminación'], '%d %b %Y').date(),
            )
        
        # Calcular total de horas
        total_horas = df[df['Unidades de medida'] == 'hr']['Valor'].sum()
        reporte.total_horas_analizadas = total_horas
        
        # Calcular eficiencia
        if 'Utilización del motor' in df['Categoría'].values:
            motor_data = df[df['Categoría'] == 'Utilización del motor']
            carga_alta = motor_data[motor_data['Serie'] == 'Carga alta']['Valor'].iloc[0] if len(motor_data[motor_data['Serie'] == 'Carga alta']) > 0 else 0
            carga_mediana = motor_data[motor_data['Serie'] == 'Carga mediana']['Valor'].iloc[0] if len(motor_data[motor_data['Serie'] == 'Carga mediana']) > 0 else 0
            eficiencia = ((carga_alta + carga_mediana) / total_horas) * 100 if total_horas > 0 else 0
            reporte.eficiencia_general = eficiencia
        
        reporte.save()
        
    except Exception as e:
        raise Exception(f"Error procesando CSV: {str(e)}")

def generar_recomendaciones_automaticas(reporte):
    """Generar recomendaciones automáticas basadas en los datos"""
    recomendaciones = []
    
    # Obtener datos principales
    datos = {}
    for dato in reporte.datos.all():
        if dato.categoria not in datos:
            datos[dato.categoria] = {}
        datos[dato.categoria][dato.serie] = dato.valor
    
    # Análisis de utilización del motor
    if 'Utilización del motor' in datos:
        motor = datos['Utilización del motor']
        en_reposo = motor.get('En reposo', 0)
        carga_alta = motor.get('Carga alta', 0)
        carga_mediana = motor.get('Carga mediana', 0)
        
        if en_reposo > reporte.total_horas_analizadas * 0.5:  # Más del 50% en reposo
            recomendaciones.append(f"⚠️ Alto tiempo en reposo ({en_reposo} hr). Considerar optimizar horarios de trabajo.")
        
        tiempo_productivo = carga_alta + carga_mediana
        eficiencia = (tiempo_productivo / reporte.total_horas_analizadas) * 100 if reporte.total_horas_analizadas > 0 else 0
        
        if eficiencia < 50:
            recomendaciones.append(f"⚠️ Eficiencia baja ({eficiencia:.1f}%). Considerar optimización de operaciones.")
        else:
            recomendaciones.append(f"✅ Buena eficiencia del motor ({eficiencia:.1f}%).")
    
    # Análisis de modos de funcionamiento
    if 'Modos de funcionamiento' in datos:
        modos = datos['Modos de funcionamiento']
        ralenti_cargadora = modos.get('Ralentí de pala cargadora', 0)
        
        if ralenti_cargadora > reporte.total_horas_analizadas * 0.4:  # Más del 40% en ralentí
            recomendaciones.append(f"⚠️ Excesivo tiempo en ralentí de cargadora ({ralenti_cargadora} hr). Revisar procedimientos operativos.")
    
    # Análisis de marchas MFWD
    if 'MFWD Utilization per gear' in datos:
        mfwd = datos['MFWD Utilization per gear']
        f5_uso = mfwd.get('Activado - F5', 0)
        f4_uso = mfwd.get('Activado - F4', 0)
        
        if f5_uso == 0 and f4_uso == 0:
            recomendaciones.append("💡 Marchas F4 y F5 no utilizadas. Considerar entrenamiento en uso de marchas altas para mayor eficiencia.")
    
    # Guardar recomendaciones
    reporte.recomendaciones_automaticas = '\n'.join(recomendaciones)
    reporte.save()

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
