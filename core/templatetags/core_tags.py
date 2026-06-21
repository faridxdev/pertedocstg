from django import template

register = template.Library()

@register.filter(name='split')
def split(value, key):
    """
    Divise une chaîne de caractères par le séparateur donné.
    Usage: {{ value|split:"," }}
    """
    return value.split(key)