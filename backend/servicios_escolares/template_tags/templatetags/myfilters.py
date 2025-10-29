from django import template

register = template.Library()

@register.filter
def attr(obj, attr_name):
    return getattr(obj, attr_name)

# Acceder a un diccionario por clave desde plantillas
# Uso: {{ mi_dict|dict_get:clave }}
@register.filter(name="dict_get")
def dict_get(d, key):
    try:
        if isinstance(d, dict):
            return d.get(key)
        # Soporte para objetos con acceso tipo dict
        return getattr(d, key, None)
    except Exception:
        return None
