from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum
from django.conf import settings
from .models import Residencia, ResidenciaBitacoraEntry, Tramite, Bitacora
from .forms import ActaResidenciaForm, ResidenciaForm
from datos_academicos.models import Alumno, PeriodoEscolar
from docxtpl import DocxTemplate
from docx2pdf import convert
import pythoncom
import pandas as pd
import os
import tempfile
from datetime import datetime
from io import BytesIO

# Importaciones para PDF directo
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT


RESIDENCIAS_DIR = os.path.join(settings.BASE_DIR, 'base de datos', 'Procesos', 'residencias')
EXCEL_FILENAME = 'BITACORA DE RESIDENCIA PROFESIONAL ACTUALIZADO 2.xlsx'
DOCX_ACTA_FILENAME = 'FORMATO 2024.docx'


def _normalizar_nombre(col):
    return str(col).strip().lower()


def _buscar_col(cols, opciones):
    cols_norm = { _normalizar_nombre(c): c for c in cols }
    for op in opciones:
        key = _normalizar_nombre(op)
        if key in cols_norm:
            return cols_norm[key]
    return None


def _parse_residencias_desde_excel(path_excel):
    xls = pd.ExcelFile(path_excel)
    creados = 0
    actualizados = 0
    entradas_bitacora = 0

    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name)
        if df.empty:
            continue

        df.columns = [str(c).strip() for c in df.columns]

        col_matricula = _buscar_col(df.columns, ['matricula', 'matrícula'])
        col_empresa = _buscar_col(df.columns, ['empresa', 'compañía', 'organización'])
        col_proyecto = _buscar_col(df.columns, ['proyecto', 'nombre del proyecto'])
        col_asesor_int = _buscar_col(df.columns, ['asesor interno'])
        col_asesor_ext = _buscar_col(df.columns, ['asesor externo'])
        col_inicio = _buscar_col(df.columns, ['inicio', 'fecha inicio', 'fecha de inicio'])
        col_fin = _buscar_col(df.columns, ['fin', 'fecha fin', 'fecha de fin', 'termino'])
        col_horas = _buscar_col(df.columns, ['horas', 'horas realizadas', 'hrs'])
        col_fecha = _buscar_col(df.columns, ['fecha', 'día'])
        col_actividad = _buscar_col(df.columns, ['actividad', 'tarea', 'descripcion actividad'])
        col_evidencia = _buscar_col(df.columns, ['evidencia', 'observaciones'])

        es_bitacora = col_matricula and col_fecha and col_actividad
        es_residencia = col_matricula and (col_empresa or col_proyecto)

        for _, row in df.iterrows():
            matricula = str(row[col_matricula]).strip() if col_matricula else None
            if not matricula or matricula.lower() in ('nan', '', 'none'):
                continue

            alumno = Alumno.objects.filter(matricula__iexact=matricula).first()
            if not alumno:
                # Si no existe el alumno, saltamos esta fila
                continue

            residencia = None

            if es_residencia:
                empresa = str(row[col_empresa]).strip() if col_empresa else ''
                proyecto = str(row[col_proyecto]).strip() if col_proyecto else ''
                asesor_interno = str(row[col_asesor_int]).strip() if col_asesor_int else ''
                asesor_externo = str(row[col_asesor_ext]).strip() if col_asesor_ext else ''

                residencia, created = Residencia.objects.get_or_create(
                    alumno=alumno,
                    proyecto=proyecto or 'Proyecto de Residencia',
                    defaults={
                        'empresa': empresa or 'Empresa',
                        'asesor_interno': asesor_interno or 'Asesor Interno',
                        'asesor_externo': asesor_externo,
                    }
                )

                # Actualiza datos si existen fechas/horas
                def _parse_fecha(val):
                    try:
                        if pd.isna(val):
                            return None
                        if isinstance(val, datetime):
                            return val.date()
                        return datetime.strptime(str(val).strip(), '%Y-%m-%d').date()
                    except Exception:
                        return None

                f_inicio = _parse_fecha(row[col_inicio]) if col_inicio else None
                f_fin = _parse_fecha(row[col_fin]) if col_fin else None
                horas_prog = None
                try:
                    if col_horas:
                        horas_prog = int(float(str(row[col_horas]).strip()))
                except Exception:
                    horas_prog = None

                cambios = False
                if f_inicio and residencia.fecha_inicio != f_inicio:
                    residencia.fecha_inicio = f_inicio
                    cambios = True
                if f_fin and residencia.fecha_fin != f_fin:
                    residencia.fecha_fin = f_fin
                    cambios = True
                if horas_prog and residencia.horas_programadas != horas_prog:
                    residencia.horas_programadas = horas_prog
                    cambios = True
                if cambios:
                    residencia.save()
                    actualizados += 1
                else:
                    if created:
                        creados += 1

            # Bitácora
            if es_bitacora:
                if not residencia:
                    # buscamos residencia existente por alumno
                    residencia = Residencia.objects.filter(alumno=alumno).order_by('-creado').first()
                    if not residencia:
                        continue

                # parse fecha y horas
                def _parse_fecha_bit(val):
                    try:
                        if pd.isna(val):
                            return None
                        if isinstance(val, datetime):
                            return val.date()
                        return datetime.strptime(str(val).strip(), '%Y-%m-%d').date()
                    except Exception:
                        return None

                fecha_b = _parse_fecha_bit(row[col_fecha]) if col_fecha else None
                actividad = str(row[col_actividad]).strip() if col_actividad else ''
                evidencia = str(row[col_evidencia]).strip() if col_evidencia else ''
                horas_b = 0
                try:
                    horas_b = int(float(str(row[col_horas]).strip())) if col_horas else 0
                except Exception:
                    horas_b = 0

                if fecha_b and actividad:
                    ResidenciaBitacoraEntry.objects.create(
                        residencia=residencia,
                        fecha=fecha_b,
                        actividad=actividad,
                        horas=horas_b,
                        evidencia=evidencia,
                        hoja=sheet_name
                    )
                    entradas_bitacora += 1

    # Recalcular horas cumplidas
    for r in Residencia.objects.all():
        total_horas = r.bitacora.aggregate(s=Sum('horas'))['s'] or 0
        if r.horas_cumplidas != total_horas:
            r.horas_cumplidas = total_horas
            r.save()

    return {
        'residencias_creadas': creados,
        'residencias_actualizadas': actualizados,
        'bitacoras_insertadas': entradas_bitacora,
    }


