from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import csv
from datetime import datetime, timedelta, date
from decimal import Decimal
import io
import base64

from .models import (
    Usuario, Sucursal, Provincia, Ciudad, ActividadTrabajo, 
    RegistroHorasTecnico, PermisoAusencia
)
from .forms import (
    RegistroHorasTecnicoForm, PermisoAusenciaForm, AprobarPermisoForm,
    EspecializacionAdminForm
)
from .decorators import (
    requiere_especializacion_admin, 
    requiere_administrativo, 
    requiere_especializacion_o_general
)
from gestionDeTaller.models import Servicio
from clientes.models import Cliente, Equipo

@login_required
def cronometro(request):
    """Vista principal del cronómetro para técnicos"""
    if request.user.rol != 'TECNICO':
        messages.error(request, "Solo los técnicos pueden acceder al cronómetro.")
        return redirect('gestionDeTaller:gestion_de_taller')
    
    # Obtener sesión activa del técnico
    sesion_activa = SesionCronometro.get_sesion_activa_tecnico(request.user)
    
    # Obtener actividades disponibles
    actividades = ActividadTrabajo.objects.all().order_by('disponibilidad', 'genera_ingreso', 'nombre')
    
    # Calcular la fecha límite (15 días atrás desde hoy) - solo para servicios COMPLETADO
    fecha_limite = timezone.now().date() - timedelta(days=15)
    
    # Obtener servicios disponibles incluyendo completados recientes
    servicios = Servicio.objects.filter(
        estado__in=['PROGRAMADO', 'ESPERA_REPUESTOS', 'EN_PROCESO', 'A_FACTURAR', 'COMPLETADO']
    ).filter(
        # Aplicar filtro de fecha solo para servicios COMPLETADO
        models.Q(estado__in=['PROGRAMADO', 'ESPERA_REPUESTOS', 'EN_PROCESO', 'A_FACTURAR']) |
        models.Q(estado='COMPLETADO', fecha_servicio__gte=fecha_limite)
    ).order_by('estado', '-fecha_servicio')
    
    # Filtrar por sucursal del técnico si no es superuser
    if not request.user.is_superuser:
        servicios = servicios.filter(preorden__sucursal=request.user.sucursal)
    
    context = {
        'sesion_activa': sesion_activa,
        'actividades': actividades,
        'servicios': servicios,
        'tecnico': request.user,
    }
    
    return render(request, 'recursosHumanos/cronometro.html', context)

