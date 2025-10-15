from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from datos_academicos.models import PeriodoEscolar, Alumno, Tramite
from django.db.models import Count
from .utils import obtener_periodo_activo, necesita_crear_periodo
from .forms import PeriodoEscolarForm
from django.contrib import messages
from django.conf import settings




def home(request):
    return render(request, 'home.html')


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
    return render(request, 'app/dashboard.html', context)



@login_required
def configuracion(request):
    periodo = obtener_periodo_activo()
    mostrar_modal_creacion = necesita_crear_periodo()

    if request.method == 'POST':
        form_name = request.POST.get('form_name')
        # Diferenciar formularios en la misma página
        if form_name == 'periodo_actual':
            # Si hay periodo, editar; si no, crear nuevo
            if periodo:
                form = PeriodoEscolarForm(request.POST, instance=periodo)
            else:
                form = PeriodoEscolarForm(request.POST)
            if form.is_valid():
                obj = form.save()
                messages.success(request, "Periodo escolar guardado correctamente.")
                # Redirigir para aplicar PRG y que el mensaje aparezca
                return redirect('configuracion')
            else:
                # Si hay errores, mostrar modal con el form (no redirigir)
                mostrar_modal_creacion = True
        else:
            # otros formularios de configuración que tengas...
            form = PeriodoEscolarForm(instance=periodo)
    else:
        form = PeriodoEscolarForm(instance=periodo)

    context = {
        'segment': 'configuracion',
        'form_periodo': form,
        'periodo': periodo,
        'mostrar_modal_creacion': mostrar_modal_creacion,
    }
    return render(request, 'app/configuracion.html', context)

