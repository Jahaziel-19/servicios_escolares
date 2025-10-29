from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from django.contrib import messages

from .models_inscripcion import Reinscripcion, ReinscripcionLog, CargaAcademica, CargaAcademicaItem, ReinscripcionPago
from .models import Alumno, PeriodoEscolar, Materia, Carrera, MateriaCarrera


def _is_admin_user(user):
    return (
        user.is_authenticated and (
            user.is_staff or user.is_superuser or user.groups.filter(name__in=['ServiciosEscolares', 'Servicios Escolares']).exists()
        )
    )


@login_required
def reinscripcion_panel(request):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden('Acceso restringido')

    periodo_activo = PeriodoEscolar.objects.filter(activo=True).first()
    reinscripciones = Reinscripcion.objects.filter(periodo_escolar=periodo_activo) if periodo_activo else []

    context = {
        'periodo_activo': periodo_activo,
        'reinscripciones': reinscripciones,
    }
    return render(request, 'datos_academicos/reinscripcion/panel.html', context)


@login_required
def reinscripcion_iniciar(request, alumno_id):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden('Acceso restringido')
    alumno = get_object_or_404(Alumno, id=alumno_id)
    periodo_activo = PeriodoEscolar.objects.filter(activo=True).first()
    if not periodo_activo or not periodo_activo.reinscripcion_habilitada:
        return JsonResponse({'ok': False, 'error': 'Reinscripción no habilitada para el periodo actual.'}, status=400)

    reins, created = Reinscripcion.objects.get_or_create(
        alumno=alumno, periodo_escolar=periodo_activo,
        defaults={'usuario_registro': request.user}
    )
    if created:
        ReinscripcionLog.objects.create(
            reinscripcion=reins,
            alumno=alumno,
            usuario=request.user,
            accion='Crear',
            detalles='Reinscripción iniciada.'
        )
    return redirect('datos_academicos:reinscripcion_detalle', reins_id=reins.id)


@login_required
def reinscripcion_iniciar_form(request):
    """Flujo alternativo: iniciar reinscripción mediante formulario.
    Acepta `alumno_id` (oculto desde el buscador) o `q` (matrícula exacta).
    """
    if not _is_admin_user(request.user):
        return HttpResponseForbidden('Acceso restringido')

    q = (request.POST.get('q') or request.GET.get('q') or '').strip()
    alumno_id = request.POST.get('alumno_id') or request.GET.get('alumno_id')

    alumno = None
    if alumno_id and str(alumno_id).isdigit():
        alumno = get_object_or_404(Alumno, id=int(alumno_id))
    elif q:
        alumno = Alumno.objects.filter(matricula__iexact=q).first()

    if not alumno:
        messages.error(request, 'No se encontró alumno. Selecciona desde el buscador o ingresa matrícula exacta.')
        return redirect('datos_academicos:reinscripcion_panel')

    return redirect('datos_academicos:reinscripcion_iniciar', alumno_id=alumno.id)


@login_required
def reinscripcion_detalle(request, reins_id):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden('Acceso restringido')
    reins = get_object_or_404(Reinscripcion, id=reins_id)
    carga = CargaAcademica.objects.filter(alumno=reins.alumno, periodo_escolar=reins.periodo_escolar).first()

    items = CargaAcademicaItem.objects.filter(carga=carga) if carga else []
    # Materias disponibles para asignación manual (siguiente semestre)
    # Usar la relación through MateriaCarrera, ya que Materia no tiene campos 'semestre' ni 'carrera' directos
    siguiente_semestre = (reins.alumno.semestre or 0) + 1
    materias_disponibles = Materia.objects.filter(
        materiacarrera__carrera=reins.alumno.carrera,
        materiacarrera__semestre=siguiente_semestre
    ).order_by('clave')
    context = {
        'reins': reins,
        'carga': carga,
        'items': items,
        'materias_disponibles': materias_disponibles,
    }
    return render(request, 'datos_academicos/reinscripcion/detalle.html', context)


