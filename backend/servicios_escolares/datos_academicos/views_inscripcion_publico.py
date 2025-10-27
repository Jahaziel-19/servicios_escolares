from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction

from admision.models import SolicitudAdmision
from .models_inscripcion_nueva import InscripcionNueva, DocumentoInscripcionNueva, PagoInscripcionConcepto
from .forms_inscripcion_nueva import (
    Paso1AspiranteForm,
    Paso2ProgramaForm,
    Paso3DocumentosForm,
    Paso4PagoForm,
    PagoConceptoFormSet,
)

# Configuración de los pasos
STEPS = {
    1: {'name': 'Aspirante', 'form': Paso1AspiranteForm},
    2: {'name': 'Programa', 'form': Paso2ProgramaForm},
    3: {'name': 'Documentos', 'form': Paso3DocumentosForm},
    4: {'name': 'Pago', 'form': Paso4PagoForm},
}


def _get_solicitud_by_folio(folio: str):
    return SolicitudAdmision.objects.filter(folio=folio).first()


def _estado_habilitado(estado: str) -> bool:
    return estado and estado.lower() in ['aceptada', 'seleccionado']


def _get_or_create_inscripcion_publico(request, solicitud: SolicitudAdmision):
    # Extraer nombre desde las respuestas del formulario de admisión
    nombre = solicitud.get_respuesta('nombre') or ''
    apellido_paterno = solicitud.get_respuesta('apellido_paterno') or ''
    apellido_materno = solicitud.get_respuesta('apellido_materno') or ''

    inscripcion, created = InscripcionNueva.objects.get_or_create(
        folio=solicitud.folio,
        defaults={
            'nombre': nombre,
            'apellido_paterno': apellido_paterno,
            'apellido_materno': apellido_materno,
            'curp': solicitud.curp,
            'email': solicitud.email,
        }
    )
    return inscripcion


def _ensure_pago_conceptos(inscripcion: InscripcionNueva):
    # Asegura que existan los registros de conceptos de pago para esta inscripción
    for code, _label in PagoInscripcionConcepto.CONCEPT_CHOICES:
        PagoInscripcionConcepto.objects.get_or_create(
            inscripcion=inscripcion,
            concepto=code,
            defaults={'estado': 'pendiente'}
        )


def inscripcion_publico_inicio(request):
    """Pantalla de inicio para capturar folio y entrar al flujo público."""
    context = {
        'title': 'Proceso de Inscripción',
    }
    if request.method == 'POST':
        folio = request.POST.get('folio', '').strip()
        solicitud = _get_solicitud_by_folio(folio)
        if not solicitud:
            messages.error(request, 'Folio no encontrado. Verifique su número.')
            return render(request, 'datos_academicos/inscripcion_publico/inicio.html', context)
        if not _estado_habilitado(solicitud.estado):
            messages.error(request, 'Su solicitud todavía no está habilitada para inscripción.')
            return render(request, 'datos_academicos/inscripcion_publico/inicio.html', context)
        # Crear o recuperar inscripción y redirigir al paso 1
        _get_or_create_inscripcion_publico(request, solicitud)
        return redirect('datos_academicos:inscripcion_publico_paso', folio=solicitud.folio, paso=1)

    return render(request, 'datos_academicos/inscripcion_publico/inicio.html', context)


