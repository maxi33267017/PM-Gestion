from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Filtro para acceder a valores de diccionario en templates"""
    if not isinstance(dictionary, dict):
        return 0
    return dictionary.get(key, 0) 