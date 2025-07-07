from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Obtener un elemento de un diccionario por clave"""
    return dictionary.get(key, {})

@register.filter
def etapa_color(etapa):
    """Retornar el color CSS para cada etapa del embudo"""
    colores = {
        'CONTACTO_INICIAL': 'info',
        'CALIFICACION': 'warning',
        'PROPUESTA': 'primary',
        'NEGOCIACION': 'secondary',
        'CIERRE': 'success',
        'PERDIDO': 'danger',
    }
    return colores.get(etapa, 'secondary')

@register.filter
def resultado_color(resultado):
    """Retornar el color CSS para cada resultado de contacto"""
    colores = {
        'EXITOSO': 'success',
        'PENDIENTE': 'warning',
        'NO_CONTESTA': 'danger',
        'REPROGRAMADO': 'info',
        'CANCELADO': 'secondary',
    }
    return colores.get(resultado, 'secondary') 