from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models_inscripcion import Reinscripcion
from .models import PeriodoEscolar


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
def reinscripciones_listar(request):
    """Lista de reinscripciones con filtros y estadísticas básicas."""
    if not _is_admin_user(request.user):
        messages.error(request, "Acceso restringido: solo personal administrativo.")
        return redirect("datos_academicos:servicios_login")

    estado = (request.GET.get("estado") or "").strip()
    periodo_id = (request.GET.get("periodo") or "").strip()

    queryset = (
        Reinscripcion.objects.select_related("alumno", "periodo_escolar").order_by("-fecha_solicitud")
    )

    if estado:
        queryset = queryset.filter(estado=estado)
    if periodo_id:
        try:
            queryset = queryset.filter(periodo_escolar_id=int(periodo_id))
        except ValueError:
            pass

    reinscripciones = list(queryset[:50])

    estados_choices = getattr(
        Reinscripcion, "ESTADO_CHOICES", Reinscripcion._meta.get_field("estado").choices
    )

    try:
        periodos = PeriodoEscolar.objects.all().order_by("-año", "ciclo")
    except Exception:
        periodos = PeriodoEscolar.objects.all()

    stats = {
        "total": Reinscripcion.objects.count(),
        "pendientes": Reinscripcion.objects.filter(estado="Pendiente").count(),
        "aprobadas": Reinscripcion.objects.filter(estado="Aprobada").count(),
        "completadas": Reinscripcion.objects.filter(estado="Completada").count(),
        "rechazadas": Reinscripcion.objects.filter(estado="Rechazada").count(),
    }

    context = {
        "title": "Gestión de Reinscripciones",
        "reinscripciones": reinscripciones,
        "stats": stats,
        "estados_choices": estados_choices,
        "estado_filtro": estado,
        "periodos": periodos,
        "periodo_filtro": periodo_id,
    }
    return render(request, "datos_academicos/reinscripciones/reinscripcion_list.html", context)


@login_required
def reinscripcion_detalle(request, pk: int):
    """Detalle de una reinscripción."""
    if not _is_admin_user(request.user):
        messages.error(request, "Acceso restringido: solo personal administrativo.")
        return redirect("datos_academicos:servicios_login")

    reinscripcion = get_object_or_404(
        Reinscripcion.objects.select_related("alumno", "periodo_escolar"), id=pk
    )

    context = {
        "title": f"Reinscripción {getattr(reinscripcion, 'folio', reinscripcion.id)}",
        "reinscripcion": reinscripcion,
    }
    return render(request, "datos_academicos/reinscripciones/reinscripcion_detail.html", context)