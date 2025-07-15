from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime, time, timedelta
from .models import SesionCronometro, ActividadTrabajo, Usuario, AlertaCronometro
from gestionDeTaller.models import Servicio, LogCambioServicio

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
    
    # Obtener servicios disponibles (PROGRAMADO, EN_ESPERA_REPUESTOS, EN_PROCESO)
    servicios = Servicio.objects.filter(
        estado__in=['PROGRAMADO', 'ESPERA_REPUESTOS', 'EN_PROCESO']
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
