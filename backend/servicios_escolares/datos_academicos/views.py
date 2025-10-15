from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Q, Count, Sum, Avg
from django.utils.timezone import now
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
import json
from django.views.decorators.http import require_GET
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
import pandas as pd
import json
from .forms import AlumnoForm, TramiteForm, CalificacionForm
from .models import PeriodoEscolar, Carrera, Materia, Grupo, Alumno, Docente, PlanEstudio, Tramite, Calificacion, MateriaCarrera
from django.http import JsonResponse
from .serializer import (
    PeriodoEscolarSerializer,
    CarreraSerializer,
    MateriaSerializer,
    GrupoSerializer,
    AlumnoSerializer,
    DocenteSerializer,
    PlanEstudioSerializer, 
    TramiteSerializer
)
from procedimientos.models import Tramite, Bitacora
from .forms_inscripcion import InscripcionForm, ReinscripcionForm, BusquedaAlumnoForm
from .utils_inscripcion import generar_formato_inscripcion, generar_formato_reinscripcion, crear_plantillas_por_defecto
from .models_inscripcion import Inscripcion, Reinscripcion

# API para autocompletado
@require_GET
@login_required
def api_alumno_list(request):
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    # Filtrar alumnos con la consulta
    alumnos = Alumno.objects.filter(
        Q(nombre__icontains=query) | 
        Q(apellido_paterno__icontains=query) |
        Q(apellido_materno__icontains=query) |
        Q(matricula__icontains=query)
    ).filter(activo=True)
    
    # Limitar a 10 resultados
    alumnos = alumnos[:10]
    
    data = [{
        'id': alumno.id,
        'nombre': alumno.nombre,
        'apellido_paterno': alumno.apellido_paterno,
        'apellido_materno': alumno.apellido_materno,
        'matricula': alumno.matricula
    } for alumno in alumnos]
    
    return JsonResponse(data, safe=False)

@require_GET
@login_required
def api_materia_list(request):
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    materias = Materia.objects.filter(
        Q(nombre__icontains=query) | 
        Q(clave__icontains=query)
    )[:10]
    
    data = [{
        'id': materia.id,
        'nombre': materia.nombre,
        'clave': materia.clave,
        'creditos': materia.creditos
    } for materia in materias]
    
    return JsonResponse(data, safe=False)

# Views servicios escolares
@login_required
def dashboard(request):
    # KPIs
    alumnos_inscritos = Alumno.objects.filter(estatus='Inscrito').count()
    variacion_alumnos = 5  # Ejemplo, calcula real según tu lógica

    tramites_en_curso = Tramite.objects.filter(estado='En proceso').count()
    variacion_tramites = -3  # Ejemplo

    egresados = Alumno.objects.filter(estatus='Titulado').count()
    variacion_egresados = 2

    certificados_emitidos = Tramite.objects.filter(tipo='certificado').count()
    variacion_certificados = 7

    # Datos para gráfico alumnos por carrera
    datos_carreras = (
        Alumno.objects
        .values('carrera__nombre')
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad')
    )
    carreras = [item['carrera__nombre'] for item in datos_carreras]
    cantidades_carreras = [item['cantidad'] for item in datos_carreras]

    # Datos para gráfico trámites por tipo
    datos_tramites = (
        Tramite.objects
        .values('tipo')
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad')
    )
    tramites_tipos = [item['tipo'] for item in datos_tramites]
    tramites_cantidades = [item['cantidad'] for item in datos_tramites]

    # Trámites recientes
    tramites_recientes = Tramite.objects.order_by('-fecha_solicitud')[:5]

    context = {
        'segment': 'dashboard',
        'alumnos_inscritos': alumnos_inscritos,
        'variacion_alumnos': variacion_alumnos,
        'tramites_en_curso': tramites_en_curso,
        'variacion_tramites': variacion_tramites,
        'egresados': egresados,
        'variacion_egresados': variacion_egresados,
        'certificados_emitidos': certificados_emitidos,
        'variacion_certificados': variacion_certificados,
        'carreras': carreras,
        'cantidades_carreras': cantidades_carreras,
        'tramites_tipos': tramites_tipos,
        'tramites_cantidades': tramites_cantidades,
        'tramites_recientes': tramites_recientes,
    }
    return render(request, 'datos_academicos/dashboard.html', context)