def verificar_y_enviar_alertas():
    """Función para verificar cronómetros activos y enviar alertas"""
    from datetime import timedelta
    
    sesiones_activas = SesionCronometro.objects.filter(activa=True)
    
    for sesion in sesiones_activas:
        duracion = sesion.get_duracion()
        horas_activas = duracion.total_seconds() / 3600
        
        # Alerta de cronómetro olvidado (más de 4 horas)
        if horas_activas >= 4:
            alerta = AlertaCronometro.crear_alerta_cronometro_olvidado(sesion)
            if alerta:
                alerta.enviar_email()
        
        # Alerta de cronómetro activo (cada 2 horas)
        elif horas_activas >= 2 and int(horas_activas) % 2 == 0:
            alerta = AlertaCronometro.crear_alerta_cronometro_activo(sesion)
            if alerta:
                alerta.enviar_email()

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def iniciar_cronometro(request):
    """API para iniciar una sesión de cronómetro"""
    if request.user.rol != 'TECNICO':
        return JsonResponse({'success': False, 'message': 'Solo técnicos pueden iniciar cronómetros'})
    
    try:
        data = json.loads(request.body)
        actividad_id = data.get('actividad_id')
        servicio_id = data.get('servicio_id')
        descripcion = data.get('descripcion', '')
        
        # Validar que no haya sesión activa
        sesion_existente = SesionCronometro.get_sesion_activa_tecnico(request.user)
        if sesion_existente:
            return JsonResponse({
                'success': False, 
                'message': 'Ya tienes una sesión activa. Detén la sesión actual antes de iniciar una nueva.'
            })
        
        # Obtener actividad
        actividad = get_object_or_404(ActividadTrabajo, id=actividad_id)
        
        # Obtener servicio si se proporciona
        servicio = None
        if servicio_id:
            servicio = get_object_or_404(Servicio, id=servicio_id)
            
            # Cambiar estado del servicio si es necesario
            if servicio.estado in ['PROGRAMADO', 'ESPERA_REPUESTOS']:
                estado_anterior = servicio.estado
                servicio.estado = 'EN_PROCESO'
                servicio.save()
                
                # Crear log de auditoría
                LogCambioServicio.objects.create(
                    servicio=servicio,
                    usuario=request.user,
                    estado_anterior=estado_anterior,
                    estado_nuevo='EN_PROCESO',
                    motivo='Cambio automático al iniciar cronómetro de técnico'
                )
        
        # Crear nueva sesión
        sesion = SesionCronometro.objects.create(
            tecnico=request.user,
            actividad=actividad,
            servicio=servicio,
            descripcion=descripcion
        )
        
        # Enviar alerta inicial al técnico y managers
        alerta = AlertaCronometro.crear_alerta_cronometro_activo(sesion)
        if alerta:
            alerta.enviar_email()
        
        return JsonResponse({
            'success': True,
            'message': 'Cronómetro iniciado correctamente',
            'sesion_id': sesion.id,
            'hora_inicio': sesion.hora_inicio.isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al iniciar cronómetro: {str(e)}'
        })

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def detener_cronometro(request):
    """API para detener una sesión de cronómetro"""
    if request.user.rol != 'TECNICO':
        return JsonResponse({'success': False, 'message': 'Solo técnicos pueden detener cronómetros'})
    
    try:
        sesion = SesionCronometro.get_sesion_activa_tecnico(request.user)
        if not sesion:
            return JsonResponse({
                'success': False,
                'message': 'No tienes una sesión activa'
            })
        
        # Finalizar sesión
        success, message = sesion.finalizar_sesion()
        
        return JsonResponse({
            'success': success,
            'message': message,
            'duracion_horas': sesion.get_duracion_horas() if success else 0
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al detener cronómetro: {str(e)}'
        })

