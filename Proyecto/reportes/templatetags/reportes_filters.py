from django import template

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