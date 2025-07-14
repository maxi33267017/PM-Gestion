from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def add_days(date, days):
    """Añade días a una fecha"""
    try:
        return date + timedelta(days=int(days))
    except (ValueError, TypeError):
        return date

@register.filter
def get_item(dictionary, key):
    """Obtiene un elemento de un diccionario por clave"""
    return dictionary.get(key, []) 