@login_required
def residencias_panel(request):
    indicadores = {
        'total': Residencia.objects.count(),
        'en_curso': Residencia.objects.filter(estado='EN_CURSO').count(),
        'concluidas': Residencia.objects.filter(estado='CONCLUIDA').count(),
        'aprobadas': Residencia.objects.filter(estado='APROBADA').count(),
        'reprobadas': Residencia.objects.filter(estado='REPROBADA').count(),
        'horas_totales': ResidenciaBitacoraEntry.objects.aggregate(s=Sum('horas'))['s'] or 0,
    }

    residencias = Residencia.objects.select_related('alumno', 'periodo_escolar').order_by('-creado')[:50]

    return render(request, 'procedimientos/residencias/panel.html', {
        'segment': 'residencias',
        'indicadores': indicadores,
        'residencias': residencias,
    })


@login_required
def residencias_crear(request):
    if request.method == 'POST':
        form = ResidenciaForm(request.POST)
        if form.is_valid():
            residencia = form.save()
            messages.success(request, 'Residencia creada correctamente. Ahora puedes emitir el acta.')
            return redirect('procedimientos:residencias_emitir_acta', residencia_id=residencia.id)
    else:
        form = ResidenciaForm()

    return render(request, 'procedimientos/residencias/crear.html', {
        'form': form,
        'segment': 'residencias',
    })


@login_required
def residencias_importar_excel(request):
    excel_path = os.path.join(RESIDENCIAS_DIR, EXCEL_FILENAME)
    if not os.path.exists(excel_path):
        messages.error(request, f'No se encontró el Excel en {excel_path}')
        return redirect('procedimientos:residencias_panel')

    resumen = _parse_residencias_desde_excel(excel_path)
    messages.success(request, (
        f"Importación completada: {resumen['residencias_creadas']} residencias nuevas, "
        f"{resumen['residencias_actualizadas']} actualizadas, "
        f"{resumen['bitacoras_insertadas']} entradas de bitácora"
    ))
    return redirect('procedimientos:residencias_panel')


