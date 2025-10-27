from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from .models_inscripcion_nueva import InscripcionNueva, DocumentoInscripcionNueva
from .forms_inscripcion_nueva import (
    Paso1AspiranteForm,
    Paso2ProgramaForm,
    Paso3DocumentosForm,
    Paso4PagoForm,
)


STEPS = {
    1: {'name': 'Aspirante', 'form': Paso1AspiranteForm},
    2: {'name': 'Programa', 'form': Paso2ProgramaForm},
    3: {'name': 'Documentos', 'form': Paso3DocumentosForm},
    4: {'name': 'Pago', 'form': Paso4PagoForm},
}


def _get_or_create_inscripcion(request):
    ins_id = request.session.get('ins_nueva_id')
    if ins_id:
        return get_object_or_404(InscripcionNueva, id=ins_id)
    ins = InscripcionNueva.objects.create(creado_por=request.user if request.user.is_authenticated else None)
    request.session['ins_nueva_id'] = ins.id
    return ins


def _is_admin_user(user):
    return user.is_staff or user.is_superuser or user.groups.filter(name__in=['ServiciosEscolares', 'Servicios Escolares']).exists()


@login_required
def inicio(request):
    # Admin-only guard
    if not _is_admin_user(request.user):
        messages.error(request, 'Acceso restringido: solo personal administrativo.')
        return redirect('datos_academicos:servicios_login')
    ins = _get_or_create_inscripcion(request)
    return redirect('datos_academicos:inscripcion_nueva_paso', paso=1)


@login_required
def paso(request, paso: int):
    # Admin-only guard
    if not _is_admin_user(request.user):
        messages.error(request, 'Acceso restringido: solo personal administrativo.')
        return redirect('datos_academicos:servicios_login')
    if paso not in STEPS:
        messages.error(request, 'Paso inválido')
        return redirect('datos_academicos:inscripcion_nueva_paso', paso=1)

    inscripcion = _get_or_create_inscripcion(request)

    step_conf = STEPS[paso]

    if request.method == 'POST':
        if paso in (1, 2, 4):
            form = step_conf['form'](request.POST, request.FILES, instance=inscripcion)
            if form.is_valid():
                form.save()
                next_paso = paso + 1 if paso < max(STEPS.keys()) else 'resumen'
                if next_paso == 'resumen':
                    return redirect('datos_academicos:inscripcion_nueva_resumen')
                return redirect('datos_academicos:inscripcion_nueva_paso', paso=next_paso)
        elif paso == 3:
            form = step_conf['form'](request.POST, request.FILES)
            if form.is_valid():
                tipo = form.cleaned_data['tipo']
                notas = form.cleaned_data.get('notas')
                archivos = request.FILES.getlist('archivos')
                created = 0
                with transaction.atomic():
                    for f in archivos:
                        DocumentoInscripcionNueva.objects.create(
                            inscripcion=inscripcion,
                            tipo=tipo,
                            archivo=f,
                            notas=notas or ''
                        )
                        created += 1
                messages.success(request, f'{created} documento(s) cargado(s)')
                return redirect('datos_academicos:inscripcion_nueva_paso', paso=3)
        else:
            form = step_conf['form']()
    else:
        if paso in (1, 2, 4):
            form = step_conf['form'](instance=inscripcion)
        else:
            form = step_conf['form']()

    context = {
        'inscripcion': inscripcion,
        'form': form,
        'paso': paso,
        'steps': STEPS,
        'paso_nombre': step_conf["name"],
        'title': f'Inscripción (Nuevo) - Paso {paso}: {step_conf["name"]}'
    }
    return render(request, 'datos_academicos/inscripcion_nueva/paso.html', context)


@login_required
def resumen(request):
    # Admin-only guard
    if not _is_admin_user(request.user):
        messages.error(request, 'Acceso restringido: solo personal administrativo.')
        return redirect('datos_academicos:servicios_login')
    inscripcion = _get_or_create_inscripcion(request)

    if request.method == 'POST':
        inscripcion.estado = 'Enviado'
        inscripcion.save(update_fields=['estado'])
        messages.success(request, f'Inscripción {inscripcion.folio} enviada para revisión')
        # Limpiar sesión del flujo
        try:
            del request.session['ins_nueva_id']
        except KeyError:
            pass
        return redirect('datos_academicos:inscripcion_nueva_confirmacion', folio=inscripcion.folio)

    context = {
        'inscripcion': inscripcion,
        'title': 'Revisión y envío de inscripción'
    }
    return render(request, 'datos_academicos/inscripcion_nueva/resumen.html', context)


@login_required
def confirmacion(request, folio: str):
    # Admin-only guard
    if not _is_admin_user(request.user):
        messages.error(request, 'Acceso restringido: solo personal administrativo.')
        return redirect('datos_academicos:servicios_login')
    inscripcion = get_object_or_404(InscripcionNueva, folio=folio)
    context = {
        'inscripcion': inscripcion,
        'title': 'Inscripción enviada'
    }
    return render(request, 'datos_academicos/inscripcion_nueva/confirmacion.html', context)