# Gestión de alumnos por servicios escolares
@login_required
def gestion_alumnos(request):
    from datetime import datetime, timedelta
    from django.db.models import Q, Case, When, IntegerField, FloatField, F, Count, Avg
    
    # Estadísticas generales de alumnos
    total_alumnos = Alumno.objects.count()
    alumnos_inscritos = Alumno.objects.filter(estatus='Inscrito').count()
    nuevos_ingresos = Alumno.objects.filter(division_estudio='Nuevo Ingreso').count()
    reingresos = Alumno.objects.filter(division_estudio='Reingreso').count()
    promedio_general = Alumno.objects.aggregate(promedio=Avg('promedio'))['promedio'] or 0
    
    # Porcentaje de inscritos
    porcentaje_inscritos = (alumnos_inscritos / total_alumnos * 100) if total_alumnos > 0 else 0
    
    # Alumnos del mes actual
    mes_actual = datetime.now().replace(day=1)
    alumnos_mes = Alumno.objects.filter(
        fecha_inscripcion__gte=mes_actual
    ).count() if hasattr(Alumno, 'fecha_inscripcion') else 0
    
    # Total de créditos aprobados
    total_creditos_aprobados = Alumno.objects.aggregate(
        total=Sum('creditos_aprobados')
    )['total'] or 0
    
    # Estadísticas por carrera
    carreras_stats = Alumno.objects.values('carrera__nombre', 'carrera__clave').annotate(
        num_alumnos=Count('id'),
        promedio=Avg('promedio'),
        inscritos=Count('id', filter=Q(estatus='Inscrito'))
    ).annotate(
        porcentaje_inscritos=Case(
            When(num_alumnos=0, then=0),
            default=F('inscritos') * 100.0 / F('num_alumnos'),
            output_field=FloatField()
        )
    ).order_by('-num_alumnos')[:5]
    
    # Distribución por estatus
    estatus_distribucion = Alumno.objects.values('estatus').annotate(
        cantidad=Count('id')
    ).order_by('-cantidad')
    
    # Colores para gráficos
    colores_estatus = {
        'Inscrito': '#22c55e',
        'No Inscrito': '#ef4444',
        'Titulado': '#3b82f6',
        'Baja definitiva': '#f59e0b',
        'Baja temporal': '#8b5cf6'
    }
    
    for estatus in estatus_distribucion:
        estatus['color'] = colores_estatus.get(estatus['estatus'], '#6b7280')
    
    # Datos para gráficos (JSON)
    carreras_data = [carrera['carrera__nombre'] for carrera in carreras_stats]
    cantidades_data = [carrera['num_alumnos'] for carrera in carreras_stats]
    estatus_data = [estatus['estatus'] for estatus in estatus_distribucion]
    estatus_cantidades = [estatus['cantidad'] for estatus in estatus_distribucion]
    
    context = {
        'segment': 'gestion_alumnos',
        'username': request.user.username if request.user.is_authenticated else None,
        'total_alumnos': total_alumnos,
        'alumnos_inscritos': alumnos_inscritos,
        'nuevos_ingresos': nuevos_ingresos,
        'reingresos': reingresos,
        'promedio_general': promedio_general,
        'porcentaje_inscritos': porcentaje_inscritos,
        'alumnos_mes': alumnos_mes,
        'total_creditos_aprobados': total_creditos_aprobados,
        'carreras_populares': carreras_stats,
        'estatus_distribucion': estatus_distribucion,
        'carreras_data': carreras_data,
        'cantidades_data': cantidades_data,
        'estatus_data': estatus_data,
        'estatus_cantidades': estatus_cantidades,
    }
    return render(request, 'datos_academicos/gestion_alumnos.html', context)

