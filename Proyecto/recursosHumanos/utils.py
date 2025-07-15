from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from .models import AlertaCronometro, SesionCronometro, Usuario
from django.contrib.auth.models import Group


def enviar_alerta_cronometro(sesion_cronometro):
    """
    Envía alertas por email cuando un técnico tiene un cronómetro activo
    """
    try:
        # Obtener el técnico
        tecnico = sesion_cronometro.tecnico
        
        # Calcular tiempo transcurrido
        tiempo_transcurrido = timezone.now() - sesion_cronometro.fecha_inicio
        horas = int(tiempo_transcurrido.total_seconds() // 3600)
        minutos = int((tiempo_transcurrido.total_seconds() % 3600) // 60)
        
        # Obtener gerentes y administradores
        gerentes = Usuario.objects.filter(
            groups__name__in=['Gerentes', 'Administradores']
        ).distinct()
        
        # Lista de destinatarios
        destinatarios = []
        for gerente in gerentes:
            if gerente.email:
                destinatarios.append(gerente.email)
        
        # Agregar el técnico a los destinatarios si tiene email
        if tecnico.email:
            destinatarios.append(tecnico.email)
        
        if not destinatarios:
            return False
        
        # Preparar contexto para el template
        context = {
            'tecnico': tecnico,
            'servicio': sesion_cronometro.servicio,
            'fecha_inicio': sesion_cronometro.fecha_inicio,
            'tiempo_transcurrido': f"{horas}h {minutos}m",
            'actividad': sesion_cronometro.actividad,
        }
        
        # Renderizar el template del email
        mensaje_html = render_to_string('recursosHumanos/emails/alerta_cronometro.html', context)
        mensaje_texto = render_to_string('recursosHumanos/emails/alerta_cronometro.txt', context)
        
        # Enviar el email
        send_mail(
            subject=f'⚠️ Alerta: Cronómetro activo - {tecnico.get_full_name()}',
            message=mensaje_texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinatarios,
            html_message=mensaje_html,
            fail_silently=False,
        )
        
        # Crear registro de alerta
        AlertaCronometro.objects.create(
            sesion_cronometro=sesion_cronometro,
            tipo_alerta='CRONOMETRO_ACTIVO',
            mensaje=f'Cronómetro activo por {horas}h {minutos}m',
            enviado=True
        )
        
        return True
        
    except Exception as e:
        # Crear registro de alerta fallida
        AlertaCronometro.objects.create(
            sesion_cronometro=sesion_cronometro,
            tipo_alerta='CRONOMETRO_ACTIVO',
            mensaje=f'Error al enviar alerta: {str(e)}',
            enviado=False
        )
        return False


def verificar_cronometros_activos():
    """
    Verifica cronómetros activos y envía alertas si es necesario
    """
    # Obtener cronómetros activos
    cronometros_activos = SesionCronometro.objects.filter(
        fecha_fin__isnull=True
    )
    
    for cronometro in cronometros_activos:
        tiempo_transcurrido = timezone.now() - cronometro.fecha_inicio
        
        # Enviar alerta si han pasado más de 2 horas
        if tiempo_transcurrido > timedelta(hours=2):
            # Verificar si ya se envió una alerta reciente (últimas 2 horas)
            alerta_reciente = AlertaCronometro.objects.filter(
                sesion_cronometro=cronometro,
                tipo_alerta='CRONOMETRO_ACTIVO',
                fecha_creacion__gte=timezone.now() - timedelta(hours=2)
            ).exists()
            
            if not alerta_reciente:
                enviar_alerta_cronometro(cronometro)


def enviar_resumen_diario():
    """
    Envía un resumen diario de cronómetros activos a los gerentes
    """
    try:
        # Obtener cronómetros activos
        cronometros_activos = SesionCronometro.objects.filter(
            fecha_fin__isnull=True
        )
        
        if not cronometros_activos.exists():
            return True
        
        # Obtener gerentes
        gerentes = Usuario.objects.filter(
            groups__name__in=['Gerentes', 'Administradores']
        ).distinct()
        
        destinatarios = []
        for gerente in gerentes:
            if gerente.email:
                destinatarios.append(gerente.email)
        
        if not destinatarios:
            return False
        
        # Preparar contexto
        context = {
            'cronometros_activos': cronometros_activos,
            'fecha': timezone.now().date(),
        }
        
        # Renderizar templates
        mensaje_html = render_to_string('recursosHumanos/emails/resumen_diario.html', context)
        mensaje_texto = render_to_string('recursosHumanos/emails/resumen_diario.txt', context)
        
        # Enviar email
        send_mail(
            subject=f'📊 Resumen Diario - Cronómetros Activos ({timezone.now().date()})',
            message=mensaje_texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinatarios,
            html_message=mensaje_html,
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        return False 