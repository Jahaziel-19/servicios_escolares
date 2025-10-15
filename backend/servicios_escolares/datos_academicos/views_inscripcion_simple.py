from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
import json

from .models_inscripcion_simple import InscripcionSimple
from .forms_inscripcion_simple import InscripcionSimpleForm, BusquedaInscripcionForm
from .models import Carrera, PeriodoEscolar


@login_required
def inscripcion_simple_view(request):
    """
    Vista principal para el formulario de inscripción simple
    """
    if request.method == 'POST':
        form = InscripcionSimpleForm(request.POST)
        
        if form.is_valid():
            try:
                inscripcion = form.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Inscripción registrada correctamente',
                    'folio': inscripcion.folio,
                    'id': inscripcion.id
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error al guardar la inscripción: {str(e)}'
                })
        else:
            # Retornar errores de validación
            errors = {}
            for field, field_errors in form.errors.items():
                errors[field] = field_errors[0] if field_errors else ''
            
            return JsonResponse({
                'success': False,
                'message': 'Por favor corrija los errores en el formulario',
                'errors': errors
            })
    
    else:
        form = InscripcionSimpleForm()
    
    # Obtener carreras activas para el template
    carreras = Carrera.objects.all().order_by('nombre')
    
    context = {
        'form': form,
        'carreras': carreras,
        'title': 'Inscripción Simple'
    }
    
    return render(request, 'datos_academicos/inscripcion_simple.html', context)


@login_required
def inscripcion_list_view(request):
    """
    Vista para listar inscripciones con búsqueda
    """
    form_busqueda = BusquedaInscripcionForm(request.GET or None)
    inscripciones = InscripcionSimple.objects.all().order_by('-fecha_solicitud')
    
    # Aplicar filtros de búsqueda
    if form_busqueda.is_valid():
        folio = form_busqueda.cleaned_data.get('folio')
        nombre = form_busqueda.cleaned_data.get('nombre')
        curp = form_busqueda.cleaned_data.get('curp')
        carrera = form_busqueda.cleaned_data.get('carrera')
        estado = form_busqueda.cleaned_data.get('estado')
        
        if folio:
            inscripciones = inscripciones.filter(folio__icontains=folio)
        
        if nombre:
            inscripciones = inscripciones.filter(
                Q(nombre__icontains=nombre) |
                Q(apellido_paterno__icontains=nombre) |
                Q(apellido_materno__icontains=nombre)
            )
        
        if curp:
            inscripciones = inscripciones.filter(curp__icontains=curp)
        
        if carrera:
            inscripciones = inscripciones.filter(carrera_solicitada=carrera)
        
        if estado:
            inscripciones = inscripciones.filter(estado=estado)
    
    # Paginación
    paginator = Paginator(inscripciones, 20)  # 20 inscripciones por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas básicas
    stats = {
        'total': inscripciones.count(),
        'pendientes': inscripciones.filter(estado='Pendiente').count(),
        'aprobadas': inscripciones.filter(estado='Aprobada').count(),
        'rechazadas': inscripciones.filter(estado='Rechazada').count(),
    }
    
    context = {
        'form_busqueda': form_busqueda,
        'page_obj': page_obj,
        'inscripciones': page_obj,
        'stats': stats,
        'title': 'Lista de Inscripciones'
    }
    
    return render(request, 'datos_academicos/inscripcion_list_simple.html', context)


@login_required
def inscripcion_detail_view(request, pk):
    """
    Vista de detalle de una inscripción
    """
    inscripcion = get_object_or_404(InscripcionSimple, pk=pk)
    
    context = {
        'inscripcion': inscripcion,
        'title': f'Inscripción {inscripcion.folio}'
    }
    
    return render(request, 'datos_academicos/inscripcion_detail_simple.html', context)


@login_required
@require_http_methods(["POST"])
def cambiar_estado_inscripcion(request, pk):
    """
    Vista para cambiar el estado de una inscripción
    """
    inscripcion = get_object_or_404(InscripcionSimple, pk=pk)
    
    try:
        data = json.loads(request.body)
        nuevo_estado = data.get('estado')
        
        if nuevo_estado not in dict(InscripcionSimple.ESTADO_CHOICES):
            return JsonResponse({
                'success': False,
                'message': 'Estado no válido'
            })
        
        estado_anterior = inscripcion.estado
        inscripcion.estado = nuevo_estado
        inscripcion.save()
        
        # Si se aprueba la inscripción, ofrecer crear alumno
        mensaje = f'Estado cambiado de "{estado_anterior}" a "{nuevo_estado}"'
        puede_crear_alumno = inscripcion.puede_crear_alumno
        
        return JsonResponse({
            'success': True,
            'message': mensaje,
            'nuevo_estado': nuevo_estado,
            'puede_crear_alumno': puede_crear_alumno
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Datos JSON inválidos'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al cambiar estado: {str(e)}'
        })


