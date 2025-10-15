from django import template

register = template.Library()


@register.filter(name='length_is')
def length_is(value, arg):
    """
    Compatibilidad para el filtro removido en Django 5.1+.
    Devuelve True si la longitud de 'value' es igual a 'arg'.
    """
    try:
        return len(value) == int(arg)
    except Exception:
        return False