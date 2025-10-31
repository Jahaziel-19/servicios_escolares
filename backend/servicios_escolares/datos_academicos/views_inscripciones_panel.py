from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone

from admision.email_utils import send_email_safe

from .models_inscripcion_simple import InscripcionSimple
# Reinscripción eliminada del sistema
from .models import PeriodoEscolar, Alumno
from datetime import date
from .models_inscripcion_nueva import InscripcionNueva, PagoInscripcionConcepto, DocumentoInscripcionNueva


def _is_admin_user(user):
    """Permite acceso a staff, superusuarios o grupo ServiciosEscolares."""
    try:
        return (
            user.is_staff
            or user.is_superuser
            or user.groups.filter(name__in=["ServiciosEscolares", "Servicios Escolares"]).exists()
        )
    except Exception:
        return False


@login_required
def inscripciones_panel_admin(request):
    """Panel administrativo de inscripciones con estilo de Admisión."""
    if not _is_admin_user(request.user):
        messages.error(request, "Acceso restringido: solo personal administrativo.")
        return redirect("datos_academicos:servicios_login")

    # Stats Inscripción Simple
    stats_simple = {
        "total": InscripcionSimple.objects.count(),
        "pendientes": InscripcionSimple.objects.filter(estado="Pendiente").count(),
        "aprobadas": InscripcionSimple.objects.filter(estado="Aprobada").count(),
        "rechazadas": InscripcionSimple.objects.filter(estado="Rechazada").count(),
    }
    recientes_simple = InscripcionSimple.objects.order_by("-fecha_solicitud")[:5]

    # Reinscripción removida: limpiar estadísticas y recientes
    stats_reins = None
    recientes_reins = []

    # Stats Inscripción Nueva (públicas)
    stats_nueva = {
        "total": InscripcionNueva.objects.count(),
        "borrador": InscripcionNueva.objects.filter(estado="Borrador").count(),
        "enviadas": InscripcionNueva.objects.filter(estado="Enviado").count(),
        "revision": InscripcionNueva.objects.filter(estado="En Revisión").count(),
        "aprobadas": InscripcionNueva.objects.filter(estado="Aprobada").count(),
        "rechazadas": InscripcionNueva.objects.filter(estado="Rechazada").count(),
        "completadas": InscripcionNueva.objects.filter(estado="Completada").count(),
    }
    recientes_nueva = InscripcionNueva.objects.select_related("carrera_solicitada", "periodo_escolar").order_by("-creado_en")[:5]

    periodo_activo = PeriodoEscolar.objects.filter(activo=True).first()

    context = {
        "title": "Panel de Inscripciones",
        "periodo_activo": periodo_activo,
        "stats_simple": stats_simple,
        "recientes_simple": recientes_simple,
        # Se removieron estadísticas y recientes de Reinscripción
        "stats_nueva": stats_nueva,
        "recientes_nueva": recientes_nueva,
        "estados_nueva_choices": InscripcionNueva.ESTADO_CHOICES,
    }
    return render(request, "datos_academicos/inscripciones/panel_admin.html", context)


@login_required
def inscripciones_publicas_listar(request):
    """Listado de InscripcionNueva (públicas) para administración."""
    if not _is_admin_user(request.user):
        messages.error(request, "Acceso restringido: solo personal administrativo.")
        return redirect("datos_academicos:servicios_login")

    estado = request.GET.get("estado")
    q = request.GET.get("q", "").strip()

    qs = InscripcionNueva.objects.select_related("carrera_solicitada", "periodo_escolar")
    if estado:
        qs = qs.filter(estado=estado)
    if q:
        qs = qs.filter(nombre__icontains=q) | qs.filter(apellido_paterno__icontains=q) | qs.filter(apellido_materno__icontains=q) | qs.filter(folio__icontains=q)

    qs = qs.order_by("-creado_en")

    # Paginación
    from django.core.paginator import Paginator
    page_number = request.GET.get("page", 1)
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(page_number)

    estados_choices = [c[0] for c in InscripcionNueva.ESTADO_CHOICES]
    conteos = {e: InscripcionNueva.objects.filter(estado=e).count() for e in estados_choices}

    context = {
        "title": "Inscripciones públicas",
        "inscripciones": page_obj,
        "paginator": paginator,
        "page_obj": page_obj,
        "total": paginator.count,
        "estado": estado,
        "q": q,
        "conteos": conteos,
    }
    return render(request, "datos_academicos/inscripcion_publica_list.html", context)


