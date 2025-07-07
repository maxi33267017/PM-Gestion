"""
Utilidades de seguridad para la gestión de servicios
"""
from django.contrib import messages
from django.utils import timezone

# Estados del servicio
ESTADOS_SERVICIO = [
    'PROGRAMADO',
    'EN_PROCESO', 
    'ESPERA_REPUESTOS',
    'A_FACTURAR',  # Estado crítico - "Finalizado a Facturar"
    'COMPLETADO'
]

# Reglas de transición de estados
ESTADOS_PERMITIDOS = {
    'PROGRAMADO': ['EN_PROCESO', 'COMPLETADO'],
    'EN_PROCESO': ['ESPERA_REPUESTOS', 'A_FACTURAR', 'COMPLETADO'],
    'ESPERA_REPUESTOS': ['EN_PROCESO', 'A_FACTURAR', 'COMPLETADO'],
    'A_FACTURAR': ['COMPLETADO'],  # Solo puede ir a COMPLETADO
    'COMPLETADO': []  # Estado final
}

def puede_cambiar_estado(user, servicio, nuevo_estado):
    """
    Determina si un usuario puede cambiar el estado de un servicio
    
    Args:
        user: Usuario que intenta hacer el cambio
        servicio: Instancia del servicio
        nuevo_estado: Nuevo estado al que se quiere cambiar
    
    Returns:
        bool: True si puede cambiar, False en caso contrario
    """
    # Gerente siempre puede cambiar estados
    if user.rol == 'GERENTE':
        return True
    
    # Si el servicio está "Finalizado a Facturar", solo puede ir a "Completado"
    if servicio.estado == 'A_FACTURAR':
        return nuevo_estado == 'COMPLETADO'
    
    # Para otros estados, técnicos y administradores pueden cambiar
    # siempre que no esté en estado crítico
    if user.rol in ['TECNICO', 'ADMINISTRATIVO', 'ADMINISTRACION']:
        return True
    
    return False

def es_transicion_valida(estado_actual, nuevo_estado):
    """
    Verifica si la transición de estado es válida según las reglas definidas
    
    Args:
        estado_actual: Estado actual del servicio
        nuevo_estado: Nuevo estado al que se quiere cambiar
    
    Returns:
        bool: True si la transición es válida, False en caso contrario
    """
    if estado_actual not in ESTADOS_PERMITIDOS:
        return False
    
    return nuevo_estado in ESTADOS_PERMITIDOS[estado_actual]

def puede_modificar_servicio(user, servicio):
    """
    Determina si un usuario puede modificar un servicio
    
    Args:
        user: Usuario que intenta modificar
        servicio: Instancia del servicio
    
    Returns:
        bool: True si puede modificar, False en caso contrario
    """
    # Gerente siempre puede modificar
    if user.rol == 'GERENTE':
        return True
    
    # Si el servicio está "Finalizado a Facturar", solo gerente puede modificar
    if servicio.estado == 'A_FACTURAR':
        return False
    
    # Para otros estados, técnicos y administradores pueden modificar
    return user.rol in ['TECNICO', 'ADMINISTRATIVO', 'ADMINISTRACION']

def puede_modificar_informe(user, servicio):
    """
    Determina si un usuario puede modificar el informe de un servicio
    
    Args:
        user: Usuario que intenta modificar
        servicio: Instancia del servicio
    
    Returns:
        bool: True si puede modificar, False en caso contrario
    """
    # Gerente siempre puede modificar
    if user.rol == 'GERENTE':
        return True
    
    # Si el servicio tiene firma del cliente, solo gerente puede modificar
    if servicio.firma_cliente:
        return False
    
    # Para otros casos, técnicos y administradores pueden modificar
    return user.rol in ['TECNICO', 'ADMINISTRATIVO', 'ADMINISTRACION']