def inscripcion_publico_paso(request, folio: str, paso: int):
    solicitud = _get_solicitud_by_folio(folio)
    if not solicitud:
        messages.error(request, 'Folio no válido.')
        return redirect('datos_academicos:inscripcion_publico_inicio')
    if not _estado_habilitado(solicitud.estado):
        messages.error(request, 'Su solicitud todavía no está habilitada para inscripción.')
        return redirect('datos_academicos:inscripcion_publico_inicio')

    if paso not in STEPS:
        messages.error(request, 'Paso inválido')
        return redirect('datos_academicos:inscripcion_publico_paso', folio=solicitud.folio, paso=1)

    inscripcion = _get_or_create_inscripcion_publico(request, solicitud)
    step_conf = STEPS[paso]

    # Preparar contexto base
    context = {
        'solicitud': solicitud,
        'inscripcion': inscripcion,
        'paso': paso,
        'steps': STEPS,
        'paso_nombre': step_conf['name'],
        'title': f'Inscripción - Paso {paso}: {step_conf["name"]}'
    }

    if request.method == 'POST':
        accion = request.POST.get('accion', 'guardar')
        if paso in (1, 2):
            form = step_conf['form'](request.POST, request.FILES, instance=inscripcion)
            if form.is_valid():
                form.save()
                next_paso = paso + 1
                return redirect('datos_academicos:inscripcion_publico_paso', folio=solicitud.folio, paso=next_paso)
            context['form'] = form
        elif paso == 3:
            form = step_conf['form'](request.POST, request.FILES)
            if form.is_valid():
                created = 0
                with transaction.atomic():
                    for code, _label in DocumentoInscripcionNueva.TIPO_CHOICES:
                        files = request.FILES.getlist(f'archivo_{code}')
                        notas = request.POST.get(f'nota_{code}', '')
                        for f in files:
                            DocumentoInscripcionNueva.objects.create(
                                inscripcion=inscripcion,
                                tipo=code,
                                archivo=f,
                                notas=notas or ''
                            )
                            created += 1
                if created > 0:
                    messages.success(request, f'{created} documento(s) cargado(s)')
                else:
                    messages.info(request, 'No se adjuntó ningún archivo.')
                if accion == 'continuar':
                    return redirect('datos_academicos:inscripcion_publico_paso', folio=solicitud.folio, paso=4)
                return redirect('datos_academicos:inscripcion_publico_paso', folio=solicitud.folio, paso=3)
            context['form'] = form
        elif paso == 4:
            _ensure_pago_conceptos(inscripcion)
            queryset = PagoInscripcionConcepto.objects.filter(inscripcion=inscripcion).order_by('concepto')
            formset = PagoConceptoFormSet(request.POST, request.FILES, queryset=queryset)
            if formset.is_valid():
                formset.save()
                messages.success(request, 'Pagos actualizados correctamente.')
                if accion == 'continuar':
                    return redirect('datos_academicos:inscripcion_publico_resumen', folio=solicitud.folio)
                return redirect('datos_academicos:inscripcion_publico_paso', folio=solicitud.folio, paso=4)
            context['formset'] = formset
        else:
            context['form'] = step_conf['form']()
    else:
        if paso in (1, 2):
            context['form'] = step_conf['form'](instance=inscripcion)
        elif paso == 3:
            context['form'] = step_conf['form']()
            # Pasar documentos existentes y checklist amigable
            docs = DocumentoInscripcionNueva.objects.filter(inscripcion=inscripcion)
            docs_por_tipo = {t[0]: [] for t in DocumentoInscripcionNueva.TIPO_CHOICES}
            for d in docs:
                docs_por_tipo.setdefault(d.tipo, []).append(d)
            # Armamos una lista (codigo, etiqueta, lista_docs) para fácil render en plantilla
            required_docs = DocumentoInscripcionNueva.TIPO_CHOICES
            docs_checklist = []
            for code, label in required_docs:
                docs_checklist.append((code, label, docs_por_tipo.get(code, [])))
            context['docs_por_tipo'] = docs_por_tipo
            context['required_docs'] = required_docs
            context['docs_checklist'] = docs_checklist
        elif paso == 4:
            _ensure_pago_conceptos(inscripcion)
            queryset = PagoInscripcionConcepto.objects.filter(inscripcion=inscripcion).order_by('concepto')
            context['formset'] = PagoConceptoFormSet(queryset=queryset)
        else:
            context['form'] = step_conf['form']()

    return render(request, 'datos_academicos/inscripcion_publico/paso.html', context)


def inscripcion_publico_resumen(request, folio: str):
    solicitud = _get_solicitud_by_folio(folio)
    if not solicitud:
        messages.error(request, 'Folio no válido.')
        return redirect('datos_academicos:inscripcion_publico_inicio')
    inscripcion = _get_or_create_inscripcion_publico(request, solicitud)

    if request.method == 'POST':
        # Enviar para revisión
        inscripcion.estado = 'Enviado'
        inscripcion.save()
        return redirect('datos_academicos:inscripcion_publico_confirmacion', folio=inscripcion.folio)

    context = {
        'solicitud': solicitud,
        'inscripcion': inscripcion,
        'title': 'Revisar y enviar inscripción'
    }
    return render(request, 'datos_academicos/inscripcion_publico/resumen.html', context)


def inscripcion_publico_confirmacion(request, folio: str):
    inscripcion = get_object_or_404(InscripcionNueva, folio=folio)
    context = {
        'inscripcion': inscripcion,
        'title': 'Inscripción enviada'
    }
    return render(request, 'datos_academicos/inscripcion_publico/confirmacion.html', context)