@login_required
def residencias_generar_acta(request, residencia_id):
    residencia = Residencia.objects.select_related('alumno', 'periodo_escolar').filter(id=residencia_id).first()
    if not residencia:
        messages.warning(request, 'La residencia solicitada no existe o fue eliminada.')
        return redirect('procedimientos:residencias_panel')

    alumno = residencia.alumno
    periodo = residencia.periodo_escolar

    # Construir PDF personalizado directamente con ReportLab
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        'TituloActa',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=12
    )
    subtitulo_style = ParagraphStyle(
        'SubtituloActa',
        parent=styles['Heading2'],
        fontSize=12,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=18
    )
    texto_style = ParagraphStyle(
        'Texto',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT,
        leading=14
    )

    story = []
    story.append(Paragraph('Acta de Residencia Profesional', titulo_style))
    story.append(Paragraph('Departamento de Servicios Escolares', subtitulo_style))
    story.append(Spacer(1, 12))

    # Datos principales en tabla
    datos = [
        ['Alumno', f"{alumno.nombre} {alumno.apellido_paterno} {alumno.apellido_materno}"],
        ['Matrícula', alumno.matricula],
        ['Carrera', getattr(getattr(alumno, 'carrera', None), 'nombre', '')],
        ['Periodo', str(periodo) if periodo else ''],
        ['Empresa', residencia.empresa or ''],
        ['Proyecto', residencia.proyecto or ''],
        ['Asesor interno', residencia.asesor_interno or ''],
        ['Asesor externo', residencia.asesor_externo or ''],
        ['Fecha de inicio', residencia.fecha_inicio.strftime('%d/%m/%Y') if residencia.fecha_inicio else ''],
        ['Fecha de término', residencia.fecha_fin.strftime('%d/%m/%Y') if residencia.fecha_fin else ''],
        ['Horas programadas', str(residencia.horas_programadas or 0)],
        ['Horas cumplidas', str(residencia.horas_cumplidas or 0)],
        ['Avance', f"{residencia.avance_horas()}%"],
    ]

    tabla_estilo = TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (0,-1), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('COLWIDTHS', (0,0), (0,-1), 5*cm),
    ])
    tabla = Table(datos, colWidths=[5*cm, 10*cm])
    tabla.setStyle(tabla_estilo)
    story.append(tabla)
    story.append(Spacer(1, 18))

    # Declaración
    texto = (
        'Por medio de la presente se certifica que el/la alumno(a) indicado(a) ha realizado su Residencia Profesional '
        'conforme a los lineamientos establecidos, en la empresa y proyecto descritos anteriormente. '
        'El presente documento se emite para los fines administrativos correspondientes.'
    )
    story.append(Paragraph(texto, texto_style))
    story.append(Spacer(1, 24))

    # Firmas
    firmas_datos = [
        ['______________________________', '______________________________'],
        ['Alumno', 'Asesor Interno'],
        ['______________________________', '______________________________'],
        ['Asesor Externo', 'Jefe de Servicios Escolares'],
    ]
    firmas_tabla = Table(firmas_datos, colWidths=[8*cm, 8*cm])
    firmas_tabla.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(firmas_tabla)
    story.append(Spacer(1, 12))

    # Fecha de emisión
    fecha_emision = datetime.now().strftime('%d/%m/%Y')
    story.append(Paragraph(f"Fecha de emisión: {fecha_emision}", texto_style))

    # Construir PDF
    doc.build(story)

    # Registrar trámite y bitácora
    tramite = Tramite.objects.create(
        alumno=alumno,
        tipo='acta_residencia',
        estado='Procesado',
        fecha_procesado=datetime.now(),
        observaciones=f'Acta de residencia generada para proyecto "{residencia.proyecto}".'
    )
    Bitacora.objects.create(
        tramite=tramite,
        usuario=request.user,
        accion='Generó acta de residencia',
        comentario=f'Residencia en {residencia.empresa} - Proyecto: {residencia.proyecto}'
    )

    # Responder PDF
    buffer.seek(0)
    from django.http import HttpResponse
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="acta_residencia_{alumno.matricula}.pdf"'
    return response


@login_required
def residencias_emitir_acta(request, residencia_id):
    residencia = Residencia.objects.select_related('alumno', 'periodo_escolar').filter(id=residencia_id).first()
    if not residencia:
        messages.warning(request, 'La residencia solicitada no existe o fue eliminada.')
        return redirect('procedimientos:residencias_panel')
    if request.method == 'POST':
        form = ActaResidenciaForm(request.POST)
        if form.is_valid():
            # Actualizar/guardar datos en la residencia
            cd = form.cleaned_data
            residencia.alumno = cd['alumno']
            residencia.periodo_escolar = cd.get('periodo_escolar')
            residencia.empresa = cd['empresa']
            residencia.proyecto = cd['proyecto']
            residencia.asesor_interno = cd['asesor_interno']
            residencia.asesor_externo = cd.get('asesor_externo', '')
            residencia.fecha_inicio = cd.get('fecha_inicio')
            residencia.fecha_fin = cd.get('fecha_fin')
            residencia.horas_programadas = cd.get('horas_programadas')
            residencia.save()

            # Generar acta en PDF, registrar y responder
            return residencias_generar_acta(request, residencia.id)
    else:
        form = ActaResidenciaForm()
        form.inicializar_desde_residencia(residencia)

    return render(request, 'procedimientos/residencias/emitir_acta.html', {
        'form': form,
        'residencia': residencia,
    })