@login_required
def inscripcion_publica_detalle(request, pk):
    """Detalle de una InscripcionNueva, con gestión de estado y pagos por concepto."""
    if not _is_admin_user(request.user):
        messages.error(request, "Acceso restringido: solo personal administrativo.")
        return redirect("datos_academicos:servicios_login")

    ins = get_object_or_404(InscripcionNueva, pk=pk)
    pagos = list(ins.pagos.all())
    documentos = list(ins.documentos.all())

    if request.method == "POST":
        try:
            with transaction.atomic():
                # Actualizar estado y observaciones de la inscripción
                estado_anterior = ins.estado
                nuevo_estado = request.POST.get("estado")
                observaciones = request.POST.get("observaciones", "")
                if nuevo_estado in dict(InscripcionNueva.ESTADO_CHOICES):
                    ins.estado = nuevo_estado
                ins.observaciones = observaciones
                ins.save()

                # Actualizar pagos por concepto
                for p in pagos:
                    prefix = f"pago-{p.id}-"
                    p_estado = request.POST.get(prefix + "estado", p.estado)
                    p_monto = request.POST.get(prefix + "monto", None)
                    p_notas = request.POST.get(prefix + "notas", "")
                    p_file = request.FILES.get(prefix + "comprobante", None)

                    if p_estado in dict(PagoInscripcionConcepto.ESTADO_CHOICES):
                        p.estado = p_estado
                    if p_monto not in (None, ""):
                        try:
                            p.monto = float(p_monto)
                        except Exception:
                            pass
                    p.notas = p_notas
                    if p_file:
                        p.comprobante = p_file
                    p.save()

                # Envío de correo si se rechaza, usando observaciones como motivo
                if nuevo_estado == "Rechazada" and ins.email:
                    try:
                        subject = f"Inscripción Pública Rechazada - Folio {ins.folio}"
                        motivo = observaciones.strip() or "Sin motivo especificado."
                        institucion = getattr(settings, 'INSTITUCION_NOMBRE', 'Institución Educativa')
                        html_content = (
                            f"<p>Estimado(a) {ins.nombre} {ins.apellido_paterno},</p>"
                            f"<p>Su inscripción con folio <strong>{ins.folio}</strong> ha sido <strong>rechazada</strong>.</p>"
                            f"<p><strong>Motivo:</strong> {motivo}</p>"
                            f"<p>Si tiene dudas, responda a este correo o contacte a servicios escolares.</p>"
                            f"<p>Atentamente,<br>{institucion}</p>"
                        )
                        text_content = (
                            f"Estimado(a) {ins.nombre} {ins.apellido_paterno},\n"
                            f"Su inscripción con folio {ins.folio} ha sido rechazada.\n"
                            f"Motivo: {motivo}\n\n"
                            f"Si tiene dudas, contacte a servicios escolares.\n"
                            f"Atentamente, {institucion}"
                        )
                        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tecnm.mx')
                        email = EmailMultiAlternatives(subject, text_content, from_email, [ins.email])
                        email.attach_alternative(html_content, "text/html")
                        send_email_safe(email)
                        messages.info(request, "Correo de rechazo enviado al aspirante.")
                    except Exception:
                        messages.warning(request, "No fue posible enviar el correo de rechazo.")

                # Crear Alumno si se marca Completada
                if nuevo_estado == "Completada":
                    try:
                        if not ins.carrera_solicitada:
                            raise Exception("La inscripción no tiene una carrera seleccionada.")

                        periodo = ins.periodo_escolar or PeriodoEscolar.objects.filter(activo=True).first()
                        año = str(periodo.año)[-2:] if periodo else str(date.today().year)[-2:]

                        # Mapeo de claves de carrera (consistente con InscripcionSimple)
                        clave_carrera_map = {
                            'INGENIERÍA EN ELECTROMECÁNICA': '01',
                            'INGENIERÍA EN GESTIÓN EMPRESARIAL': '02',
                            'INGENIERÍA LOGÍSTICA': '03',
                            'INGENIERÍA EN MATERIALES': '04',
                            'INGENIERÍA QUÍMICA': '05',
                        }
                        carrera_nombre = (ins.carrera_solicitada.nombre or '').upper()
                        clave_carrera = clave_carrera_map.get(carrera_nombre, '00')
                        prefijo = f"{año}{clave_carrera}"

                        ultimo = Alumno.objects.filter(matricula__startswith=prefijo).order_by('-matricula').first()
                        if ultimo and ultimo.matricula:
                            try:
                                consecutivo = int(ultimo.matricula[-3:]) + 1
                            except Exception:
                                consecutivo = 1
                        else:
                            consecutivo = 1
                        matricula = f"{prefijo}{consecutivo:03d}"

                        # Mapear modalidad libre a código A/B
                        mod_raw = (ins.modalidad or '').upper()
                        modalidad = 'B' if 'SABAT' in mod_raw else 'A'

                        alumno = Alumno.objects.create(
                            matricula=matricula,
                            nombre=ins.nombre,
                            apellido_paterno=ins.apellido_paterno,
                            apellido_materno=ins.apellido_materno,
                            carrera=ins.carrera_solicitada,
                            semestre=1,
                            modalidad=modalidad,
                            plan_estudio=getattr(ins.carrera_solicitada, 'plan_estudio', None),
                            fecha_ingreso=date.today(),
                            estatus='Inscrito',
                            division_estudio='Nuevo Ingreso',
                            curp=ins.curp,
                            email=ins.email,
                            fecha_nacimiento=ins.fecha_nacimiento,
                            telefono=ins.telefono,
                        )
                        messages.success(request, f"Alumno creado con matrícula {alumno.matricula}. Inscripción marcada como Completada.")
                    except Exception as e:
                        messages.error(request, f"No se pudo crear el alumno: {e}")

                messages.success(request, "Inscripción y pagos actualizados correctamente.")
                # Si es AJAX, responder JSON compacto para que el cliente cierre modal y recargue
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    from django.http import JsonResponse
                    return JsonResponse({"ok": True})
                return redirect("datos_academicos:inscripcion_publica_detalle", pk=ins.pk)
        except Exception as e:
            messages.error(request, f"Error al guardar cambios: {e}")

    context = {
        "title": f"Inscripción pública {ins.folio}",
        "inscripcion": ins,
        "pagos": pagos,
        "documentos": documentos,
        "estados": InscripcionNueva.ESTADO_CHOICES,
        "estados_pagos": PagoInscripcionConcepto.ESTADO_CHOICES,
    }
    # Si es AJAX, entregar parcial
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "datos_academicos/inscripciones/_detalle_form.html", context)
    return render(request, "datos_academicos/inscripcion_publica_detalle.html", context)