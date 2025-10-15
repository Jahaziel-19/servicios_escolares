from docxtpl import DocxTemplate
from datetime import datetime, date
from io import BytesIO
from django.http import HttpResponse
from django.conf import settings
import os
from .models_inscripcion import Inscripcion, Reinscripcion
from .models import Alumno, Carrera, PeriodoEscolar


def generar_formato_inscripcion(inscripcion_id, plantilla_path=None):
    """
    Genera el formato de inscripción en formato DOCX usando una plantilla
    """
    try:
        inscripcion = Inscripcion.objects.get(id=inscripcion_id)
        
        # Usar plantilla por defecto si no se especifica una
        if not plantilla_path:
            plantilla_path = os.path.join(
                settings.MEDIA_ROOT, 
                'plantillas', 
                'formato_inscripcion.docx'
            )
        
        # Verificar que existe la plantilla
        if not os.path.exists(plantilla_path):
            raise FileNotFoundError(f"No se encontró la plantilla en: {plantilla_path}")
        
        # Crear contexto con datos de la inscripción
        contexto = crear_contexto_inscripcion(inscripcion)
        
        # Generar documento
        doc = DocxTemplate(plantilla_path)
        doc.render(contexto)
        
        # Crear buffer para la respuesta
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        # Crear nombre del archivo
        nombre_archivo = f"inscripcion_{inscripcion.folio}_{inscripcion.nombre.replace(' ', '_')}.docx"
        
        # Crear respuesta HTTP
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
        
        return response
        
    except Inscripcion.DoesNotExist:
        raise ValueError(f"No se encontró la inscripción con ID: {inscripcion_id}")
    except Exception as e:
        raise Exception(f"Error al generar formato de inscripción: {str(e)}")


def generar_formato_reinscripcion(reinscripcion_id, plantilla_path=None):
    """
    Genera el formato de reinscripción en formato DOCX usando una plantilla
    """
    try:
        reinscripcion = Reinscripcion.objects.get(id=reinscripcion_id)
        
        # Usar plantilla por defecto si no se especifica una
        if not plantilla_path:
            plantilla_path = os.path.join(
                settings.MEDIA_ROOT, 
                'plantillas', 
                'formato_reinscripcion.docx'
            )
        
        # Verificar que existe la plantilla
        if not os.path.exists(plantilla_path):
            raise FileNotFoundError(f"No se encontró la plantilla en: {plantilla_path}")
        
        # Crear contexto con datos de la reinscripción
        contexto = crear_contexto_reinscripcion(reinscripcion)
        
        # Generar documento
        doc = DocxTemplate(plantilla_path)
        doc.render(contexto)
        
        # Crear buffer para la respuesta
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        # Crear nombre del archivo
        nombre_archivo = f"reinscripcion_{reinscripcion.folio}_{reinscripcion.alumno.matricula}.docx"
        
        # Crear respuesta HTTP
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
        
        return response
        
    except Reinscripcion.DoesNotExist:
        raise ValueError(f"No se encontró la reinscripción con ID: {reinscripcion_id}")
    except Exception as e:
        raise Exception(f"Error al generar formato de reinscripción: {str(e)}")


