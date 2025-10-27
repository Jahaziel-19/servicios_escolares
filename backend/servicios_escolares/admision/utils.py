from django.http import HttpResponse
from django.conf import settings
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from io import BytesIO
import os
from datetime import datetime
import json
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics import renderPM
from django.urls import reverse


def _crear_qr_image(data: str, size_cm: float = 3.0):
    """Genera una imagen de QR para el dato proporcionado y la devuelve como Flowable Image."""
    try:
        qrw = qr.QrCodeWidget(data)
        bounds = qrw.getBounds()
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        size_pts = size_cm * cm
        d = Drawing(size_pts, size_pts, transform=[size_pts / width, 0, 0, size_pts / height, 0, 0])
        d.add(qrw)
        png_bytes = renderPM.drawToString(d, fmt='PNG')
        return Image(BytesIO(png_bytes), width=size_pts, height=size_pts)
    except Exception:
        return None


def generar_ficha_admision_pdf(solicitud):
    """
    Genera una ficha de admisión en formato PDF similar al formato oficial
    """
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=1.5*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    titulo_principal = ParagraphStyle(
        'TituloPrincipal',
        fontSize=14,
        spaceAfter=2,
        alignment=TA_CENTER,
        textColor=HexColor('#0066cc'),
        fontName='Helvetica-Bold',
        leading=16
    )
    
    titulo_secundario = ParagraphStyle(
        'TituloSecundario',
        fontSize=12,
        spaceAfter=2,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )
    
    subtitulo = ParagraphStyle(
        'Subtitulo',
        fontSize=9,
        spaceAfter=10,
        alignment=TA_CENTER,
        textColor=colors.black,
        fontName='Helvetica'
    )
    
    titulo_ficha = ParagraphStyle(
        'TituloFicha',
        fontSize=12,
        spaceAfter=10,
        alignment=TA_CENTER,
        textColor=HexColor('#cc0000'),
        fontName='Helvetica-Bold'
    )
    
    texto_label = ParagraphStyle(
        'TextoLabel',
        fontSize=8,
        textColor=colors.black,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER
    )
    
    texto_dato = ParagraphStyle(
        'TextoDato',
        fontSize=9,
        textColor=colors.black,
        fontName='Helvetica',
        alignment=TA_CENTER
    )
    
    seccion_titulo = ParagraphStyle(
        'SeccionTitulo',
        fontSize=9,
        textColor=colors.black,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        spaceAfter=6
    )
    
    texto_normal = ParagraphStyle(
        'TextoNormal',
        fontSize=8,
        textColor=colors.black,
        fontName='Helvetica',
        leading=10
    )
    
    texto_pequeno = ParagraphStyle(
        'TextoPequeno',
        fontSize=7,
        textColor=colors.black,
        fontName='Helvetica',
        leading=9
    )
    
    story = []
    
    # === ENCABEZADO INSTITUCIONAL ===
    # Logo y título (simular disposición con tabla)
    # Construir URL absoluto para el QR hacia el registro exitoso del aspirante
    try:
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        path_qr = reverse('admision:admision_publico:registro_exitoso', args=[solicitud.folio])
        qr_url = f"{base_url}{path_qr}"
        qr_img = _crear_qr_image(qr_url, size_cm=3.0)
    except Exception:
        qr_img = None
    
    # Bloque derecho como tabla anidada para evitar KeepTogether dentro de la celda
    if qr_img:
        qr_block_data = [
            [Paragraph(f"Folio de ficha: ____{solicitud.folio}____", texto_label)],
            [qr_img],
        ]
    else:
        qr_block_data = [
            [Paragraph(f"Folio de ficha: ____{solicitud.folio}____", texto_label)],
            [Paragraph("", texto_label)],
        ]
    qr_block_table = Table(qr_block_data, colWidths=[doc.width * 0.3])
    qr_block_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    encabezado_data = [
        [
            Paragraph("TECNOLÓGICO NACIONAL DE MÉXICO", titulo_principal),
            qr_block_table,
        ],
        [
            Paragraph("INSTITUTO TECNOLÓGICO SUPERIOR DE TLAXCO", titulo_secundario),
            ""
        ],
        [
            Paragraph("Departamento de Servicios Escolares", subtitulo),
            ""
        ]
    ]
    
    encabezado_table = Table(encabezado_data, colWidths=[doc.width * 0.7, doc.width * 0.3])
    encabezado_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(encabezado_table)
    
    # Línea separadora azul
    linea = Table([[""]], colWidths=[doc.width])
    linea.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 2, HexColor('#0066cc')),
    ]))
    story.append(linea)
    story.append(Spacer(1, 8))
    
    # Título de la ficha
    story.append(Paragraph(f"SOLICITUD PARA EL EXAMEN DE SELECCIÓN", titulo_ficha))
    story.append(Spacer(1, 10))
    
    # === INFORMACIÓN BÁSICA (FOLIO, FECHA, ESTADO) ===
    info_basica_data = [
        [
            Paragraph("FOLIO", texto_label),
            Paragraph("FECHA DE REGISTRO", texto_label),
            Paragraph("ESTADO", texto_label)
        ],
        [
            Paragraph(solicitud.folio, texto_dato),
            Paragraph(solicitud.fecha_registro.strftime('%d/%m/%Y %H:%M'), texto_dato),
            Paragraph(solicitud.get_estado_display(), texto_dato)
        ]
    ]
    
    info_basica_table = Table(info_basica_data, colWidths=[doc.width/3, doc.width/3, doc.width/3])
    info_basica_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_basica_table)
    story.append(Spacer(1, 12))
    
    # === PROCESAR RESPUESTAS ===
    if solicitud.respuestas_json:
        try:
            respuestas = solicitud.respuestas_json if isinstance(solicitud.respuestas_json, dict) else json.loads(solicitud.respuestas_json)
        except Exception:
            respuestas = {}
    else:
        respuestas = {}
    
    # === DATOS PERSONALES ===
    story.append(Paragraph("DATOS PERSONALES", seccion_titulo))
    
    # Fila 1: Apellidos y Nombre
    nombre_data = [
        [
            Paragraph("Apellido Paterno", texto_label),
            Paragraph("Apellido Materno", texto_label),
            Paragraph("Nombre(s)", texto_label)
        ],
        [
            Paragraph(respuestas.get('apellido_paterno', ''), texto_dato),
            Paragraph(respuestas.get('apellido_materno', ''), texto_dato),
            Paragraph(respuestas.get('nombre', ''), texto_dato)
        ]
    ]
    nombre_table = Table(nombre_data, colWidths=[doc.width/3, doc.width/3, doc.width/3])
    nombre_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(nombre_table)
    
    # Fila 2: Fecha nacimiento y nacionalidad
    nacimiento_data = [
        [
            Paragraph("Fecha de<br/>Nacimiento", texto_label),
            "",
            Paragraph("Nacionalidad", texto_label)
        ],
        [
            Paragraph(respuestas.get('fecha_nacimiento', ''), texto_dato),
            "",
            Paragraph(respuestas.get('nacionalidad', 'Mexicano(a)'), texto_dato)
        ]
    ]
    nacimiento_table = Table(nacimiento_data, colWidths=[doc.width*0.4, doc.width*0.2, doc.width*0.4])
    nacimiento_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#cccccc')),
        ('SPAN', (0, 0), (1, 0)),
        ('SPAN', (0, 1), (1, 1)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(nacimiento_table)
    
    # Fila 3: Edad, Género y CURP
    edad_genero_data = [
        [
            Paragraph("EDAD", texto_label),
            Paragraph("GÉNERO", texto_label),
            Paragraph("CURP", texto_label)
        ],
        [
            Paragraph(str(respuestas.get('edad', '')), texto_dato),
            Paragraph(respuestas.get('sexo', ''), texto_dato),
            Paragraph(respuestas.get('curp', ''), texto_dato)
        ]
    ]
    edad_genero_table = Table(edad_genero_data, colWidths=[doc.width*0.15, doc.width*0.25, doc.width*0.6])
    edad_genero_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(edad_genero_table)
    story.append(Spacer(1, 10))
    
    # === CARRERAS ===
    story.append(Paragraph("Carreras:", seccion_titulo))
    
    carreras_data = [
        [
            Paragraph("1ª Opción", texto_label),
            Paragraph("2ª Opción", texto_label)
        ],
        [
            Paragraph(respuestas.get('carrera_primera_opcion', 'N/A'), texto_dato),
            Paragraph(respuestas.get('carrera_segunda_opcion', ''), texto_dato)
        ]
    ]
    carreras_table = Table(carreras_data, colWidths=[doc.width/2, doc.width/2])
    carreras_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(carreras_table)
    story.append(Spacer(1, 10))
    
    # === PREPARATORIA DE PROCEDENCIA ===
    story.append(Paragraph("Preparatoria de Procedencia:", seccion_titulo))
    
    prep_data = [
        [
            Paragraph("Preparatoria:", texto_label),
            Paragraph("Nombre", texto_label),
            Paragraph("Ciudad", texto_label),
            Paragraph("Estado", texto_label)
        ],
        [
            Paragraph(respuestas.get('tipo_preparatoria', ''), texto_dato),
            Paragraph(respuestas.get('escuela_procedencia', ''), texto_dato),
            Paragraph(respuestas.get('ciudad_escuela', ''), texto_dato),
            Paragraph(respuestas.get('estado_escuela', ''), texto_dato)
        ]
    ]
    prep_table = Table(prep_data, colWidths=[doc.width*0.15, doc.width*0.4, doc.width*0.225, doc.width*0.225])
    prep_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(prep_table)
    
    # Promedio y año
    prom_data = [
        [
            Paragraph("Promedio General:", texto_label),
            Paragraph("Año de Egreso:", texto_label)
        ],
        [
            Paragraph(str(respuestas.get('promedio_bachillerato', '')), texto_dato),
            Paragraph(str(respuestas.get('año_egreso', '')), texto_dato)
        ]
    ]
    prom_table = Table(prom_data, colWidths=[doc.width/2, doc.width/2])
    prom_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(prom_table)
    story.append(Spacer(1, 10))
    
    # === DOMICILIO ACTUAL ===
    story.append(Paragraph("Domicilio Actual", seccion_titulo))
    
    domicilio_data = [
        [
            Paragraph("Calle, N. Exterior y/o Interior", texto_label),
        ],
        [
            Paragraph(respuestas.get('direccion', ''), texto_dato),
        ]
    ]
    domicilio_table1 = Table(domicilio_data, colWidths=[doc.width])
    domicilio_table1.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(domicilio_table1)
    
    domicilio_data2 = [
        [
            Paragraph("Colonia o Localidad", texto_label),
            Paragraph("Municipio", texto_label),
            Paragraph("Estado", texto_label)
        ],
        [
            Paragraph(respuestas.get('colonia', ''), texto_dato),
            Paragraph(respuestas.get('ciudad', ''), texto_dato),
            Paragraph(respuestas.get('estado', ''), texto_dato)
        ]
    ]
    domicilio_table2 = Table(domicilio_data2, colWidths=[doc.width/3, doc.width/3, doc.width/3])
    domicilio_table2.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(domicilio_table2)
    
    domicilio_data3 = [
        [
            Paragraph("Código Postal", texto_label),
            Paragraph("Correo Electrónico (e-mail)", texto_label),
            Paragraph("Teléfono", texto_label)
        ],
        [
            Paragraph(respuestas.get('codigo_postal', ''), texto_dato),
            Paragraph(respuestas.get('email', ''), texto_dato),
            Paragraph(respuestas.get('telefono', ''), texto_dato)
        ]
    ]
    domicilio_table3 = Table(domicilio_data3, colWidths=[doc.width*0.2, doc.width*0.5, doc.width*0.3])
    domicilio_table3.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(domicilio_table3)
    story.append(Spacer(1, 12))
    
    # === TEXTO INFORMATIVO ===
    texto_info = f"Solicitud para aspirantes que deseen ingresar al <b>INSTITUTO TECNOLÓGICO SUPERIOR DE TLAXCO</b> para el periodo <b>{solicitud.periodo.nombre.upper()}</b>."
    story.append(Paragraph(texto_info, texto_normal))
    story.append(Spacer(1, 15))
    
    # === FIRMAS ===
    firmas_data = [
        [
            Paragraph("           ___________________________________", texto_label),
            Paragraph("           ___________________________________", texto_label)
        ],
        [
            Paragraph("Firma del Solicitante", texto_label),
            Paragraph("Validación de la Ficha", texto_label)
        ]
    ]
    firmas_table = Table(firmas_data, colWidths=[doc.width/2, doc.width/2])
    firmas_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(firmas_table)
    story.append(Spacer(1, 12))
    
    # === NOTAS ===
    story.append(Paragraph("NOTAS:", texto_normal))
    story.append(Spacer(1, 4))
    
    notas = [
        "Esta ficha es válida únicamente para el período de admisión indicado.",
        "Si eres extranjero o mexicano que desea contar con el permiso para estudiar en México, expedido por la Secretaría de Gobernación y presentarlo el día de su inscripción.",
        "Si eres menor de edad, tu padre o tutor o persona que te acompañe o tu bachillerato en el extranjero deberá presentar revalidación de estudios correspondientes al momento de la inscripción.",
        "Esta persona al Instituto Tecnológico, deberá haber concluido los estudios de bachillerato (D. O. F. 17 de diciembre de 1997).",
        "Estoy consciente que mis datos personales son recabados y utilizados con fines académicos, administrativos y/o de operación, por lo que autorizo al Instituto Tecnológico Superior de Tlaxco utilizarlos para los fines detallados en el Aviso de Privacidad de datos personales proporcionados por esta Institución. Así mismo estoy consciente que cualquier cambio de Aviso de Privacidad de datos personales podrá efectuarse por esta institución en cualquier momento."
    ]
    
    for i, nota in enumerate(notas, 1):
        story.append(Paragraph(f"➤ {nota}", texto_pequeno))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph("        ___________________________________", texto_label))
    story.append(Paragraph("Firma del solicitante", texto_label))
    
    doc.build(story)
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