def validar_cambio_estado(user, servicio, nuevo_estado):
    """
    Valida y registra un cambio de estado de servicio
    
    Args:
        user: Usuario que intenta hacer el cambio
        servicio: Instancia del servicio
        nuevo_estado: Nuevo estado al que se quiere cambiar
    
    Returns:
        tuple: (bool, str) - (éxito, mensaje)
    """
    # Verificar permisos del usuario
    if not puede_cambiar_estado(user, servicio, nuevo_estado):
        return False, f"No tienes permisos para cambiar el estado a '{nuevo_estado}'"
    
    # Verificar transición válida
    if not es_transicion_valida(servicio.estado, nuevo_estado):
        return False, f"No se puede cambiar de '{servicio.get_estado_display()}' a '{dict(servicio.ESTADO_CHOICES)[nuevo_estado]}'"
    
    # Si el servicio está "Finalizado a Facturar", solo puede ir a "Completado"
    if servicio.estado == 'A_FACTURAR' and nuevo_estado != 'COMPLETADO':
        return False, "Un servicio 'Finalizado a Facturar' solo puede cambiar a 'Completado'"
    
    return True, "Cambio de estado válido"

def registrar_cambio_estado(servicio, usuario, estado_anterior, estado_nuevo, motivo=""):
    """
    Registra un cambio de estado en el log de auditoría
    
    Args:
        servicio: Instancia del servicio
        usuario: Usuario que hizo el cambio
        estado_anterior: Estado anterior
        estado_nuevo: Estado nuevo
        motivo: Motivo del cambio (opcional)
    """
    try:
        from .models import LogCambioServicio
        LogCambioServicio.objects.create(
            servicio=servicio,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            motivo=motivo
        )
    except ImportError:
        # Si el modelo de log no existe, no hacer nada
        pass

def obtener_estados_disponibles(user, servicio):
    """
    Obtiene los estados disponibles para un usuario y servicio específicos
    
    Args:
        user: Usuario que intenta cambiar el estado
        servicio: Instancia del servicio
    
    Returns:
        list: Lista de estados disponibles
    """
    if user.rol == 'GERENTE':
        # Gerente puede cambiar a cualquier estado válido
        return ESTADOS_PERMITIDOS.get(servicio.estado, [])
    
    elif servicio.estado == 'A_FACTURAR':
        # Si está "Finalizado a Facturar", solo puede ir a "Completado"
        return ['COMPLETADO']
    
    else:
        # Para otros casos, técnicos y admin pueden cambiar según las reglas
        return ESTADOS_PERMITIDOS.get(servicio.estado, [])

def registrar_cambio_informe(servicio, usuario, campo_modificado, valor_anterior, valor_nuevo, motivo="", ip_address=None):
    """
    Registra un cambio en el informe de un servicio
    
    Args:
        servicio: Instancia del servicio
        usuario: Usuario que hizo el cambio
        campo_modificado: Nombre del campo que se modificó
        valor_anterior: Valor anterior del campo
        valor_nuevo: Valor nuevo del campo
        motivo: Motivo del cambio (opcional)
        ip_address: Dirección IP del usuario (opcional)
    """
    try:
        from .models import LogCambioInforme
        LogCambioInforme.objects.create(
            servicio=servicio,
            usuario=usuario,
            campo_modificado=campo_modificado,
            valor_anterior=str(valor_anterior) if valor_anterior is not None else "",
            valor_nuevo=str(valor_nuevo) if valor_nuevo is not None else "",
            motivo=motivo,
            ip_address=ip_address
        )
    except ImportError:
        # Si el modelo de log no existe, no hacer nada
        pass

def obtener_cambios_informe(servicio):
    """
    Obtiene todos los cambios registrados para un informe de servicio
    
    Args:
        servicio: Instancia del servicio
    
    Returns:
        QuerySet: Cambios ordenados por fecha descendente
    """
    try:
        from .models import LogCambioInforme
        return LogCambioInforme.objects.filter(servicio=servicio).order_by('-fecha_cambio')
    except ImportError:
        return []

def obtener_usuarios_cambios_informe(servicio):
    """
    Obtiene los usuarios únicos que han hecho cambios en el informe
    
    Args:
        servicio: Instancia del servicio
    
    Returns:
        QuerySet: Usuarios únicos que han hecho cambios
    """
    try:
        from .models import LogCambioInforme
        return LogCambioInforme.objects.filter(servicio=servicio).values_list('usuario__nombre', flat=True).distinct()
    except ImportError:
        return [] 