import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def parse_json_responses(json_input):
    """
    Convierte las respuestas del formulario (JSON string o dict) en HTML amigable.
    Acepta tanto cadenas JSON como diccionarios ya parseados.
    """
    if not json_input:
        return mark_safe('<p class="text-muted">No hay respuestas disponibles</p>')
    
    try:
        # Aceptar tanto string como dict
        if isinstance(json_input, str):
            data = json.loads(json_input)
        else:
            data = json_input
        html_parts = []
        
        # Organizar por secciones si existen
        sections = {}
        for key, value in data.items():
            # Intentar determinar la sección basándose en el nombre del campo
            section = get_field_section(key)
            if section not in sections:
                sections[section] = []
            sections[section].append((key, value))
        
        # Generar HTML por secciones
        for section_name, fields in sections.items():
            if section_name != 'General':
                html_parts.append(f'<h6 class="text-primary mt-3 mb-2">{section_name}</h6>')
            
            html_parts.append('<div class="row">')
            for key, value in fields:
                formatted_key = format_field_name(key)
                formatted_value = format_field_value(value)
                
                html_parts.append(f'''
                <div class="col-md-6 mb-2">
                    <strong>{formatted_key}:</strong> {formatted_value}
                </div>
                ''')
            html_parts.append('</div>')
        
        return mark_safe(''.join(html_parts))
        
    except (json.JSONDecodeError, TypeError):
        # Mostrar una vista simple si no se puede parsear adecuadamente
        try:
            pretty = json.dumps(json_input, indent=2, ensure_ascii=False)
        except Exception:
            pretty = str(json_input)
        return mark_safe(f'<div class="alert alert-warning">Error al procesar las respuestas</div><pre class="json-viewer">{pretty}</pre>')

def get_field_section(field_name):
    """
    Determina la sección a la que pertenece un campo basándose en su nombre
    """
    field_name_lower = field_name.lower()
    
    if any(word in field_name_lower for word in ['nombre', 'apellido', 'curp', 'fecha_nacimiento', 'genero', 'estado_civil']):
        return 'Datos Personales'
    elif any(word in field_name_lower for word in ['telefono', 'email', 'direccion', 'calle', 'colonia', 'ciudad', 'estado', 'cp']):
        return 'Datos de Contacto'
    elif any(word in field_name_lower for word in ['escuela', 'bachillerato', 'preparatoria', 'promedio', 'carrera', 'programa']):
        return 'Datos Académicos'
    elif any(word in field_name_lower for word in ['trabajo', 'empleo', 'empresa', 'ocupacion']):
        return 'Datos Laborales'
    else:
        return 'General'

def format_field_name(field_name):
    """
    Formatea el nombre del campo para mostrarlo de manera legible
    """
    # Reemplazar guiones bajos con espacios
    formatted = field_name.replace('_', ' ')
    
    # Capitalizar cada palabra
    formatted = ' '.join(word.capitalize() for word in formatted.split())
    
    # Correcciones específicas
    corrections = {
        'Curp': 'CURP',
        'Cp': 'Código Postal',
        'Email': 'Correo Electrónico',
        'Id': 'ID',
        'Rfc': 'RFC',
        'Nss': 'NSS'
    }
    
    for old, new in corrections.items():
        formatted = formatted.replace(old, new)
    
    return formatted

def format_field_value(value):
    """
    Formatea el valor del campo para mostrarlo de manera apropiada
    """
    if value is None or value == '':
        return '<span class="text-muted">No especificado</span>'
    
    if isinstance(value, bool):
        return '<span class="badge bg-success">Sí</span>' if value else '<span class="badge bg-secondary">No</span>'
    
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return '<span class="text-muted">Ninguno</span>'
        return ', '.join(str(item) for item in value)
    
    if isinstance(value, dict):
        # Para objetos anidados, mostrar como lista de key: value
        items = []
        for k, v in value.items():
            items.append(f'{format_field_name(k)}: {format_field_value(v)}')
        return '<br>'.join(items)
    
    # Para strings largos, truncar si es necesario
    str_value = str(value)
    if len(str_value) > 100:
        return f'{str_value[:97]}...'
    
    return str_value

@register.filter
def json_pretty(value):
    """
    Formatea JSON para mostrarlo de manera legible
    """
    try:
        if isinstance(value, str):
            parsed = json.loads(value)
        else:
            parsed = value
        return json.dumps(parsed, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return str(value)

@register.simple_tag
def get_estado_color(estado):
    """
    Retorna la clase CSS apropiada para el color del estado
    """
    colors = {
        'borrador': 'secondary',
        'enviada': 'primary',
        'en_revision': 'warning',
        'aceptada': 'success',
        'rechazada': 'danger',
        'cancelado': 'dark'
    }
    return colors.get(estado, 'secondary')

@register.simple_tag
def get_estado_icon(estado):
    """
    Retorna el ícono apropiado para el estado
    """
    icons = {
        'borrador': 'fas fa-edit',
        'enviada': 'fas fa-paper-plane',
        'en_revision': 'fas fa-clock',
        'aceptada': 'fas fa-check-circle',
        'rechazada': 'fas fa-times-circle',
        'cancelado': 'fas fa-ban'
    }
    return icons.get(estado, 'fas fa-question-circle')

# ============== Helpers para acceder a valores JSON ==============

@register.filter(name='get_json_value')
def get_json_value(json_input, key):
    """
    Obtiene un valor de un JSON (string o dict) de forma segura.
    Retorna cadena vacía si no existe o si hay error.
    """
    try:
        # Normalizar a dict
        if isinstance(json_input, str):
            try:
                data = json.loads(json_input)
            except json.JSONDecodeError:
                return ''
        else:
            data = json_input
        if isinstance(data, dict):
            return data.get(key, '')
        return ''
    except Exception:
        return ''

@register.filter(name='get_json_value_any')
def get_json_value_any(json_input, keys_csv):
    """
    Retorna el primer valor no vacío entre múltiples llaves separadas por coma.
    """
    try:
        keys = [k.strip() for k in keys_csv.split(',') if k.strip()]
        for k in keys:
            val = get_json_value(json_input, k)
            if isinstance(val, (list, dict)):
                if val:
                    return val
            else:
                if str(val).strip() != '':
                    return val
        return ''
    except Exception:
        return ''