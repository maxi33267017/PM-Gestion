from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Obtener un elemento de un diccionario por clave"""
    return dictionary.get(key, 0)

@register.filter
def multiply(value, arg):
    """Multiplicar un valor por un argumento"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Dividir un valor por un argumento"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0 

@register.filter
def hours_format(timedelta_obj):
    """Convert timedelta to hours format"""
    if timedelta_obj is None:
        return "0.0"
    
    if isinstance(timedelta_obj, timedelta):
        total_seconds = timedelta_obj.total_seconds()
        hours = total_seconds / 3600
        return f"{hours:.1f}"
    else:
        return str(timedelta_obj) 