@login_required
def gestion_calificaciones(request):
    from datetime import datetime, timedelta
    from django.db.models import Q, Case, When, IntegerField, FloatField, F
    
    # Estadísticas generales de calificaciones
    total_calificaciones = Calificacion.objects.count()
    calificaciones_aprobadas = Calificacion.objects.filter(calificacion__gte=60).count()
    calificaciones_reprobadas = Calificacion.objects.filter(calificacion__lt=60).count()
    promedio_general = Calificacion.objects.aggregate(promedio=Avg('calificacion'))['promedio'] or 0
    
    # Porcentajes de aprobación y reprobación
    porcentaje_aprobacion = (calificaciones_aprobadas / total_calificaciones * 100) if total_calificaciones > 0 else 0
    porcentaje_reprobacion = (calificaciones_reprobadas / total_calificaciones * 100) if total_calificaciones > 0 else 0
    
    # Calificaciones del mes actual
    mes_actual = datetime.now().replace(day=1)
    calificaciones_mes = Calificacion.objects.filter(
        fecha_registro__gte=mes_actual
    ).count() if hasattr(Calificacion, 'fecha_registro') else 0
    
    # Total de créditos
    total_creditos = Calificacion.objects.aggregate(
        total=Sum('creditos')
    )['total'] or 0
    
    # Estadísticas por tipo de acreditación
    acreditaciones_ordinario = Calificacion.objects.filter(acreditacion='Ordinario').count()
    acreditaciones_convalidacion = Calificacion.objects.filter(acreditacion='Convalidación').count()
    acreditaciones_extraordinario = Calificacion.objects.filter(acreditacion='Extraordinario').count()
    
    acreditacion_stats = Calificacion.objects.values('acreditacion').annotate(
        total=Count('id')
    ).order_by('-total')
    
    acreditacion_labels = [item['acreditacion'] for item in acreditacion_stats]
    acreditacion_data = [item['total'] for item in acreditacion_stats]
    
    # Calificaciones por carrera
    datos_calificaciones_carrera = (
        Calificacion.objects
        .values('alumno__carrera__nombre')
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad')
    )
    carreras_calificaciones = [item['alumno__carrera__nombre'] for item in datos_calificaciones_carrera]
    cantidades_calificaciones = [item['cantidad'] for item in datos_calificaciones_carrera]
    
    # Distribución de calificaciones por rango
    rangos_calificaciones = [
        {'rango': '0-59 (Reprobado)', 'cantidad': Calificacion.objects.filter(calificacion__lt=60).count()},
        {'rango': '60-69 (Suficiente)', 'cantidad': Calificacion.objects.filter(calificacion__gte=60, calificacion__lt=70).count()},
        {'rango': '70-79 (Bien)', 'cantidad': Calificacion.objects.filter(calificacion__gte=70, calificacion__lt=80).count()},
        {'rango': '80-89 (Notable)', 'cantidad': Calificacion.objects.filter(calificacion__gte=80, calificacion__lt=90).count()},
        {'rango': '90-100 (Excelente)', 'cantidad': Calificacion.objects.filter(calificacion__gte=90).count()},
    ]
    rangos_nombres = [item['rango'] for item in rangos_calificaciones]
    rangos_cantidades = [item['cantidad'] for item in rangos_calificaciones]
    
    # Materias con más calificaciones registradas - con estadísticas adicionales
    materias_populares = (
        Calificacion.objects
        .values('materia__nombre', 'materia__clave')
        .annotate(
            num_calificaciones=Count('id'),
            promedio=Avg('calificacion'),
            aprobadas=Count(Case(When(calificacion__gte=60, then=1), output_field=IntegerField())),
            total_evaluaciones=Count('id')
        )
        .annotate(
            porcentaje_aprobacion=Case(
                When(total_evaluaciones=0, then=0),
                default=F('aprobadas') * 100.0 / F('total_evaluaciones'),
                output_field=FloatField()
            )
        )
        .order_by('-num_calificaciones')[:10]
    )
    
    # Calificaciones por período escolar
    datos_periodos = (
        Calificacion.objects
        .values('periodo_escolar__ciclo', 'periodo_escolar__año')
        .annotate(cantidad=Count('id'))
        .order_by('-periodo_escolar__año', '-periodo_escolar__ciclo')
    )
    
    # Tendencias por período escolar
    periodos_stats = Calificacion.objects.values(
        'periodo_escolar__ciclo', 'periodo_escolar__año'
    ).annotate(
        promedio=Avg('calificacion'),
        total=Count('id')
    ).order_by('periodo_escolar__año', 'periodo_escolar__ciclo')[:6]
    
    periodos_nombres = [f"{item['periodo_escolar__ciclo']} {item['periodo_escolar__año']}" for item in periodos_stats]
    periodos_promedios = [float(item['promedio']) if item['promedio'] else 0 for item in periodos_stats]
    
    # Alertas y notificaciones
    materias_bajo_rendimiento = Calificacion.objects.values(
        'materia__nombre'
    ).annotate(
        promedio=Avg('calificacion')
    ).filter(promedio__lt=60)
    
    materias_excelencia = Calificacion.objects.values(
        'materia__nombre'
    ).annotate(
        promedio=Avg('calificacion')
    ).filter(promedio__gte=90)
    
    # Calificaciones pendientes (simulado - ajustar según lógica de negocio)
    calificaciones_pendientes = 0  # Implementar lógica específica si es necesario
    
    context = {
        'segment': 'gestion_calificaciones',
        'username': request.user.username if request.user.is_authenticated else None,
        
        # Estadísticas generales
        'total_calificaciones': total_calificaciones,
        'calificaciones_aprobadas': calificaciones_aprobadas,
        'calificaciones_reprobadas': calificaciones_reprobadas,
        'promedio_general': round(promedio_general, 2) if promedio_general else 0,
        'porcentaje_aprobacion': round(porcentaje_aprobacion, 1),
        'porcentaje_reprobacion': round(porcentaje_reprobacion, 1),
        'calificaciones_mes': calificaciones_mes,
        'total_creditos': total_creditos,
        
        # Estadísticas por acreditación
        'acreditaciones_ordinario': acreditaciones_ordinario,
        'acreditaciones_convalidacion': acreditaciones_convalidacion,
        'acreditaciones_extraordinario': acreditaciones_extraordinario,
        'acreditacion_stats': acreditacion_stats,
        'acreditacion_labels': json.dumps(acreditacion_labels),
        'acreditacion_data': json.dumps(acreditacion_data),
        
        # Datos para gráficos (convertidos a JSON)
        'carreras_calificaciones': json.dumps(carreras_calificaciones),
        'cantidades_calificaciones': json.dumps(cantidades_calificaciones),
        'rangos_nombres': json.dumps(rangos_nombres),
        'rangos_cantidades': json.dumps(rangos_cantidades),
        'periodos_nombres': json.dumps(periodos_nombres),
        'periodos_promedios': json.dumps(periodos_promedios),
        
        # Listas para mostrar en tablas
        'materias_populares': materias_populares,
        'datos_periodos': datos_periodos,
        'materias_bajo_rendimiento': materias_bajo_rendimiento,
        'materias_excelencia': materias_excelencia,
        'calificaciones_pendientes': calificaciones_pendientes,
    }
    return render(request, 'datos_academicos/gestion_calificaciones.html', context)

@login_required
def gestion_materias(request):
    # Estadísticas de materias
    total_materias = Materia.objects.count()
    materias_obligatorias = Materia.objects.filter(tipo='Obligatoria').count()
    materias_optativas = Materia.objects.filter(tipo='Optativa').count()
    materias_especialidad = Materia.objects.filter(tipo='Especialidad').count()
    
    # Estadísticas de planes de estudio
    total_planes = PlanEstudio.objects.count()
    planes_activos = total_planes  # Todos los planes se consideran activos por ahora
    
    # Materias por carrera
    datos_materias_carrera = (
        MateriaCarrera.objects
        .values('carrera__nombre')
        .annotate(cantidad=Count('materia'))
        .order_by('-cantidad')
    )
    carreras_materias = [item['carrera__nombre'] for item in datos_materias_carrera]
    cantidades_materias = [item['cantidad'] for item in datos_materias_carrera]
    
    # Distribución de créditos por tipo de materia
    datos_creditos = (
        Materia.objects
        .values('tipo')
        .annotate(total_creditos=Sum('creditos'))
        .order_by('-total_creditos')
    )
    tipos_materia = [item['tipo'] for item in datos_creditos]
    creditos_por_tipo = [item['total_creditos'] for item in datos_creditos]
    
    # Materias más utilizadas en calificaciones
    materias_populares = (
        Materia.objects
        .annotate(num_calificaciones=Count('calificaciones'))
        .order_by('-num_calificaciones')[:5]
    )
    
    # Promedio de créditos por materia
    promedio_creditos = Materia.objects.aggregate(
        promedio=Avg('creditos')
    )['promedio'] or 0
    
    context = {
        'segment': 'gestion_materias',
        'username': request.user.username if request.user.is_authenticated else None,
        # Estadísticas generales
        'total_materias': total_materias,
        'materias_obligatorias': materias_obligatorias,
        'materias_optativas': materias_optativas,
        'materias_especialidad': materias_especialidad,
        'total_planes': total_planes,
        'planes_activos': planes_activos,
        'promedio_creditos': round(promedio_creditos, 1),
        # Datos para gráficos (convertidos a JSON)
        'carreras_materias': json.dumps(carreras_materias),
        'cantidades_materias': json.dumps(cantidades_materias),
        'tipos_materia': json.dumps(tipos_materia),
        'creditos_por_tipo': json.dumps(creditos_por_tipo),
        'materias_populares': materias_populares,
    }
    return render(request, 'datos_academicos/gestion_materias.html', context)