def crear_contexto_inscripcion(inscripcion):
    """
    Crea el contexto de variables para el formato de inscripción
    """
    contexto = {
        # Información básica
        'folio': inscripcion.folio,
        'fecha_inscripcion': inscripcion.fecha_inscripcion.strftime('%d/%m/%Y'),
        'fecha_emision': datetime.now().strftime('%d/%m/%Y'),
        
        # Datos personales
        'nombre_completo': f"{inscripcion.nombre} {inscripcion.apellido_paterno} {inscripcion.apellido_materno}".strip(),
        'nombre': inscripcion.nombre,
        'apellido_paterno': inscripcion.apellido_paterno,
        'apellido_materno': inscripcion.apellido_materno,
        'curp': inscripcion.curp,
        'fecha_nacimiento': inscripcion.fecha_nacimiento.strftime('%d/%m/%Y') if inscripcion.fecha_nacimiento else '',
        'lugar_nacimiento': inscripcion.lugar_nacimiento or '',
        'genero': inscripcion.get_genero_display(),
        'estado_civil': inscripcion.get_estado_civil_display(),
        
        # Datos académicos
        'carrera': inscripcion.carrera.nombre if inscripcion.carrera else '',
        'carrera_clave': inscripcion.carrera.clave if inscripcion.carrera else '',
        'periodo_escolar': str(inscripcion.periodo_escolar) if inscripcion.periodo_escolar else '',
        'semestre': inscripcion.semestre,
        'modalidad': inscripcion.get_modalidad_display(),
        'turno': inscripcion.get_turno_display(),
        
        # Datos de contacto
        'telefono': inscripcion.telefono or '',
        'email': inscripcion.email or '',
        'telefono_emergencia': inscripcion.telefono_emergencia or '',
        'contacto_emergencia': inscripcion.contacto_emergencia or '',
        
        # Dirección
        'calle': inscripcion.calle or '',
        'numero': inscripcion.numero or '',
        'colonia': inscripcion.colonia or '',
        'municipio': inscripcion.municipio or '',
        'estado': inscripcion.estado or '',
        'codigo_postal': inscripcion.codigo_postal or '',
        
        # Datos académicos previos
        'escuela_procedencia': inscripcion.escuela_procedencia or '',
        'promedio_bachillerato': str(inscripcion.promedio_bachillerato) if inscripcion.promedio_bachillerato else '',
        'año_egreso': str(inscripcion.año_egreso) if inscripcion.año_egreso else '',
        
        # Documentos
        'acta_nacimiento': 'Sí' if inscripcion.acta_nacimiento else 'No',
        'certificado_bachillerato': 'Sí' if inscripcion.certificado_bachillerato else 'No',
        'curp_documento': 'Sí' if inscripcion.curp_documento else 'No',
        'fotografias': 'Sí' if inscripcion.fotografias else 'No',
        'certificado_medico': 'Sí' if inscripcion.certificado_medico else 'No',
        
        # Estado del proceso
        'estatus': inscripcion.get_estatus_display(),
        'observaciones': inscripcion.observaciones or '',
    }
    
    return contexto


def crear_contexto_reinscripcion(reinscripcion):
    """
    Crea el contexto de variables para el formato de reinscripción
    """
    alumno = reinscripcion.alumno
    
    contexto = {
        # Información básica
        'folio': reinscripcion.folio,
        'fecha_reinscripcion': reinscripcion.fecha_reinscripcion.strftime('%d/%m/%Y'),
        'fecha_emision': datetime.now().strftime('%d/%m/%Y'),
        
        # Datos del alumno
        'matricula': alumno.matricula,
        'nombre_completo': f"{alumno.nombre} {alumno.apellido_paterno} {alumno.apellido_materno}".strip(),
        'nombre': alumno.nombre,
        'apellido_paterno': alumno.apellido_paterno,
        'apellido_materno': alumno.apellido_materno,
        'curp': alumno.curp,
        
        # Datos académicos actuales
        'carrera_actual': alumno.carrera.nombre if alumno.carrera else '',
        'semestre_actual': alumno.semestre,
        'promedio_actual': str(alumno.promedio) if alumno.promedio else '',
        'creditos_aprobados': str(alumno.creditos_aprobados) if alumno.creditos_aprobados else '',
        'estatus_actual': alumno.get_estatus_display(),
        
        # Datos de reinscripción
        'periodo_escolar': str(reinscripcion.periodo_escolar) if reinscripcion.periodo_escolar else '',
        'semestre_reinscripcion': reinscripcion.semestre,
        'motivo_reinscripcion': reinscripcion.get_motivo_reinscripcion_display(),
        'observaciones': reinscripcion.observaciones or '',
        
        # Datos específicos según el motivo
        'fecha_baja': reinscripcion.fecha_baja.strftime('%d/%m/%Y') if reinscripcion.fecha_baja else '',
        'motivo_baja': reinscripcion.motivo_baja or '',
        'carrera_anterior': reinscripcion.carrera_anterior.nombre if reinscripcion.carrera_anterior else '',
        'carrera_nueva': reinscripcion.carrera_nueva.nombre if reinscripcion.carrera_nueva else '',
        
        # Contacto actualizado
        'telefono_actualizado': reinscripcion.telefono_actualizado or alumno.telefono or '',
        'email_actualizado': reinscripcion.email_actualizado or alumno.email or '',
        
        # Estado del proceso
        'estatus': reinscripcion.get_estatus_display(),
    }
    
    return contexto


