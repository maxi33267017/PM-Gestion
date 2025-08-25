from django import template

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