class AlumnoListView(LoginRequiredMixin, ListView):
    model = Alumno
    template_name = 'datos_academicos/alumno_list.html'
    context_object_name = 'alumnos'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related('carrera')
        q = self.request.GET.get('q', '')
        carrera = self.request.GET.get('carrera')
        estatus = self.request.GET.get('estatus')

        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q) |
                Q(apellido_paterno__icontains=q) |
                Q(apellido_materno__icontains=q) |
                Q(matricula__icontains=q) |
                Q(carrera__nombre__icontains=q)
            )

        if carrera:
            queryset = queryset.filter(carrera_id=carrera)

        if estatus:
            queryset = queryset.filter(estatus=estatus)

        return queryset.order_by('matricula')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['carreras'] = Carrera.objects.all()
        context['segment'] = 'gestion_alumnos'
        return context  
    
class AlumnoDetailView(LoginRequiredMixin, DetailView):
    model = Alumno
    template_name = 'datos_academicos/alumno_detail.html'
    context_object_name = 'alumno'

class AlumnoCreateView(LoginRequiredMixin, CreateView):
    model = Alumno
    form_class = AlumnoForm
    template_name = 'datos_academicos/alumno_form.html'
    success_url = reverse_lazy('alumno_list')

class AlumnoUpdateView(LoginRequiredMixin, UpdateView):
    model = Alumno
    form_class = AlumnoForm
    template_name = 'datos_academicos/alumno_form.html'
    success_url = reverse_lazy('datos_academicos:alumno_list')

class AlumnoDeleteView(LoginRequiredMixin, DeleteView):
    model = Alumno
    template_name = 'datos_academicos/alumno_confirm_delete.html'
    success_url = reverse_lazy('datos_academicos:alumno_list')


# views de api para el manejo de datos académicos
class PeriodoEscolarViewSet(viewsets.ModelViewSet):
    queryset = PeriodoEscolar.objects.all()
    serializer_class = PeriodoEscolarSerializer
    permission_classes = [IsAuthenticated]

class CarreraViewSet(viewsets.ModelViewSet):
    queryset = Carrera.objects.all()
    serializer_class = CarreraSerializer
    permission_classes = [IsAuthenticated]

class MateriaViewSet(viewsets.ModelViewSet):
    queryset = Materia.objects.all()
    serializer_class = MateriaSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)

class GrupoViewSet(viewsets.ModelViewSet):
    queryset = Grupo.objects.all()
    serializer_class = GrupoSerializer
    permission_classes = [IsAuthenticated]

class AlumnoViewSet(viewsets.ModelViewSet):
    queryset = Alumno.objects.all()
    serializer_class = AlumnoSerializer
    permission_classes = [IsAuthenticated]
    