def crear_plantillas_por_defecto():
    """
    Crea las plantillas por defecto para inscripción y reinscripción si no existen
    """
    plantillas_dir = os.path.join(settings.MEDIA_ROOT, 'plantillas')
    
    # Crear directorio si no existe
    os.makedirs(plantillas_dir, exist_ok=True)
    
    # Plantilla de inscripción
    plantilla_inscripcion = os.path.join(plantillas_dir, 'formato_inscripcion.docx')
    if not os.path.exists(plantilla_inscripcion):
        crear_plantilla_inscripcion_basica(plantilla_inscripcion)
    
    # Plantilla de reinscripción
    plantilla_reinscripcion = os.path.join(plantillas_dir, 'formato_reinscripcion.docx')
    if not os.path.exists(plantilla_reinscripcion):
        crear_plantilla_reinscripcion_basica(plantilla_reinscripcion)


def crear_plantilla_inscripcion_basica(ruta_archivo):
    """
    Crea una plantilla básica de inscripción con variables de ejemplo
    """
    from docx import Document
    from docx.shared import Inches
    
    doc = Document()
    
    # Título
    titulo = doc.add_heading('FORMATO DE INSCRIPCIÓN', 0)
    titulo.alignment = 1  # Centrado
    
    # Información básica
    doc.add_heading('INFORMACIÓN BÁSICA', level=1)
    doc.add_paragraph(f'Folio: {{{{ folio }}}}')
    doc.add_paragraph(f'Fecha de inscripción: {{{{ fecha_inscripcion }}}}')
    doc.add_paragraph(f'Período escolar: {{{{ periodo_escolar }}}}')
    
    # Datos personales
    doc.add_heading('DATOS PERSONALES', level=1)
    doc.add_paragraph(f'Nombre completo: {{{{ nombre_completo }}}}')
    doc.add_paragraph(f'CURP: {{{{ curp }}}}')
    doc.add_paragraph(f'Fecha de nacimiento: {{{{ fecha_nacimiento }}}}')
    doc.add_paragraph(f'Lugar de nacimiento: {{{{ lugar_nacimiento }}}}')
    doc.add_paragraph(f'Género: {{{{ genero }}}}')
    doc.add_paragraph(f'Estado civil: {{{{ estado_civil }}}}')
    
    # Datos académicos
    doc.add_heading('DATOS ACADÉMICOS', level=1)
    doc.add_paragraph(f'Carrera: {{{{ carrera }}}}')
    doc.add_paragraph(f'Semestre: {{{{ semestre }}}}')
    doc.add_paragraph(f'Modalidad: {{{{ modalidad }}}}')
    doc.add_paragraph(f'Turno: {{{{ turno }}}}')
    doc.add_paragraph(f'Escuela de procedencia: {{{{ escuela_procedencia }}}}')
    doc.add_paragraph(f'Promedio de bachillerato: {{{{ promedio_bachillerato }}}}')
    
    # Datos de contacto
    doc.add_heading('DATOS DE CONTACTO', level=1)
    doc.add_paragraph(f'Teléfono: {{{{ telefono }}}}')
    doc.add_paragraph(f'Email: {{{{ email }}}}')
    doc.add_paragraph(f'Contacto de emergencia: {{{{ contacto_emergencia }}}}')
    doc.add_paragraph(f'Teléfono de emergencia: {{{{ telefono_emergencia }}}}')
    
    # Dirección
    doc.add_heading('DIRECCIÓN', level=1)
    doc.add_paragraph(f'Calle y número: {{{{ calle }}}} {{{{ numero }}}}')
    doc.add_paragraph(f'Colonia: {{{{ colonia }}}}')
    doc.add_paragraph(f'Municipio: {{{{ municipio }}}}')
    doc.add_paragraph(f'Estado: {{{{ estado }}}}')
    doc.add_paragraph(f'Código postal: {{{{ codigo_postal }}}}')
    
    # Documentos
    doc.add_heading('DOCUMENTOS ENTREGADOS', level=1)
    doc.add_paragraph(f'Acta de nacimiento: {{{{ acta_nacimiento }}}}')
    doc.add_paragraph(f'Certificado de bachillerato: {{{{ certificado_bachillerato }}}}')
    doc.add_paragraph(f'CURP: {{{{ curp_documento }}}}')
    doc.add_paragraph(f'Fotografías: {{{{ fotografias }}}}')
    doc.add_paragraph(f'Certificado médico: {{{{ certificado_medico }}}}')
    
    # Observaciones
    doc.add_heading('OBSERVACIONES', level=1)
    doc.add_paragraph(f'{{{{ observaciones }}}}')
    
    # Firmas
    doc.add_paragraph('\n\n')
    doc.add_paragraph('_' * 30 + '                    ' + '_' * 30)
    doc.add_paragraph('Firma del alumno                           Firma del responsable')
    
    doc.save(ruta_archivo)