@login_required
@require_http_methods(["POST"])
def reinscripcion_validar_documentos(request, reins_id):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden('Acceso restringido')
    reins = get_object_or_404(Reinscripcion, id=reins_id)
    reins.marcar_documentos_validados(request.user)
    ReinscripcionLog.objects.create(
        reinscripcion=reins,
        alumno=reins.alumno,
        usuario=request.user,
        accion='ValidarDocumentos',
        detalles='Documentos validados por servicios escolares.'
    )
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(["POST"])
def reinscripcion_validar_pagos(request, reins_id):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden('Acceso restringido')
    reins = get_object_or_404(Reinscripcion, id=reins_id)
    reins.marcar_pagos_validados(request.user)
    ReinscripcionLog.objects.create(
        reinscripcion=reins,
        alumno=reins.alumno,
        usuario=request.user,
        accion='ValidarPagos',
        detalles='Pagos validados contra comprobantes.'
    )
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(["POST"]) 
@transaction.atomic
def reinscripcion_asignar_materias(request, reins_id):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden('Acceso restringido')
    reins = get_object_or_404(Reinscripcion, id=reins_id)
    alumno = reins.alumno
    periodo = reins.periodo_escolar

    carga, _ = CargaAcademica.objects.get_or_create(
        alumno=alumno, periodo_escolar=periodo,
        defaults={'estado': 'Borrador'}
    )

    siguiente_semestre = (alumno.semestre or 0) + 1
    materia_ids = request.POST.getlist('materias')
    materia_clave = (request.POST.get('materia_clave') or '').strip()

    if materia_clave:
        # Buscar por clave exacta y asignar incrementalmente
        m = Materia.objects.filter(clave__iexact=materia_clave).first()
        if not m:
            return JsonResponse({'ok': False, 'error': 'Materia no encontrada por clave'}, status=400)
        obj, created = CargaAcademicaItem.objects.get_or_create(
            carga=carga,
            materia=m,
            defaults={'adelantada': False, 'semestre_asignado': siguiente_semestre}
        )
        if created:
            reins.marcar_materias_asignadas(request.user)
            ReinscripcionLog.objects.create(
                reinscripcion=reins,
                alumno=alumno,
                usuario=request.user,
                accion='AsignarMateriaPorClave',
                detalles=f"Materia {m.clave} asignada por clave."
            )
        return JsonResponse({'ok': True, 'agregadas': 1 if created else 0})
    elif materia_ids:
        # Asignación manual incremental: agregar materias seleccionadas sin borrar las existentes.
        materias = list(Materia.objects.filter(id__in=materia_ids).distinct())
        nuevos = 0
        for m in materias:
            obj, created = CargaAcademicaItem.objects.get_or_create(
                carga=carga,
                materia=m,
                defaults={'adelantada': False, 'semestre_asignado': siguiente_semestre}
            )
            if created:
                nuevos += 1

        reins.marcar_materias_asignadas(request.user)
        ReinscripcionLog.objects.create(
            reinscripcion=reins,
            alumno=alumno,
            usuario=request.user,
            accion='AsignarMaterias',
            detalles=f'{nuevos} nuevas materias agregadas (total {CargaAcademicaItem.objects.filter(carga=carga).count()}).'
        )
        return JsonResponse({'ok': True, 'agregadas': nuevos})
    else:
        # Asignación automática: reemplazar por malla del siguiente semestre de la carrera.
        materias = Materia.objects.filter(
            materiacarrera__semestre=siguiente_semestre,
            materiacarrera__carrera=alumno.carrera
        ).distinct()

        CargaAcademicaItem.objects.filter(carga=carga).delete()
        for m in materias:
            CargaAcademicaItem.objects.create(
                carga=carga, materia=m, adelantada=False, semestre_asignado=siguiente_semestre
            )

        reins.marcar_materias_asignadas(request.user)
        ReinscripcionLog.objects.create(
            reinscripcion=reins,
            alumno=alumno,
            usuario=request.user,
            accion='AsignarMateriasAuto',
            detalles=f'{len(materias)} materias asignadas automáticamente para semestre {siguiente_semestre}.'
        )
        return JsonResponse({'ok': True, 'materias': [m.nombre for m in materias]})


@login_required
@require_http_methods(["POST"]) 
@transaction.atomic
def reinscripcion_eliminar_materia_item(request, reins_id, item_id):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden('Acceso restringido')
    reins = get_object_or_404(Reinscripcion, id=reins_id)
    carga = CargaAcademica.objects.filter(alumno=reins.alumno, periodo_escolar=reins.periodo_escolar).first()
    if not carga:
        return JsonResponse({'ok': False, 'error': 'Carga no encontrada'}, status=404)
    item = get_object_or_404(CargaAcademicaItem, id=item_id, carga=carga)
    nombre = item.materia.nombre
    item.delete()
    ReinscripcionLog.objects.create(
        reinscripcion=reins,
        alumno=reins.alumno,
        usuario=request.user,
        accion='EliminarMateria',
        detalles=f"Materia '{nombre}' eliminada de la carga."
    )
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(["POST"])
def reinscripcion_registrar_pago(request, reins_id):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden('Acceso restringido')
    reins = get_object_or_404(Reinscripcion, id=reins_id)

    concepto = request.POST.get('concepto', '')
    monto = request.POST.get('monto')
    condonado = request.POST.get('condonado') == 'on'
    motivo = request.POST.get('motivo_condonacion', '')
    comprobante = request.FILES.get('comprobante')

    pago = ReinscripcionPago.objects.create(
        reinscripcion=reins,
        concepto=concepto,
        monto=monto or None,
        comprobante=comprobante,
        condonado=condonado,
        motivo_condonacion=motivo or None,
        usuario=request.user,
        validado=bool(condonado)  # si se condona, se considera validado por política
    )
    ReinscripcionLog.objects.create(
        reinscripcion=reins,
        alumno=reins.alumno,
        usuario=request.user,
        accion='RegistrarPago',
        detalles=f"Pago registrado: {pago.concepto} ({'Condonado' if pago.condonado else 'Adjunto'})"
    )
    return redirect('datos_academicos:reinscripcion_detalle', reins_id=reins.id)


@login_required
@require_http_methods(["POST"])
def reinscripcion_subir_carga_pdf(request, reins_id):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden('Acceso restringido')
    reins = get_object_or_404(Reinscripcion, id=reins_id)
    pdf = request.FILES.get('carga_pdf')
    if pdf:
        reins.carga_academica_pdf = pdf
        reins.usuario_ultima_accion = request.user
        reins.save()
        ReinscripcionLog.objects.create(
            reinscripcion=reins,
            alumno=reins.alumno,
            usuario=request.user,
            accion='AdjuntarPDF',
            detalles='PDF de carga académica adjuntado.'
        )
    return redirect('datos_academicos:reinscripcion_detalle', reins_id=reins.id)


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def reinscripcion_confirmar(request, reins_id):
    if not _is_admin_user(request.user):
        return HttpResponseForbidden('Acceso restringido')
    reins = get_object_or_404(Reinscripcion, id=reins_id)
    reins.confirmar(request.user)

    carga = CargaAcademica.objects.filter(alumno=reins.alumno, periodo_escolar=reins.periodo_escolar).first()
    if carga:
        carga.estado = 'Confirmada'
        carga.fecha_confirmacion = timezone.now()
        carga.confirmada_por = request.user
        carga.save()

    return JsonResponse({'ok': True})