@api_view(['GET'])
def alumno_detail_api(request, pk):
    """API para obtener datos de un alumno específico, incluyendo su carrera"""
    if not request.user.is_authenticated:
        return Response({'error': 'Autenticación requerida'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        alumno = Alumno.objects.get(pk=pk)
        data = {
            'id': alumno.id,
            'nombre': alumno.nombre,
            'apellido_paterno': alumno.apellido_paterno,
            'apellido_materno': alumno.apellido_materno,
            'matricula': alumno.matricula,
            'carrera': alumno.carrera.id if alumno.carrera else None,
            'carrera_nombre': alumno.carrera.nombre if alumno.carrera else None,
            'activo': alumno.activo
        }
        return Response(data)
    except Alumno.DoesNotExist:
        return Response({'error': 'Alumno no encontrado'}, status=status.HTTP_404_NOT_FOUND)

class DocenteViewSet(viewsets.ModelViewSet):
    queryset = Docente.objects.all()
    serializer_class = DocenteSerializer
    permission_classes = [IsAuthenticated]

class PlanEstudioViewSet(viewsets.ModelViewSet):
    queryset = PlanEstudio.objects.all()
    serializer_class = PlanEstudioSerializer
    permission_classes = [IsAuthenticated]

class TramiteViewSet(viewsets.ModelViewSet):
    queryset = Tramite.objects.all()
    serializer_class = TramiteSerializer
    permission_classes = [IsAuthenticated]

    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        archivo = request.FILES.get("archivo")
        if not archivo:
            return Response({"error": "No se envió archivo"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Cargar todas las hojas
            hojas = pd.read_excel(archivo, sheet_name=None)

            hoja_materias = None
            for nombre_hoja, df in hojas.items():
                columnas = [col.strip().upper() for col in df.columns if isinstance(col, str)]
                if "CLAVE" in columnas and "NOMBRE DE LA MATERIA" in columnas:
                    hoja_materias = df
                    break

            if hoja_materias is None:
                return Response({"error": "No se encontró una hoja con columnas 'CLAVE' y 'NOMBRE DE LA MATERIA'"}, status=status.HTTP_400_BAD_REQUEST)

            hoja_materias = hoja_materias.dropna(subset=["CLAVE", "NOMBRE DE LA MATERIA"])

            for _, fila in hoja_materias.iterrows():
                Materia.objects.update_or_create(
                    clave=str(fila["CLAVE"]).strip(),
                    defaults={
                        "nombre": str(fila["NOMBRE DE LA MATERIA"]).strip(),
                        "creditos": int(fila.get("CRED", 0)),
                        "horas_teoricas": int(fila.get("T", 0)),
                        "horas_practicas": int(fila.get("P", 0)),
                        "tipo": str(fila.get("TIPO DE CURSO", "")).strip(),
                    }
                )

            return Response({"mensaje": "Materias importadas correctamente"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CalificacionListView(LoginRequiredMixin, ListView):
    model = Calificacion
    template_name = 'datos_academicos/calificaciones/calificacion_list.html'
    context_object_name = 'calificaciones'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related('alumno', 'materia', 'periodo_escolar')
        q = self.request.GET.get('q', '')
        periodo = self.request.GET.get('periodo')
        acreditacion = self.request.GET.get('acreditacion')

        if q:
            queryset = queryset.filter(
                Q(alumno__nombre__icontains=q) |
                Q(alumno__matricula__icontains=q) |
                Q(materia__nombre__icontains=q)
            )

        if periodo:
            queryset = queryset.filter(periodo_escolar_id=periodo)

        if acreditacion:
            queryset = queryset.filter(acreditacion=acreditacion)

        return queryset.order_by('alumno__matricula', 'materia__nombre')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['periodos'] = PeriodoEscolar.objects.all()
        context['acreditaciones'] = ['Ordinario', 'Convalidación']
        context['segment'] = 'gestion_calificaciones'
        return context

@login_required
def calificacion_list(request):
    return CalificacionListView.as_view()(request)

@login_required
def calificacion_detail(request, pk):
    calificacion = get_object_or_404(Calificacion, pk=pk)
    return render(request, 'datos_academicos/calificaciones/calificacion_detail.html', {'calificacion': calificacion})

@login_required
def calificacion_create(request):
    if request.method == 'POST':
        form = CalificacionForm(request.POST)
        if form.is_valid():
            # Verificar si se proporcionó un ID de materia específico
            materia_id = form.cleaned_data.get('materia_id')
            if materia_id:
                try:
                    materia = Materia.objects.get(id=materia_id)
                    calificacion = form.save(commit=False)
                    calificacion.materia = materia
                    calificacion.save()
                    messages.success(request, 'Calificación creada correctamente.')
                    return redirect('datos_academicos:calificacion_list')
                except Materia.DoesNotExist:
                    messages.error(request, f'No se encontró la materia con ID: {materia_id}')
            else:
                form.save()
                messages.success(request, 'Calificación creada correctamente.')
                return redirect('datos_academicos:calificacion_list')
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = CalificacionForm()
    
    # Obtener todas las materias para el filtrado por JavaScript
    materias = Materia.objects.all().values('id', 'nombre', 'materiacarrera__carrera__id')
    
    return render(request, 'datos_academicos/calificaciones/calificacion_form.html', {
        'form': form,
        'materias_json': json.dumps(list(materias), cls=DjangoJSONEncoder),
    })


@login_required
def calificacion_edit(request, pk):
    calificacion = get_object_or_404(Calificacion, pk=pk)

    if request.method == 'POST':
        form = CalificacionForm(request.POST, instance=calificacion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Calificación actualizada correctamente.')
            return redirect('datos_academicos:calificacion_detail', pk=calificacion.pk)
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = CalificacionForm(instance=calificacion)

    return render(request, 'datos_academicos/calificaciones/calificacion_form.html', {'form': form})


# Vistas para gestión de materias
class MateriaListView(LoginRequiredMixin, ListView):
    model = Materia
    template_name = 'datos_academicos/materias/materia_list.html'
    context_object_name = 'materias'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '')
        carrera = self.request.GET.get('carrera')

        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q) |
                Q(clave__icontains=q)
            )

        if carrera:
            queryset = queryset.filter(materiacarrera__carrera_id=carrera)

        return queryset.order_by('clave')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['carreras'] = Carrera.objects.all()
        context['segment'] = 'gestion_materias'
        return context

@login_required
def materia_detail(request, pk):
    materia = get_object_or_404(Materia, pk=pk)
    return render(request, 'datos_academicos/materias/materia_detail.html', {'materia': materia})

@login_required
def materia_create(request):
    if request.method == 'POST':
        # Aquí iría la lógica para crear una nueva materia
        # Por ahora redirigimos a la lista
        messages.success(request, 'Materia creada correctamente.')
        return redirect('datos_academicos:materia_list')
    
    # Para GET request, mostrar el formulario
    return render(request, 'datos_academicos/materias/materia_form.html', {})
    
@login_required
def materia_edit(request, pk):
    materia = get_object_or_404(Materia, pk=pk)
    
    if request.method == 'POST':
        # Aquí iría la lógica para editar la materia
        # Por ahora redirigimos al detalle
        messages.success(request, 'Materia actualizada correctamente.')
        return redirect('datos_academicos:materia_detail', pk=materia.pk)
    
    return render(request, 'datos_academicos/materias/materia_form.html', {'materia': materia})

# Vistas para gestión de planes de estudio
class PlanEstudioListView(LoginRequiredMixin, ListView):
    model = PlanEstudio
    template_name = 'datos_academicos/planes/plan_estudio_list.html'
    context_object_name = 'planes'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('carrera')
        q = self.request.GET.get('q', '')
        carrera = self.request.GET.get('carrera')
        año = self.request.GET.get('año')

        if q:
            queryset = queryset.filter(
                Q(clave__icontains=q) |
                Q(año__icontains=q) |
                Q(carrera__nombre__icontains=q)
            )

        if carrera:
            queryset = queryset.filter(carrera_id=carrera)
            
        if año:
            queryset = queryset.filter(año=año)

        return queryset.order_by('carrera__nombre', 'año', 'clave')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Datos básicos
        context['carreras'] = Carrera.objects.all()
        context['segment'] = 'gestion_materias'
        
        # Estadísticas generales
        total_planes = PlanEstudio.objects.count()
        planes_por_carrera = PlanEstudio.objects.values('carrera__nombre').annotate(
            total=Count('id')
        ).order_by('-total')
        
        # Años disponibles para filtro
        años_disponibles = PlanEstudio.objects.values_list('año', flat=True).distinct().order_by('-año')
        
        # Estadísticas de materias por plan
        planes_con_materias = []
        for plan in self.get_queryset():
            materias_count = MateriaCarrera.objects.filter(carrera=plan.carrera).count()
            creditos_totales = MateriaCarrera.objects.filter(carrera=plan.carrera).aggregate(
                total_creditos=Sum('materia__creditos')
            )['total_creditos'] or 0
            
            planes_con_materias.append({
                'plan': plan,
                'materias_count': materias_count,
                'creditos_totales': creditos_totales
            })
        
        # Estadísticas por carrera
        stats_por_carrera = []
        for carrera in Carrera.objects.all():
            planes_carrera = PlanEstudio.objects.filter(carrera=carrera).count()
            materias_carrera = MateriaCarrera.objects.filter(carrera=carrera).count()
            creditos_carrera = MateriaCarrera.objects.filter(carrera=carrera).aggregate(
                total=Sum('materia__creditos')
            )['total'] or 0
            
            if planes_carrera > 0:
                stats_por_carrera.append({
                    'carrera': carrera.nombre,
                    'planes': planes_carrera,
                    'materias': materias_carrera,
                    'creditos': creditos_carrera
                })
        
        context.update({
            'total_planes': total_planes,
            'planes_por_carrera': planes_por_carrera,
            'años_disponibles': años_disponibles,
            'planes_con_materias': planes_con_materias,
            'stats_por_carrera': stats_por_carrera,
            'total_carreras': Carrera.objects.count(),
            'promedio_materias_por_carrera': round(
                MateriaCarrera.objects.count() / max(Carrera.objects.count(), 1), 1
            )
        })
        
        return context

@login_required
def plan_estudio_list(request):
    return PlanEstudioListView.as_view()(request)

@login_required
def plan_estudio_detail(request, pk):
    plan = get_object_or_404(PlanEstudio, pk=pk)
    # Obtener materias del plan agrupadas por semestre
    materias_por_semestre = {}
    materias_carrera = MateriaCarrera.objects.filter(carrera=plan.carrera).select_related('materia').order_by('semestre', 'materia__nombre')
    
    for mc in materias_carrera:
        semestre = mc.semestre or 'Sin semestre'
        if semestre not in materias_por_semestre:
            materias_por_semestre[semestre] = []
        materias_por_semestre[semestre].append(mc.materia)
    
    context = {
        'plan': plan,
        'materias_por_semestre': materias_por_semestre,
        'segment': 'gestion_materias'
    }
    return render(request, 'datos_academicos/planes/plan_estudio_detail.html', context)

@login_required
def plan_estudio_create(request):
    # Placeholder para crear plan de estudio
    context = {'segment': 'gestion_materias'}
    return render(request, 'datos_academicos/planes/plan_estudio_form.html', context)

@login_required
def plan_estudio_edit(request, pk):
    plan = get_object_or_404(PlanEstudio, pk=pk)
    # Placeholder para editar plan de estudio
    context = {'plan': plan, 'segment': 'gestion_materias'}
    return render(request, 'datos_academicos/planes/plan_estudio_form.html', context)


def inscripcion_nueva(request):
    """Vista para mostrar el formulario de nueva inscripción"""
    if request.method == 'GET':
        form = InscripcionForm()
        return render(request, 'datos_academicos/inscripcion_form.html', {
            'form': form,
            'title': 'Nueva Inscripción'
        })

def inscripcion_crear(request):
    """Vista para procesar la creación de una nueva inscripción"""
    if request.method == 'POST':
        form = InscripcionForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                inscripcion = form.save()
                
                # Crear plantillas por defecto si no existen
                crear_plantillas_por_defecto()
                
                return JsonResponse({
                    'success': True,
                    'folio': inscripcion.folio,
                    'inscripcion_id': inscripcion.id,
                    'message': 'Inscripción registrada exitosamente'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'errors': {'general': [str(e)]}
                })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    
    return JsonResponse({
        'success': False,
        'errors': {'general': ['Método no permitido']}
    })

def reinscripcion_nueva(request):
    """Vista para mostrar y procesar el formulario de reinscripción"""
    if request.method == 'POST':
        try:
            form = ReinscripcionForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    reinscripcion = form.save()
                    
                    # Crear plantillas por defecto si no existen
                    try:
                        crear_plantillas_por_defecto()
                    except Exception as e:
                        # Log the error but don't fail the request
                        print(f"Error creating templates: {e}")
                    
                    return JsonResponse({
                        'success': True,
                        'folio': reinscripcion.folio,
                        'reinscripcion_id': reinscripcion.id,
                        'message': 'Reinscripción registrada exitosamente'
                    })
                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'errors': {'general': [str(e)]}
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'errors': {'general': [f'Error procesando formulario: {str(e)}']}
            })
    else:
        # GET request - mostrar formulario
        try:
            form_reinscripcion = ReinscripcionForm()
            form_busqueda = BusquedaAlumnoForm()
            return render(request, 'datos_academicos/reinscripcion_form.html', {
                'form_reinscripcion': form_reinscripcion,
                'form_busqueda': form_busqueda,
                'title': 'Reinscripción de Alumno'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'errors': {'general': [f'Error cargando formulario: {str(e)}']}
            })

def reinscripcion_crear(request):
    """Vista para procesar la creación de una reinscripción"""
    if request.method == 'POST':
        form = ReinscripcionForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                reinscripcion = form.save()
                
                # Crear plantillas por defecto si no existen
                crear_plantillas_por_defecto()
                
                return JsonResponse({
                    'success': True,
                    'folio': reinscripcion.folio,
                    'reinscripcion_id': reinscripcion.id,
                    'message': 'Reinscripción registrada exitosamente'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'errors': {'general': [str(e)]}
                })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    
    return JsonResponse({
        'success': False,
        'errors': {'general': ['Método no permitido']}
    })

@login_required
def generar_documento_inscripcion(request, inscripcion_id):
    """Vista para generar el documento de inscripción en formato DOCX"""
    try:
        response = generar_formato_inscripcion(inscripcion_id)
        return response
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('datos_academicos:gestion_alumnos')
    except Exception as e:
        messages.error(request, f"Error al generar documento: {str(e)}")
        return redirect('datos_academicos:gestion_alumnos')

@login_required
def generar_documento_reinscripcion(request, reinscripcion_id):
    """Vista para generar el documento de reinscripción en formato DOCX"""
    try:
        response = generar_formato_reinscripcion(reinscripcion_id)
        return response
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('datos_academicos:gestion_alumnos')
    except Exception as e:
        messages.error(request, f"Error al generar documento: {str(e)}")
        return redirect('datos_academicos:gestion_alumnos')

def buscar_alumno_ajax(request):
    """Vista AJAX para buscar alumnos"""
    if request.method == 'GET':
        matricula = request.GET.get('matricula', '')
        alumno_id = request.GET.get('id', '')
        
        # Búsqueda por matrícula específica
        if matricula:
            try:
                alumno = Alumno.objects.get(matricula=matricula)
                return JsonResponse({
                    'success': True,
                    'alumno': {
                        'id': alumno.id,
                        'matricula': alumno.matricula,
                        'nombre_completo': f"{alumno.nombre} {alumno.apellido_paterno} {alumno.apellido_materno}",
                        'nombre': alumno.nombre,
                        'apellido_paterno': alumno.apellido_paterno,
                        'apellido_materno': alumno.apellido_materno,
                        'carrera': alumno.carrera.nombre if alumno.carrera else '',
                        'carrera_id': alumno.carrera.id if alumno.carrera else None,
                        'semestre': alumno.semestre,
                        'promedio': float(alumno.promedio) if alumno.promedio else 0.0,
                        'creditos_aprobados': alumno.creditos_aprobados,
                        'creditos_totales': alumno.creditos_totales,
                        'estatus': alumno.estatus,
                        'modalidad': alumno.modalidad,
                        'plan_estudio': alumno.plan_estudio.clave if alumno.plan_estudio else ''
                    }
                })
            except Alumno.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'No se encontró un alumno con esa matrícula'
                })
        
        # Búsqueda por ID específico
        if alumno_id:
            try:
                alumno = Alumno.objects.get(id=alumno_id)
                return JsonResponse({
                    'success': True,
                    'alumno': {
                        'id': alumno.id,
                        'matricula': alumno.matricula,
                        'nombre_completo': f"{alumno.nombre} {alumno.apellido_paterno} {alumno.apellido_materno}",
                        'nombre': alumno.nombre,
                        'apellido_paterno': alumno.apellido_paterno,
                        'apellido_materno': alumno.apellido_materno,
                        'carrera': alumno.carrera.nombre if alumno.carrera else '',
                        'carrera_id': alumno.carrera.id if alumno.carrera else None,
                        'semestre': alumno.semestre,
                        'promedio': float(alumno.promedio) if alumno.promedio else 0.0,
                        'creditos_aprobados': alumno.creditos_aprobados,
                        'creditos_totales': alumno.creditos_totales,
                        'estatus': alumno.estatus,
                        'modalidad': alumno.modalidad,
                        'plan_estudio': alumno.plan_estudio.clave if alumno.plan_estudio else ''
                    }
                })
            except Alumno.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'No se encontró el alumno'
                })
        
        # Búsqueda general para autocompletado
        query = request.GET.get('q', '')
        if len(query) >= 3:
            alumnos = Alumno.objects.filter(
                Q(matricula__icontains=query) |
                Q(nombre__icontains=query) |
                Q(apellido_paterno__icontains=query) |
                Q(apellido_materno__icontains=query)
            )[:10]
            
            results = []
            for alumno in alumnos:
                results.append({
                    'id': alumno.id,
                    'matricula': alumno.matricula,
                    'nombre_completo': f"{alumno.nombre} {alumno.apellido_paterno} {alumno.apellido_materno}",
                    'carrera': alumno.carrera.nombre if alumno.carrera else '',
                    'semestre': alumno.semestre,
                    'estatus': alumno.estatus
                })
            
            return JsonResponse({'results': results})
        
        return JsonResponse({'results': []})

