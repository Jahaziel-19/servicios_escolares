from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from datetime import datetime

from .models import Alumno, PeriodoEscolar
from .models_inscripcion import Reinscripcion
from .forms_inscripcion import ReinscripcionForm


@login_required
def aprobar_reinscripcion(request, reinscripcion_id):
    """Vista para aprobar una reinscripción"""
    reinscripcion = get_object_or_404(Reinscripcion, id=reinscripcion_id)
    
    if request.method == 'POST':
        if reinscripcion.estado != 'Pendiente':
            return JsonResponse({
                'success': False,
                'message': 'Solo se pueden aprobar reinscripciones pendientes'
            })
        
        try:
            with transaction.atomic():
                # Cambiar estado a aprobada
                reinscripcion.estado = 'Aprobada'
                reinscripcion.fecha_aprobacion = timezone.now()
                reinscripcion.usuario_aprobacion = request.user.username
                reinscripcion.save()
                
                messages.success(request, f'Reinscripción {reinscripcion.folio} aprobada exitosamente')
                return JsonResponse({
                    'success': True,
                    'message': 'Reinscripción aprobada exitosamente'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al aprobar reinscripción: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Método no permitido'
    })


@login_required
def aplicar_reinscripcion(request, reinscripcion_id):
    """Vista para aplicar los cambios de una reinscripción aprobada"""
    reinscripcion = get_object_or_404(Reinscripcion, id=reinscripcion_id)
    
    if request.method == 'POST':
        if reinscripcion.estado != 'Aprobada':
            return JsonResponse({
                'success': False,
                'message': 'Solo se pueden aplicar reinscripciones aprobadas'
            })
        
        try:
            with transaction.atomic():
                # Aplicar cambios usando el método del modelo
                if reinscripcion.aplicar_cambios():
                    messages.success(request, f'Cambios de reinscripción {reinscripcion.folio} aplicados exitosamente')
                    return JsonResponse({
                        'success': True,
                        'message': 'Cambios aplicados exitosamente',
                        'alumno_actualizado': {
                            'matricula': reinscripcion.alumno.matricula,
                            'carrera': reinscripcion.alumno.carrera.nombre if reinscripcion.alumno.carrera else '',
                            'semestre': reinscripcion.alumno.semestre,
                            'estatus': reinscripcion.alumno.estatus,
                            'modalidad': reinscripcion.alumno.modalidad
                        }
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'No se pudieron aplicar los cambios'
                    })
                    
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al aplicar cambios: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Método no permitido'
    })


@login_required
def rechazar_reinscripcion(request, reinscripcion_id):
    """Vista para rechazar una reinscripción"""
    reinscripcion = get_object_or_404(Reinscripcion, id=reinscripcion_id)
    
    if request.method == 'POST':
        motivo_rechazo = request.POST.get('motivo_rechazo', '')
        
        if reinscripcion.estado not in ['Pendiente', 'En Revisión']:
            return JsonResponse({
                'success': False,
                'message': 'Solo se pueden rechazar reinscripciones pendientes o en revisión'
            })
        
        try:
            with transaction.atomic():
                reinscripcion.estado = 'Rechazada'
                reinscripcion.observaciones = f"{reinscripcion.observaciones or ''}\n\nMotivo de rechazo: {motivo_rechazo}".strip()
                reinscripcion.save()
                
                messages.success(request, f'Reinscripción {reinscripcion.folio} rechazada')
                return JsonResponse({
                    'success': True,
                    'message': 'Reinscripción rechazada exitosamente'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al rechazar reinscripción: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Método no permitido'
    })


@login_required
def listar_reinscripciones(request):
    """Vista para listar todas las reinscripciones"""
    estado_filtro = request.GET.get('estado', '')
    periodo_filtro = request.GET.get('periodo', '')
    
    reinscripciones = Reinscripcion.objects.select_related(
        'alumno', 'periodo_escolar', 'nueva_carrera'
    ).order_by('-fecha_solicitud')
    
    if estado_filtro:
        reinscripciones = reinscripciones.filter(estado=estado_filtro)
    
    if periodo_filtro:
        reinscripciones = reinscripciones.filter(periodo_escolar_id=periodo_filtro)
    
    # Estadísticas
    stats = {
        'total': reinscripciones.count(),
        'pendientes': reinscripciones.filter(estado='Pendiente').count(),
        'aprobadas': reinscripciones.filter(estado='Aprobada').count(),
        'completadas': reinscripciones.filter(estado='Completada').count(),
        'rechazadas': reinscripciones.filter(estado='Rechazada').count(),
    }
    
    context = {
        'reinscripciones': reinscripciones[:50],  # Limitar a 50 para rendimiento
        'stats': stats,
        'periodos': PeriodoEscolar.objects.filter(activo=True),
        'estado_filtro': estado_filtro,
        'periodo_filtro': periodo_filtro,
        'estados_choices': Reinscripcion.ESTADO_CHOICES,
    }
    
    return render(request, 'datos_academicos/reinscripciones/reinscripcion_list.html', context)


@login_required
def detalle_reinscripcion(request, reinscripcion_id):
    """Vista para mostrar el detalle de una reinscripción"""
    reinscripcion = get_object_or_404(
        Reinscripcion.objects.select_related(
            'alumno', 'periodo_escolar', 'nueva_carrera'
        ), 
        id=reinscripcion_id
    )
    
    context = {
        'reinscripcion': reinscripcion,
        'puede_aprobar': reinscripcion.estado == 'Pendiente',
        'puede_aplicar': reinscripcion.estado == 'Aprobada',
        'puede_rechazar': reinscripcion.estado in ['Pendiente', 'En Revisión'],
    }
    
    return render(request, 'datos_academicos/reinscripciones/reinscripcion_detail.html', context)