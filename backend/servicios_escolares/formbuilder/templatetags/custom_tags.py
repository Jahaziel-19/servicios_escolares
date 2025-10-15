from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def display_value(value):
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return value