@login_required
def materia_detail(request, pk):
    materia = get_object_or_404(Materia, pk=pk)
    return render(request, 'datos_academicos/materias/materia_detail.html', {'materia': materia})

@login_required
def materia_create(request):
    if request.method == 'POST':
        # Aquí iría la lógica para crear una nueva materia
        # Por ahora redirigimos a la lista
        messages.success(request, 'Materia creada correctamente.')
        return redirect('datos_academicos:materia_list')
    
    # Para GET request, mostrar el formulario
    return render(request, 'datos_academicos/materias/materia_form.html', {})
    
@login_required
def materia_edit(request, pk):
    materia = get_object_or_404(Materia, pk=pk)
    
    if request.method == 'POST':
        # Aquí iría la lógica para editar la materia
        # Por ahora redirigimos al detalle
        messages.success(request, 'Materia actualizada correctamente.')
        return redirect('datos_academicos:materia_detail', pk=materia.pk)
    
    return render(request, 'datos_academicos/materias/materia_form.html', {'materia': materia})

# Vistas para gestión de planes de estudio
class PlanEstudioListView(LoginRequiredMixin, ListView):
    model = PlanEstudio
    template_name = 'datos_academicos/planes/plan_estudio_list.html'
    context_object_name = 'planes'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('carrera')
        q = self.request.GET.get('q', '')
        carrera = self.request.GET.get('carrera')
        año = self.request.GET.get('año')

        if q:
            queryset = queryset.filter(
                Q(clave__icontains=q) |
                Q(año__icontains=q) |
                Q(carrera__nombre__icontains=q)
            )

        if carrera:
            queryset = queryset.filter(carrera_id=carrera)
            
        if año:
            queryset = queryset.filter(año=año)

        return queryset.order_by('carrera__nombre', 'año', 'clave')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Datos básicos
        context['carreras'] = Carrera.objects.all()
        context['segment'] = 'gestion_materias'
        
        # Estadísticas generales
        total_planes = PlanEstudio.objects.count()
        planes_por_carrera = PlanEstudio.objects.values('carrera__nombre').annotate(
            total=Count('id')
        ).order_by('-total')
        
        # Años disponibles para filtro
        años_disponibles = PlanEstudio.objects.values_list('año', flat=True).distinct().order_by('-año')
        
        # Estadísticas de materias por plan
        planes_con_materias = []
        for plan in self.get_queryset():
            materias_count = MateriaCarrera.objects.filter(carrera=plan.carrera).count()
            creditos_totales = MateriaCarrera.objects.filter(carrera=plan.carrera).aggregate(
                total_creditos=Sum('materia__creditos')
            )['total_creditos'] or 0
            
            planes_con_materias.append({
                'plan': plan,
                'materias_count': materias_count,
                'creditos_totales': creditos_totales
            })
        
        # Estadísticas por carrera
        stats_por_carrera = []
        for carrera in Carrera.objects.all():
            planes_carrera = PlanEstudio.objects.filter(carrera=carrera).count()
            materias_carrera = MateriaCarrera.objects.filter(carrera=carrera).count()
            creditos_carrera = MateriaCarrera.objects.filter(carrera=carrera).aggregate(
                total=Sum('materia__creditos')
            )['total'] or 0
            
            if planes_carrera > 0:
                stats_por_carrera.append({
                    'carrera': carrera.nombre,
                    'planes': planes_carrera,
                    'materias': materias_carrera,
                    'creditos': creditos_carrera
                })
        
        context.update({
            'total_planes': total_planes,
            'planes_por_carrera': planes_por_carrera,
            'años_disponibles': años_disponibles,
            'planes_con_materias': planes_con_materias,
            'stats_por_carrera': stats_por_carrera,
            'total_carreras': Carrera.objects.count(),
            'promedio_materias_por_carrera': round(
                MateriaCarrera.objects.count() / max(Carrera.objects.count(), 1), 1
            )
        })
        
        return context

