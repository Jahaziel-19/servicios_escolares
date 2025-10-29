from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count
from django.utils import timezone
from datetime import datetime

from .models import PeriodoEscolar, Alumno
from servicios_escolares.forms import PeriodoEscolarForm
from admision.models import PeriodoAdmision

# Permiso: usuarios de Servicios Escolares (staff/superuser o grupo "ServiciosEscolares"/"Servicios Escolares")
def _es_servicios_escolares(user):
    return user.is_authenticated and (
        user.is_staff or user.is_superuser or user.groups.filter(name__in=["ServiciosEscolares", "Servicios Escolares"]).exists()
    )

servicios_escolares_required = user_passes_test(
    _es_servicios_escolares,
    login_url='/datos_academicos/servicios/login/'
)

@servicios_escolares_required
def periodos_listar(request):
    periodos = PeriodoEscolar.objects.all().order_by('-fecha_inicio')
    return render(request, 'datos_academicos/periodos/lista.html', {'periodos': periodos})

@servicios_escolares_required
def periodo_editar(request, periodo_id=None):
    periodo = None
    if periodo_id:
        periodo = get_object_or_404(PeriodoEscolar, id=periodo_id)

    if request.method == 'POST':
        form = PeriodoEscolarForm(request.POST, instance=periodo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Periodo guardado correctamente.')
            return redirect('datos_academicos:periodos_listar')
    else:
        form = PeriodoEscolarForm(instance=periodo)

    return render(request, 'datos_academicos/periodos/form.html', {'form': form, 'periodo': periodo})

@servicios_escolares_required
def periodo_toggle_activo(request, periodo_id):
    periodo = get_object_or_404(PeriodoEscolar, id=periodo_id)
    periodo.activo = not periodo.activo
    periodo.save()
    messages.info(request, f'Periodo {"activado" if periodo.activo else "desactivado"}.')
    return redirect('datos_academicos:periodos_listar')

@servicios_escolares_required
def periodos_panel(request):
    """Vista principal del panel de periodos con tabs y estadísticas"""
    
    # Obtener todos los periodos
    periodos = PeriodoEscolar.objects.all().order_by('-fecha_inicio')
    
    # Obtener periodos de admisión
    periodos_admision = PeriodoAdmision.objects.all().order_by('-fecha_inicio')
    
    # Calcular estadísticas
    current_year = datetime.now().year
    stats = {
        'total_periodos': periodos.count(),
        'activos': periodos.filter(activo=True).count(),
        'admision_abiertos': periodos_admision.filter(activo=True).count(),
        'este_año': periodos.filter(año=current_year).count(),
    }
    
    # Obtener años disponibles para filtros
    años_disponibles = periodos.values_list('año', flat=True).distinct().order_by('-año')
    
    # Manejar creación de nuevo periodo
    if request.method == 'POST':
        form = PeriodoEscolarForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Periodo creado correctamente.')
            return redirect('datos_academicos:periodos_panel')
        else:
            messages.error(request, 'Error al crear el periodo. Revisa los datos.')
    else:
        form = PeriodoEscolarForm()
    
    context = {
        'periodos': periodos,
        'periodos_admision': periodos_admision,
        'stats': stats,
        'años_disponibles': años_disponibles,
        'current_year': current_year,
        'form': form,
        'theme_name': 'servicios',
    }
    
    return render(request, 'datos_academicos/periodos/panel.html', context)

@servicios_escolares_required
def periodo_aplicar_transicion(request):
    """Transición automática: marcar alumnos como 'No Inscrito' al finalizar periodo."""
    hoy = timezone.now().date()
    afectados = Alumno.objects.filter(fin_semestre__isnull=False, fin_semestre__lte=hoy, estatus='Inscrito')
    count = afectados.update(estatus='No Inscrito')
    messages.success(request, f'Transición aplicada: {count} alumnos marcados como No Inscrito.')
    return redirect('datos_academicos:periodos_listar')