@login_required
@require_http_methods(["POST"])
def crear_alumno_desde_inscripcion(request, pk):
    """
    Vista para crear un alumno desde una inscripción aprobada
    """
    inscripcion = get_object_or_404(InscripcionSimple, pk=pk)
    
    try:
        if not inscripcion.puede_crear_alumno:
            return JsonResponse({
                'success': False,
                'message': 'La inscripción debe estar aprobada y no tener un alumno asociado'
            })
        
        # Obtener período escolar activo
        periodo_activo = PeriodoEscolar.objects.filter(activo=True).first()
        if not periodo_activo:
            return JsonResponse({
                'success': False,
                'message': 'No hay un período escolar activo'
            })
        
        # Crear el alumno
        alumno = inscripcion.crear_alumno(periodo_activo)
        
        return JsonResponse({
            'success': True,
            'message': f'Alumno creado exitosamente con matrícula: {alumno.matricula}',
            'matricula': alumno.matricula,
            'alumno_id': alumno.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al crear alumno: {str(e)}'
        })


@login_required
def dashboard_inscripciones(request):
    """
    Dashboard simple con estadísticas de inscripciones
    """
    import json
    from datetime import datetime, timedelta
    
    # Estadísticas generales
    total_inscripciones = InscripcionSimple.objects.count()
    pendientes = InscripcionSimple.objects.filter(estado='Pendiente').count()
    aprobadas = InscripcionSimple.objects.filter(estado='Aprobada').count()
    rechazadas = InscripcionSimple.objects.filter(estado='Rechazada').count()
    
    # Estadísticas adicionales
    hoy = datetime.now().date()
    esta_semana = hoy - timedelta(days=7)
    este_mes = hoy - timedelta(days=30)
    
    hoy_count = InscripcionSimple.objects.filter(fecha_solicitud__date=hoy).count()
    semana_count = InscripcionSimple.objects.filter(fecha_solicitud__date__gte=esta_semana).count()
    mes_count = InscripcionSimple.objects.filter(fecha_solicitud__date__gte=este_mes).count()
    
    # Inscripciones recientes (últimas 10)
    inscripciones_recientes = InscripcionSimple.objects.order_by('-fecha_solicitud')[:10]
    
    # Inscripciones por carrera
    from django.db.models import Count
    inscripciones_por_carrera = InscripcionSimple.objects.values(
        'carrera_solicitada__nombre'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:5]
    
    # Inscripciones por modalidad
    inscripciones_por_modalidad = InscripcionSimple.objects.values(
        'modalidad'
    ).annotate(
        total=Count('id')
    )
    
    # Preparar datos para gráficos
    stats_data = {
        'total': total_inscripciones,
        'pendientes': pendientes,
        'aprobadas': aprobadas,
        'rechazadas': rechazadas,
        'hoy': hoy_count,
        'esta_semana': semana_count,
        'este_mes': mes_count,
        'alumnos_creados': total_inscripciones,  # Por simplicidad, usamos el mismo valor
        'por_carrera': list(inscripciones_por_carrera),
        'por_modalidad': list(inscripciones_por_modalidad),
        'tendencia_mensual': []  # Vacío por ahora
    }
    
    context = {
        'stats': stats_data,
        'stats_json': json.dumps(stats_data),
        'inscripciones_recientes': inscripciones_recientes,
        'inscripciones_por_carrera': inscripciones_por_carrera,
        'inscripciones_por_modalidad': inscripciones_por_modalidad,
        'title': 'Dashboard de Inscripciones'
    }
    
    return render(request, 'datos_academicos/dashboard_inscripciones.html', context)


# Vistas basadas en clases (alternativas)
class InscripcionListView(ListView):
    """
    Vista de lista basada en clase (alternativa)
    """
    model = InscripcionSimple
    template_name = 'datos_academicos/inscripcion_list_simple.html'
    context_object_name = 'inscripciones'
    paginate_by = 20
    ordering = ['-fecha_solicitud']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Lista de Inscripciones'
        context['form_busqueda'] = BusquedaInscripcionForm()
        return context


class InscripcionDetailView(DetailView):
    """
    Vista de detalle basada en clase (alternativa)
    """
    model = InscripcionSimple
    template_name = 'datos_academicos/inscripcion_detail_simple.html'
    context_object_name = 'inscripcion'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Inscripción {self.object.folio}'
        return context