@login_required
def plan_estudio_list(request):
    return PlanEstudioListView.as_view()(request)

@login_required
def plan_estudio_detail(request, pk):
    plan = get_object_or_404(PlanEstudio, pk=pk)
    # Obtener materias del plan agrupadas por semestre
    materias_por_semestre = {}
    materias_carrera = MateriaCarrera.objects.filter(carrera=plan.carrera).select_related('materia').order_by('semestre', 'materia__nombre')
    
    for mc in materias_carrera:
        semestre = mc.semestre or 'Sin semestre'
        if semestre not in materias_por_semestre:
            materias_por_semestre[semestre] = []
        materias_por_semestre[semestre].append(mc.materia)
    
    context = {
        'plan': plan,
        'materias_por_semestre': materias_por_semestre,
        'segment': 'gestion_materias'
    }
    return render(request, 'datos_academicos/planes/plan_estudio_detail.html', context)

@login_required
def plan_estudio_create(request):
    # Placeholder para crear plan de estudio
    context = {'segment': 'gestion_materias'}
    return render(request, 'datos_academicos/planes/plan_estudio_form.html', context)

@login_required
def plan_estudio_edit(request, pk):
    plan = get_object_or_404(PlanEstudio, pk=pk)
    # Placeholder para editar plan de estudio
    context = {'plan': plan, 'segment': 'gestion_materias'}
    return render(request, 'datos_academicos/planes/plan_estudio_form.html', context)