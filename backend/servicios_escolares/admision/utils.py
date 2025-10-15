from django.http import HttpResponse
from django.conf import settings
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from io import BytesIO
import os
from datetime import datetime
import json


def generar_ficha_admision_pdf(solicitud):
    """
    Genera una ficha de admisión en formato PDF para una solicitud específica
    """
    # Crear buffer para el PDF
    buffer = BytesIO()
    
    # Crear el documento PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Obtener estilos
    styles = getSampleStyleSheet()
    
    # Crear estilos personalizados
    titulo_principal = ParagraphStyle(
        'TituloPrincipal',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=12,
        alignment=TA_CENTER,
        textColor=HexColor('#1976d2'),  # Azul Material Design
        fontName='Helvetica-Bold'
    )
    
    titulo_secundario = ParagraphStyle(
        'TituloSecundario',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=8,
        alignment=TA_CENTER,
        textColor=HexColor('#424242'),  # Gris oscuro Material Design
        fontName='Helvetica-Bold'
    )
    
    titulo_ficha = ParagraphStyle(
        'TituloFicha',
        parent=styles['Heading2'],
        fontSize=15,
        spaceAfter=16,
        alignment=TA_CENTER,
        textColor=HexColor('#d32f2f'),  # Rojo Material Design
        fontName='Helvetica-Bold'
    )
    
    texto_normal = ParagraphStyle(
        'TextoNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        textColor=HexColor('#212121'),  # Negro Material Design
        fontName='Helvetica'
    )
    
    texto_bold = ParagraphStyle(
        'TextoBold',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        textColor=HexColor('#212121'),
        fontName='Helvetica-Bold'
    )
    
    texto_pequeno = ParagraphStyle(
        'TextoPequeno',
        parent=styles['Normal'],
        fontSize=8,
        spaceAfter=4,
        textColor=HexColor('#666666'),
        fontName='Helvetica'
    )
    
    # Construir el contenido del PDF
    story = []
    
    # Encabezado institucional
    story.append(Paragraph("TECNOLÓGICO NACIONAL DE MÉXICO", titulo_principal))
    story.append(Paragraph("INSTITUTO TECNOLÓGICO SUPERIOR DE TLAXCO", titulo_secundario))
    story.append(Paragraph("Depto. de Servicios Escolares", texto_normal))
    story.append(Spacer(1, 20))
    
    # Título de la ficha
    story.append(Paragraph(f"FICHA DE ADMISIÓN {solicitud.periodo.nombre.upper()}", titulo_ficha))
    story.append(Spacer(1, 20))
    
    # Información básica de la solicitud
    info_basica_data = [
        ['FOLIO', 'FECHA DE REGISTRO', 'ESTADO'],
        [
            solicitud.folio,
            solicitud.fecha_registro.strftime('%d/%m/%Y %H:%M'),
            solicitud.get_estado_display()
        ]
    ]
    
    info_basica_table = Table(info_basica_data, colWidths=[4*cm, 5*cm, 4*cm])
    info_basica_table.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1976d2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Contenido
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    story.append(info_basica_table)
    story.append(Spacer(1, 20))
    
    # Datos del aspirante (extraer del JSON de respuestas)
    # Respuestas pueden venir como dict o como string JSON; manejar ambos casos de forma segura
    if solicitud.respuestas_json:
        try:
            if isinstance(solicitud.respuestas_json, dict):
                respuestas = solicitud.respuestas_json
            else:
                respuestas = json.loads(solicitud.respuestas_json)
        except Exception:
            respuestas = {}
    else:
        respuestas = {}
    
    # Información personal
    story.append(Paragraph("DATOS PERSONALES", texto_bold))
    story.append(Spacer(1, 10))
    
    datos_personales = [
        ['CURP:', respuestas.get('curp', 'N/A')],
        ['Nombre completo:', f"{respuestas.get('nombre', '')} {respuestas.get('apellido_paterno', '')} {respuestas.get('apellido_materno', '')}".strip()],
        ['Fecha de nacimiento:', respuestas.get('fecha_nacimiento', 'N/A')],
        ['Género:', respuestas.get('genero', 'N/A')],
        ['Estado civil:', respuestas.get('estado_civil', 'N/A')],
    ]
    
    for etiqueta, valor in datos_personales:
        story.append(Paragraph(f"<b>{etiqueta}</b> {valor}", texto_normal))
    
    story.append(Spacer(1, 15))
    
    # Información de contacto
    story.append(Paragraph("DATOS DE CONTACTO", texto_bold))
    story.append(Spacer(1, 10))
    
    datos_contacto = [
        ['Teléfono:', respuestas.get('telefono', 'N/A')],
        ['Email:', respuestas.get('email', 'N/A')],
        ['Dirección:', respuestas.get('direccion', 'N/A')],
        ['Ciudad:', respuestas.get('ciudad', 'N/A')],
        ['Estado:', respuestas.get('estado', 'N/A')],
        ['Código postal:', respuestas.get('codigo_postal', 'N/A')],
    ]
    
    for etiqueta, valor in datos_contacto:
        story.append(Paragraph(f"<b>{etiqueta}</b> {valor}", texto_normal))
    
    story.append(Spacer(1, 15))
    
    # Información académica
    story.append(Paragraph("INFORMACIÓN ACADÉMICA", texto_bold))
    story.append(Spacer(1, 10))
    
    datos_academicos = [
        ['Carrera de interés:', respuestas.get('carrera_interes', 'N/A')],
        ['Escuela de procedencia:', respuestas.get('escuela_procedencia', 'N/A')],
        ['Promedio de bachillerato:', respuestas.get('promedio_bachillerato', 'N/A')],
        ['Año de egreso:', respuestas.get('año_egreso', 'N/A')],
    ]
    
    for etiqueta, valor in datos_academicos:
        story.append(Paragraph(f"<b>{etiqueta}</b> {valor}", texto_normal))
    
    story.append(Spacer(1, 20))
    
    # Información importante
    story.append(Paragraph("INFORMACIÓN IMPORTANTE", texto_bold))
    story.append(Spacer(1, 10))
    
    instrucciones = [
        "• Esta ficha es válida únicamente para el período de admisión indicado.",
        "• Conserve este documento como comprobante de su solicitud de admisión.",
        "• Para consultar el estado de su solicitud, utilice su folio y CURP.",
        "• Los resultados del proceso de admisión serán publicados en las fechas establecidas.",
        "• Para cualquier aclaración, comuníquese al Departamento de Servicios Escolares.",
    ]
    
    for instruccion in instrucciones:
        story.append(Paragraph(instruccion, texto_normal))
    
    story.append(Spacer(1, 20))
    
    # Información de contacto institucional
    story.append(Paragraph("CONTACTO", texto_bold))
    story.append(Spacer(1, 10))
    
    contacto_info = [
        "Instituto Tecnológico Superior de Tlaxco",
        "Departamento de Servicios Escolares",
        "Teléfono: (241) 100-0000",
        "Email: servicios.escolares@itst.edu.mx",
        "Sitio web: www.itst.edu.mx"
    ]
    
    for info in contacto_info:
        story.append(Paragraph(info, texto_pequeno))
    
    story.append(Spacer(1, 30))
    
    # Pie de página con fecha de generación
    story.append(Paragraph(
        f"Documento generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}",
        texto_pequeno
    ))
    
    # Construir el PDF
    doc.build(story)
    
    # Preparar la respuesta
    buffer.seek(0)
    return buffer.getvalue()


def crear_respuesta_pdf_ficha(solicitud, filename=None):
    """
    Crea una respuesta HTTP con el PDF de la ficha de admisión
    """
    if not filename:
        filename = f"Ficha_Admision_{solicitud.folio}.pdf"
    
    pdf_content = generar_ficha_admision_pdf(solicitud)
    
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response