@login_required
@require_http_methods(["GET"])
def estado_cronometro(request):
    """API para obtener el estado actual del cronómetro"""
    if request.user.rol != 'TECNICO':
        return JsonResponse({'success': False, 'message': 'Solo técnicos pueden consultar cronómetros'})
    
    try:
        sesion = SesionCronometro.get_sesion_activa_tecnico(request.user)
        
        if not sesion:
            return JsonResponse({
                'success': True,
                'activa': False,
                'message': 'No hay sesión activa'
            })
        
        duracion = sesion.get_duracion()
        duracion_segundos = duracion.total_seconds()
        
        return JsonResponse({
            'success': True,
            'activa': True,
            'sesion_id': sesion.id,
            'actividad': sesion.actividad.nombre,
            'servicio': sesion.servicio.id if sesion.servicio else None,
            'servicio_info': str(sesion.servicio) if sesion.servicio else None,
            'hora_inicio': sesion.hora_inicio.isoformat(),
            'duracion_segundos': duracion_segundos,
            'duracion_horas': duracion_segundos / 3600
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al obtener estado: {str(e)}'
        })

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def finalizar_sesiones_automaticas(request):
    """API para finalizar sesiones automáticamente (llamada por tarea programada)"""
    try:
        # Verificar que sea después de las 19:00
        ahora = timezone.now()
        hora_limite = time(19, 0)
        
        if ahora.time() >= hora_limite:
            # Enviar alertas antes de finalizar
            verificar_y_enviar_alertas()
            
            # Finalizar sesiones
            SesionCronometro.finalizar_sesiones_automaticas()
            
            return JsonResponse({
                'success': True,
                'message': 'Sesiones finalizadas automáticamente'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'No es hora de finalizar sesiones automáticamente'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al finalizar sesiones: {str(e)}'
        })

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def verificar_alertas_cronometro(request):
    """API para verificar y enviar alertas de cronómetros activos"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        return JsonResponse({'success': False, 'message': 'No tienes permisos para esta acción'})
    
    try:
        verificar_y_enviar_alertas()
        
        return JsonResponse({
            'success': True,
            'message': 'Verificación de alertas completada'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al verificar alertas: {str(e)}'
        })

@login_required
def dashboard_alertas_cronometro(request):
    """Dashboard para ver alertas de cronómetros activos"""
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect('gestionDeTaller:gestion_de_taller')
    
    # Obtener sesiones activas
    if request.user.is_superuser:
        sesiones_activas = SesionCronometro.objects.filter(activa=True)
    else:
        sesiones_activas = SesionCronometro.objects.filter(
            activa=True,
            tecnico__sucursal=request.user.sucursal
        )
    
    # Calcular duración de cada sesión
    for sesion in sesiones_activas:
        sesion.duracion_actual = sesion.get_duracion()
        sesion.horas_activas = sesion.duracion_actual.total_seconds() / 3600
    
    # Obtener alertas recientes
    alertas_recientes = AlertaCronometro.objects.filter(
        fecha_envio__gte=timezone.now() - timedelta(days=7)
    ).order_by('-fecha_envio')[:20]
    
    context = {
        'sesiones_activas': sesiones_activas,
        'alertas_recientes': alertas_recientes,
        'total_sesiones_activas': sesiones_activas.count(),
    }
    
    return render(request, 'recursosHumanos/dashboard_alertas_cronometro.html', context)

# =============================================================================
# VISTAS PARA SISTEMA DE PERMISOS Y AUSENCIAS
# =============================================================================

@login_required
def lista_permisos(request):
    """
    Vista para listar permisos del usuario logueado
    """
    permisos = PermisoAusencia.objects.filter(usuario=request.user).order_by('-fecha_solicitud')
    
    context = {
        'permisos': permisos,
        'permisos_pendientes': permisos.filter(estado='PENDIENTE'),
        'permisos_aprobados': permisos.filter(estado='APROBADO'),
        'permisos_rechazados': permisos.filter(estado='RECHAZADO'),
        'permisos_activos': permisos.filter(estado='APROBADO', fecha_inicio__lte=timezone.now().date(), fecha_fin__gte=timezone.now().date()),
    }
    
    return render(request, 'recursosHumanos/permisos/lista_permisos.html', context)

@login_required
def solicitar_permiso(request):
    """
    Vista para solicitar un nuevo permiso
    """
    if request.method == 'POST':
        form = PermisoAusenciaForm(request.POST, request.FILES)
        if form.is_valid():
            permiso = form.save(commit=False)
            permiso.usuario = request.user
            permiso.save()
            
            messages.success(request, 'Permiso solicitado exitosamente. Será revisado por tu gerente.')
            return redirect('recursosHumanos:lista_permisos')
    else:
        form = PermisoAusenciaForm()
    
    context = {
        'form': form,
        'tipos_permiso': PermisoAusencia.TIPO_PERMISO_CHOICES,
    }
    
    return render(request, 'recursosHumanos/permisos/solicitar_permiso.html', context)

@login_required
def detalle_permiso(request, permiso_id):
    """
    Vista para ver el detalle de un permiso
    """
    permiso = get_object_or_404(PermisoAusencia, id=permiso_id)
    
    # Verificar que el usuario pueda ver este permiso
    if not request.user.is_superuser and request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        if permiso.usuario != request.user:
            messages.error(request, 'No tienes permiso para ver este permiso.')
            return redirect('recursosHumanos:lista_permisos')
    
    context = {
        'permiso': permiso,
    }
    
    return render(request, 'recursosHumanos/permisos/detalle_permiso.html', context)

@login_required
def editar_permiso(request, permiso_id):
    """
    Vista para editar un permiso (solo si está pendiente)
    """
    permiso = get_object_or_404(PermisoAusencia, id=permiso_id)
    
    # Verificar que el usuario pueda editar este permiso
    if permiso.usuario != request.user:
        messages.error(request, 'No puedes editar permisos de otros usuarios.')
        return redirect('recursosHumanos:lista_permisos')
    
    if permiso.estado != 'PENDIENTE':
        messages.error(request, 'Solo se pueden editar permisos pendientes.')
        return redirect('recursosHumanos:detalle_permiso', permiso_id=permiso.id)
    
    if request.method == 'POST':
        form = PermisoAusenciaForm(request.POST, request.FILES, instance=permiso)
        if form.is_valid():
            form.save()
            messages.success(request, 'Permiso actualizado exitosamente.')
            return redirect('recursosHumanos:detalle_permiso', permiso_id=permiso.id)
    else:
        form = PermisoAusenciaForm(instance=permiso)
    
    context = {
        'form': form,
        'permiso': permiso,
    }
    
    return render(request, 'recursosHumanos/permisos/editar_permiso.html', context)

@login_required
def cancelar_permiso(request, permiso_id):
    """
    Vista para cancelar un permiso
    """
    permiso = get_object_or_404(PermisoAusencia, id=permiso_id)
    
    # Verificar que el usuario pueda cancelar este permiso
    if permiso.usuario != request.user and request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para cancelar este permiso.')
        return redirect('recursosHumanos:lista_permisos')
    
    if permiso.estado not in ['PENDIENTE', 'APROBADO']:
        messages.error(request, 'Solo se pueden cancelar permisos pendientes o aprobados.')
        return redirect('recursosHumanos:detalle_permiso', permiso_id=permiso.id)
    
    if request.method == 'POST':
        observaciones = request.POST.get('observaciones', '')
        permiso.cancelar(request.user, observaciones)
        messages.success(request, 'Permiso cancelado exitosamente.')
        return redirect('recursosHumanos:lista_permisos')
    
    context = {
        'permiso': permiso,
    }
    
    return render(request, 'recursosHumanos/permisos/cancelar_permiso.html', context)

# =============================================================================
# VISTAS PARA GERENTES - APROBACIÓN DE PERMISOS
# =============================================================================

@login_required
def lista_permisos_gerente(request):
    """
    Vista para que los gerentes vean todos los permisos pendientes
    """
    # Verificar que el usuario sea gerente
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('recursosHumanos:lista_permisos')
    
    # Filtrar permisos según el rol
    if request.user.rol == 'GERENTE':
        # Gerentes ven permisos de su sucursal
        permisos = PermisoAusencia.objects.filter(
            usuario__sucursal=request.user.sucursal
        ).select_related('usuario', 'aprobado_por').order_by('-fecha_solicitud')
    else:
        # Administrativos ven todos los permisos
        permisos = PermisoAusencia.objects.all().select_related('usuario', 'aprobado_por').order_by('-fecha_solicitud')
    
    context = {
        'permisos': permisos,
        'permisos_pendientes': permisos.filter(estado='PENDIENTE'),
        'permisos_aprobados': permisos.filter(estado='APROBADO'),
        'permisos_rechazados': permisos.filter(estado='RECHAZADO'),
        'permisos_activos': permisos.filter(estado='APROBADO', fecha_inicio__lte=timezone.now().date(), fecha_fin__gte=timezone.now().date()),
    }
    
    return render(request, 'recursosHumanos/permisos/lista_permisos_gerente.html', context)

@login_required
def aprobar_permiso(request, permiso_id):
    """
    Vista para aprobar un permiso
    """
    # Verificar que el usuario sea gerente
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para aprobar permisos.')
        return redirect('recursosHumanos:lista_permisos')
    
    permiso = get_object_or_404(PermisoAusencia, id=permiso_id)
    
    # Verificar que el gerente pueda aprobar este permiso
    if request.user.rol == 'GERENTE' and permiso.usuario.sucursal != request.user.sucursal:
        messages.error(request, 'Solo puedes aprobar permisos de tu sucursal.')
        return redirect('recursosHumanos:lista_permisos_gerente')
    
    if not permiso.puede_ser_aprobado:
        messages.error(request, 'Este permiso no puede ser aprobado.')
        return redirect('recursosHumanos:detalle_permiso', permiso_id=permiso.id)
    
    if request.method == 'POST':
        form = AprobarPermisoForm(request.POST, instance=permiso)
        if form.is_valid():
            observaciones = form.cleaned_data['observaciones_aprobacion']
            permiso.aprobar(request.user, observaciones)
            messages.success(request, 'Permiso aprobado exitosamente.')
            return redirect('recursosHumanos:lista_permisos_gerente')
    else:
        form = AprobarPermisoForm(instance=permiso)
    
    context = {
        'form': form,
        'permiso': permiso,
    }
    
    return render(request, 'recursosHumanos/permisos/aprobar_permiso.html', context)

@login_required
def rechazar_permiso(request, permiso_id):
    """
    Vista para rechazar un permiso
    """
    # Verificar que el usuario sea gerente
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para rechazar permisos.')
        return redirect('recursosHumanos:lista_permisos')
    
    permiso = get_object_or_404(PermisoAusencia, id=permiso_id)
    
    # Verificar que el gerente pueda rechazar este permiso
    if request.user.rol == 'GERENTE' and permiso.usuario.sucursal != request.user.sucursal:
        messages.error(request, 'Solo puedes rechazar permisos de tu sucursal.')
        return redirect('recursosHumanos:lista_permisos_gerente')
    
    if not permiso.puede_ser_rechazado:
        messages.error(request, 'Este permiso no puede ser rechazado.')
        return redirect('recursosHumanos:detalle_permiso', permiso_id=permiso.id)
    
    if request.method == 'POST':
        form = AprobarPermisoForm(request.POST, instance=permiso)
        if form.is_valid():
            observaciones = form.cleaned_data['observaciones_aprobacion']
            permiso.rechazar(request.user, observaciones)
            messages.success(request, 'Permiso rechazado exitosamente.')
            return redirect('recursosHumanos:lista_permisos_gerente')
    else:
        form = AprobarPermisoForm(instance=permiso)
    
    context = {
        'form': form,
        'permiso': permiso,
    }
    
    return render(request, 'recursosHumanos/permisos/rechazar_permiso.html', context)

@login_required
def dashboard_permisos(request):
    """
    Dashboard con estadísticas de permisos
    """
    # Verificar que el usuario sea gerente
    if request.user.rol not in ['GERENTE', 'ADMINISTRATIVO']:
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('recursosHumanos:lista_permisos')
    
    # Filtrar permisos según el rol
    if request.user.rol == 'GERENTE':
        # Para gerentes: ver permisos de su sucursal y sucursales adicionales
        sucursales_gerente = [request.user.sucursal]
        if request.user.sucursales_adicionales.exists():
            sucursales_gerente.extend(request.user.sucursales_adicionales.all())
        permisos = PermisoAusencia.objects.filter(usuario__sucursal__in=sucursales_gerente)
    else:
        # Para administrativos: ver todos los permisos
        permisos = PermisoAusencia.objects.all()
    
    # Estadísticas
    total_permisos = permisos.count()
    permisos_pendientes = permisos.filter(estado='PENDIENTE').count()
    permisos_aprobados = permisos.filter(estado='APROBADO').count()
    permisos_rechazados = permisos.filter(estado='RECHAZADO').count()
    permisos_activos = permisos.filter(
        estado='APROBADO',
        fecha_inicio__lte=timezone.now().date(),
        fecha_fin__gte=timezone.now().date()
    ).count()
    
    # Permisos por tipo - incluir todos los tipos aunque tengan 0
    permisos_por_tipo = {}
    for tipo, nombre in PermisoAusencia.TIPO_PERMISO_CHOICES:
        count = permisos.filter(tipo_permiso=tipo).count()
        permisos_por_tipo[nombre] = count
    
    # Permisos recientes
    permisos_recientes = permisos.order_by('-fecha_solicitud')[:10]
    
    context = {
        'total_permisos': total_permisos,
        'permisos_pendientes': permisos_pendientes,
        'permisos_aprobados': permisos_aprobados,
        'permisos_rechazados': permisos_rechazados,
        'permisos_activos': permisos_activos,
        'permisos_por_tipo': permisos_por_tipo,
        'permisos_recientes': permisos_recientes,
        'debug_info': {
            'user_rol': request.user.rol,
            'user_sucursal': request.user.sucursal.nombre if request.user.sucursal else 'Sin sucursal',
            'total_permisos_found': total_permisos,
        }
    }
    
    return render(request, 'recursosHumanos/permisos/dashboard_permisos.html', context)

# ============================================================================
# VISTAS DE EJEMPLO PARA EL SISTEMA DE ESPECIALIZACIONES ADMINISTRATIVAS
# ============================================================================

@login_required
@requiere_administrativo
def dashboard_administrativo_general(request):
    """
    Dashboard general para usuarios administrativos
    """
    context = {
        'titulo': 'Dashboard Administrativo General',
        'descripcion': 'Vista general para usuarios administrativos',
        'modulos_disponibles': request.user.get_modulos_disponibles(),
        'especializacion': request.user.get_especializacion_display(),
    }
    return render(request, 'recursosHumanos/dashboard_administrativo_general.html', context)

@login_required
@requiere_especializacion_admin('rrhh')
def dashboard_administrativo_rrhh(request):
    """
    Dashboard específico para administrativos de RRHH
    """
    # Obtener estadísticas específicas de RRHH
    total_usuarios = Usuario.objects.count()
    usuarios_activos = Usuario.objects.filter(is_active=True).count()
    permisos_pendientes = PermisoAusencia.objects.filter(estado='PENDIENTE').count()
    
    context = {
        'titulo': 'Dashboard RRHH',
        'descripcion': 'Gestión de Recursos Humanos',
        'total_usuarios': total_usuarios,
        'usuarios_activos': usuarios_activos,
        'permisos_pendientes': permisos_pendientes,
        'especializacion': request.user.get_especializacion_display(),
    }
    return render(request, 'recursosHumanos/dashboard_administrativo_rrhh.html', context)

@login_required
@requiere_especializacion_admin('contable')
def dashboard_administrativo_contable(request):
    """
    Dashboard específico para administrativos contables
    """
    context = {
        'titulo': 'Dashboard Contable',
        'descripcion': 'Gestión Contable y Financiera',
        'especializacion': request.user.get_especializacion_display(),
    }
    return render(request, 'recursosHumanos/dashboard_administrativo_contable.html', context)

@login_required
@requiere_especializacion_admin('cajero')
def dashboard_administrativo_cajero(request):
    """
    Dashboard específico para cajeros
    """
    context = {
        'titulo': 'Dashboard Cajero',
        'descripcion': 'Gestión de Caja y Pagos',
        'especializacion': request.user.get_especializacion_display(),
    }
    return render(request, 'recursosHumanos/dashboard_administrativo_cajero.html', context)

@login_required
@requiere_especializacion_admin('servicios')
def dashboard_administrativo_servicios(request):
    """
    Dashboard específico para administrativos de servicios
    """
    # Obtener estadísticas de servicios
    servicios_totales = Servicio.objects.count()
    servicios_pendientes = Servicio.objects.filter(estado='PROGRAMADO').count()
    servicios_en_proceso = Servicio.objects.filter(estado='EN_PROCESO').count()
    
    context = {
        'titulo': 'Dashboard Servicios',
        'descripcion': 'Gestión de Servicios Técnicos',
        'servicios_totales': servicios_totales,
        'servicios_pendientes': servicios_pendientes,
        'servicios_en_proceso': servicios_en_proceso,
        'especializacion': request.user.get_especializacion_display(),
    }
    return render(request, 'recursosHumanos/dashboard_administrativo_servicios.html', context)

@login_required
@requiere_especializacion_admin('repuestos')
def dashboard_administrativo_repuestos(request):
    """
    Dashboard específico para administrativos de repuestos
    """
    context = {
        'titulo': 'Dashboard Repuestos',
        'descripcion': 'Gestión de Inventario de Repuestos',
        'especializacion': request.user.get_especializacion_display(),
    }
    return render(request, 'recursosHumanos/dashboard_administrativo_repuestos.html', context)

@login_required
@requiere_especializacion_o_general('rrhh')
def gestion_permisos_avanzada(request):
    """
    Vista avanzada de gestión de permisos (solo RRHH o administrativos generales)
    """
    permisos = PermisoAusencia.objects.all().order_by('-fecha_solicitud')
    
    context = {
        'titulo': 'Gestión Avanzada de Permisos',
        'descripcion': 'Gestión completa de permisos y ausencias',
        'permisos': permisos,
        'especializacion': request.user.get_especializacion_display(),
    }
    return render(request, 'recursosHumanos/gestion_permisos_avanzada.html', context)

@login_required
def perfil_especializacion(request):
    """
    Vista para que los usuarios vean y gestionen su especialización
    """
    if request.method == 'POST':
        # Aquí se podría implementar la lógica para cambiar especialización
        # Por ahora solo mostramos información
        pass
    
    context = {
        'titulo': 'Mi Perfil de Especialización',
        'descripcion': 'Información sobre tu especialización administrativa',
        'especializacion': request.user.get_especializacion_display(),
        'tiene_especializacion': request.user.tiene_especializacion(),
        'modulos_disponibles': request.user.get_modulos_disponibles(),
        'es_administrativo': request.user.es_administrativo(),
    }
    return render(request, 'recursosHumanos/perfil_especializacion.html', context)

@login_required
def gestionar_especializaciones(request):
    """
    Vista para que los gerentes gestionen las especializaciones de usuarios administrativos
    """
    # Verificar que el usuario sea gerente
    if request.user.rol != 'GERENTE':
        messages.error(request, 'Solo los gerentes pueden gestionar especializaciones.')
        return redirect('home')
    
    # Obtener usuarios administrativos
    usuarios_admin = Usuario.objects.filter(rol='ADMINISTRATIVO').order_by('apellido', 'nombre')
    
    if request.method == 'POST':
        # Procesar formularios de especialización
        for usuario in usuarios_admin:
            form_key = f'form_{usuario.id}'
            if form_key in request.POST:
                form = EspecializacionAdminForm(request.POST, instance=usuario, prefix=f'user_{usuario.id}')
                if form.is_valid():
                    form.save()
                    messages.success(
                        request, 
                        f'Especialización actualizada para {usuario.get_nombre_completo()}'
                    )
                else:
                    messages.error(
                        request, 
                        f'Error al actualizar especialización para {usuario.get_nombre_completo()}: {form.errors}'
                    )
    
    # Crear formularios para cada usuario administrativo
    formularios = {}
    for usuario in usuarios_admin:
        formularios[usuario.id] = EspecializacionAdminForm(
            instance=usuario, 
            prefix=f'user_{usuario.id}'
        )
    
    context = {
        'titulo': 'Gestión de Especializaciones Administrativas',
        'descripcion': 'Configurar especializaciones de usuarios administrativos',
        'usuarios_admin': usuarios_admin,
        'formularios': formularios,
        'especializaciones': Usuario.ESPECIALIZACIONES_ADMIN,
    }
    
    return render(request, 'recursosHumanos/gestionar_especializaciones.html', context)

@login_required
def configurar_especializacion_usuario(request, usuario_id):
    """
    Vista para configurar la especialización de un usuario específico
    """
    # Verificar que el usuario sea gerente
    if request.user.rol != 'GERENTE':
        messages.error(request, 'Solo los gerentes pueden configurar especializaciones.')
        return redirect('home')
    
    usuario = get_object_or_404(Usuario, id=usuario_id)
    
    if request.method == 'POST':
        form = EspecializacionAdminForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(
                request, 
                f'Especialización actualizada para {usuario.get_nombre_completo()}'
            )
            return redirect('recursosHumanos:gestionar_especializaciones')
    else:
        form = EspecializacionAdminForm(instance=usuario)
    
    context = {
        'titulo': f'Configurar Especialización - {usuario.get_nombre_completo()}',
        'descripcion': 'Configurar especialización administrativa',
        'usuario': usuario,
        'form': form,
        'especializaciones': Usuario.ESPECIALIZACIONES_ADMIN,
    }
    
    return render(request, 'recursosHumanos/configurar_especializacion.html', context)
