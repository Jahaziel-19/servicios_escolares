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


@register.filter(name='get_item')
def get_item(d, key):
    """
    Accede de forma segura a un elemento de diccionario en plantillas.
    Uso: {{ diccionario|get_item:clave }}. Si no existe, devuelve 0 o cadena vacía.
    """
    try:
        if isinstance(d, dict):
            return d.get(key, 0)
        return ''
    except Exception:
        return ''


@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Verifica si el usuario pertenece al grupo especificado.
    Uso: {{ request.user|has_group:"ServiciosEscolares" }}
    """
    try:
        return getattr(user, 'groups', None) is not None and user.groups.filter(name=group_name).exists()
    except Exception:
        return False