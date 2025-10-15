import os
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.apps import apps
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Plantilla, VariablePlantilla
from .forms import PlantillaForm
from .utils import armar_contexto_para_alumno, armar_contexto_para_boleta
from docxtpl import DocxTemplate
from datetime import datetime
from django.http import HttpResponse
from io import BytesIO
from datos_academicos.models import Alumno, PeriodoEscolar
#from datetime import datetime, date

class listar_plantillas(LoginRequiredMixin, ListView):
    """
    List all templates available in the system.
    """
    model = Plantilla
    template_name = 'docsbuilder/listar_plantillas.html'
    context_object_name = 'plantillas'
    paginate_by = 10
    '''
    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '')
        if q:
            queryset = queryset.filter(nombre__icontains=q)
        return queryset.order_by('nombre')
    '''
'''
    def get_queryset(self):
        queryset = super().get_queryset().select_related('carrera')
        q = self.request.GET.get('q', '')
        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q) |
                Q(apellido_paterno__icontains=q) |
                Q(apellido_materno__icontains=q) |
                Q(matricula__icontains=q) |
                Q(carrera__nombre__icontains=q)
            )
        return queryset.order_by('matricula')  
'''

'''
def listar_plantillas(request):
    plantillas = Plantilla.objects.all()
    return render(request, 'docsbuilder/listar_plantillas.html', {'plantillas': plantillas})
'''
@login_required
def generar_boleta_tramite(request, plantilla_id, alumno_id, periodo_id):
    """
    Genera una boleta de calificaciones usando una plantilla Word personalizada
    """
    plantilla = get_object_or_404(Plantilla, id=plantilla_id)
    alumno = get_object_or_404(Alumno, id=alumno_id)
    periodo_escolar = get_object_or_404(PeriodoEscolar, id=periodo_id)
    variables = plantilla.variables.all()

    # Usar la función específica para boletas
    contexto = armar_contexto_para_boleta(alumno, periodo_escolar, variables)

    ruta_plantilla = plantilla.archivo.path
    doc = DocxTemplate(ruta_plantilla)
    doc.render(contexto)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    nombre_archivo = f"Boleta_{alumno.matricula}_{periodo_escolar.ciclo}_{periodo_escolar.año}.docx"

    # Registrar trámite de boleta
    from procedimientos.models import Tramite
    Tramite.objects.create(
        alumno=alumno,
        tipo='boleta',
        estado='Procesado',
        fecha_procesado=datetime.now(),
        plantilla=plantilla
    )

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'

    return response

@login_required
def subir_plantilla(request):
    if request.method == 'POST':
        form = PlantillaForm(request.POST, request.FILES)
        if form.is_valid():
            plantilla = form.save()
            ruta_archivo = os.path.join(settings.MEDIA_ROOT, plantilla.archivo.name)
            doc = DocxTemplate(ruta_archivo)
            variables = doc.get_undeclared_template_variables()
            for var in variables:
                VariablePlantilla.objects.create(plantilla=plantilla, nombre=var)
            return redirect('docsbuilder:mapeo_variables', plantilla_id=plantilla.id)
    else:
        form = PlantillaForm()
    return render(request, 'docsbuilder/subir_plantilla.html', {'form': form})


def obtener_campos_alumno():
    Alumno = apps.get_model('datos_academicos', 'Alumno')
    campos = [field.name for field in Alumno._meta.get_fields() if not field.auto_created]
    return campos

@login_required
def mapeo_variables(request, plantilla_id):
    plantilla = get_object_or_404(Plantilla, id=plantilla_id)
    variables = plantilla.variables.all()
    campos_alumno = obtener_campos_alumno()

    if request.method == 'POST':
        for variable in variables:
            tipo = request.POST.get(f'tipo_{variable.id}')
            variable.tipo = tipo
            if tipo == 'simple':
                variable.campo = request.POST.get(f'campo_{variable.id}') or None
                variable.especial_opcion = None
            elif tipo == 'especial':
                variable.especial_opcion = request.POST.get(f'especial_{variable.id}') or None
                variable.campo = None
            elif tipo == 'tabla':
                variable.campo = None
                variable.especial_opcion = None
            variable.save()
        return redirect('docsbuilder:listar_plantillas')

    return render(request, 'docsbuilder/mapeo_variables.html', {
        'plantilla': plantilla,
        'variables': variables,
        'campos_alumno': campos_alumno,
    })

@login_required
def generar_documento_tramite(request, plantilla_id, alumno_id):
    plantilla = get_object_or_404(Plantilla, id=plantilla_id)
    alumno = get_object_or_404(Alumno, id=alumno_id)
    variables = plantilla.variables.all()

    contexto = armar_contexto_para_alumno(alumno, variables)

    ruta_plantilla = plantilla.archivo.path  # Usa path para acceso directo
    doc = DocxTemplate(ruta_plantilla)
    doc.render(contexto)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    nombre_archivo = f"{plantilla.nombre}_{alumno.matricula}.docx"

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'

    return response

@login_required
def eliminar_plantilla(request, plantilla_id):
    plantilla = get_object_or_404(Plantilla, id=plantilla_id)
    plantilla.delete()
    return redirect('docsbuilder:listar_plantillas')