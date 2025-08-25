from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplica dos valores"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def etapa_color(etapa):
    """Retorna el color CSS para cada etapa"""
    colors = {
        'PENDIENTE': 'secondary',
        'CONTACTADO': 'primary',
        'CON_RESPUESTA': 'info',
        'PRESUPUESTADO': 'warning',
        'VENTA_PERDIDA': 'danger',
        'VENTA_EXITOSA': 'success',
    }
    return colors.get(etapa, 'light')

@register.filter
def count_by_estado(queryset, estado):
    """Cuenta oportunidades por estado específico"""
    try:
        return queryset.filter(estado_contacto=estado).count()
    except:
        return 0

@register.filter
def count_ultimo_mes(queryset):
    """Cuenta oportunidades creadas en el último mes"""
    try:
        fecha_limite = timezone.now() - timedelta(days=30)
        return queryset.filter(fecha_creacion__gte=fecha_limite).count()
    except:
        return 0

@register.filter
def count_exitosas(queryset):
    """Cuenta oportunidades exitosas (VENTA_EXITOSA)"""
    try:
        return queryset.filter(estado_contacto='VENTA_EXITOSA').count()
    except:
        return 0

@register.filter
def count_pendientes(queryset):
    """Cuenta oportunidades pendientes (PENDIENTE)"""
    try:
        return queryset.filter(estado_contacto='PENDIENTE').count()
    except:
        return 0

@register.filter
def objetivo_total_embudo(embudo):
    """Calcula el objetivo total del embudo (objetivo_paquetes × valor_promedio_paquete)"""
    try:
        if embudo.objetivo_paquetes and embudo.valor_promedio_paquete:
            return float(embudo.objetivo_paquetes) * float(embudo.valor_promedio_paquete)
        else:
            return None
    except (ValueError, TypeError):
        return None 