def crear_plantilla_reinscripcion_basica(ruta_archivo):
    """
    Crea una plantilla básica de reinscripción con variables de ejemplo
    """
    from docx import Document
    
    doc = Document()
    
    # Título
    titulo = doc.add_heading('FORMATO DE REINSCRIPCIÓN', 0)
    titulo.alignment = 1  # Centrado
    
    # Información básica
    doc.add_heading('INFORMACIÓN BÁSICA', level=1)
    doc.add_paragraph(f'Folio: {{{{ folio }}}}')
    doc.add_paragraph(f'Fecha de reinscripción: {{{{ fecha_reinscripcion }}}}')
    doc.add_paragraph(f'Período escolar: {{{{ periodo_escolar }}}}')
    
    # Datos del alumno
    doc.add_heading('DATOS DEL ALUMNO', level=1)
    doc.add_paragraph(f'Matrícula: {{{{ matricula }}}}')
    doc.add_paragraph(f'Nombre completo: {{{{ nombre_completo }}}}')
    doc.add_paragraph(f'CURP: {{{{ curp }}}}')
    doc.add_paragraph(f'Carrera actual: {{{{ carrera_actual }}}}')
    doc.add_paragraph(f'Semestre actual: {{{{ semestre_actual }}}}')
    doc.add_paragraph(f'Promedio: {{{{ promedio_actual }}}}')
    doc.add_paragraph(f'Créditos aprobados: {{{{ creditos_aprobados }}}}')
    
    # Datos de reinscripción
    doc.add_heading('DATOS DE REINSCRIPCIÓN', level=1)
    doc.add_paragraph(f'Semestre a cursar: {{{{ semestre_reinscripcion }}}}')
    doc.add_paragraph(f'Motivo de reinscripción: {{{{ motivo_reinscripcion }}}}')
    doc.add_paragraph(f'Observaciones: {{{{ observaciones }}}}')
    
    # Información adicional (condicional)
    doc.add_heading('INFORMACIÓN ADICIONAL', level=1)
    doc.add_paragraph(f'Fecha de baja: {{{{ fecha_baja }}}}')
    doc.add_paragraph(f'Motivo de baja: {{{{ motivo_baja }}}}')
    doc.add_paragraph(f'Carrera anterior: {{{{ carrera_anterior }}}}')
    doc.add_paragraph(f'Nueva carrera: {{{{ carrera_nueva }}}}')
    
    # Contacto actualizado
    doc.add_heading('CONTACTO ACTUALIZADO', level=1)
    doc.add_paragraph(f'Teléfono: {{{{ telefono_actualizado }}}}')
    doc.add_paragraph(f'Email: {{{{ email_actualizado }}}}')
    
    # Estado del proceso
    doc.add_heading('ESTADO DEL PROCESO', level=1)
    
    # Firmas
    doc.add_paragraph('\n\n')
    doc.add_paragraph('_' * 30 + '                    ' + '_' * 30)
    doc.add_paragraph('Firma del alumno                           Firma del responsable')
    
    doc.save(ruta_archivo)