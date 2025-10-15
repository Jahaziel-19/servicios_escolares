import json
from django.shortcuts import render, get_object_or_404, redirect
from .models import Formulario, RespuestaFormulario
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def lista_formularios(request):
    formularios = Formulario.objects.all()
    return render(request, 'formbuilder/formularios_list.html', {'formularios': formularios})

@login_required
def crear_formulario(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        # Campos vienen como JSON string desde textarea o input hidden
        import json
        campos_json = request.POST.get('campos_json', '[]')
        try:
            campos = json.loads(campos_json)
        except:
            campos = []
        formulario = Formulario.objects.create(nombre=nombre, descripcion=descripcion, fields=campos)
        return redirect('formbuilder:formulario_creado', formulario_id=formulario.id)
    return render(request, 'formbuilder/crear_formulario.html')

@login_required
def formulario_creado(request, formulario_id):
    formulario = get_object_or_404(Formulario, id=formulario_id)
    return render(request, 'formbuilder/formulario_creado.html', {'formulario': formulario})

@login_required
def editar_formulario(request, formulario_id):
    formulario = get_object_or_404(Formulario, id=formulario_id)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        campos_json = request.POST.get('campos_json', '[]')
        try:
            campos = json.loads(campos_json)
        except Exception:
            campos = []
        formulario.nombre = nombre
        formulario.descripcion = descripcion
        formulario.fields = campos
        formulario.save()
        return redirect('formbuilder:listar_formularios')
    # Pasa los campos como JSON seguro al template
    campos_json = json.dumps(formulario.fields)
    return render(request, 'formbuilder/editar_formulario.html', {
        'formulario': formulario,
        'campos_json': campos_json
    })

@login_required
def eliminar_formulario(request, formulario_id):
    formulario = get_object_or_404(Formulario, id=formulario_id)
    if request.method == 'POST':
        formulario.delete()
        messages.success(request, 'Formulario eliminado correctamente.')
        return redirect('formbuilder:listar_formularios')
    return render(request, 'formbuilder/eliminar_formulario.html', {'formulario': formulario})
    
@login_required
def responder_formulario(request, formulario_id):
    formulario = get_object_or_404(Formulario, id=formulario_id)
    campos = formulario.fields

    if request.method == 'POST':
        respuestas = {}
        for campo in campos:
            campo_id = campo['id']
            # Para checkbox, puede venir como lista
            if campo['type'] == 'checkbox':
                valor = request.POST.getlist(campo_id)
            else:
                valor = request.POST.get(campo_id)
            respuestas[campo_id] = valor
        RespuestaFormulario.objects.create(formulario=formulario, datos=respuestas)
        return redirect('formbuilder:gracias')

    return render(request, 'formbuilder/responder_formulario.html', {'formulario': formulario, 'campos': campos})

@login_required
def gracias(request):
    return render(request, 'formbuilder/gracias.html')

@login_required
def ver_respuestas(request, formulario_id):
    formulario = get_object_or_404(Formulario, id=formulario_id)
    respuestas = formulario.respuestas.all().order_by('-fecha_respuesta')
    return render(request, 'formbuilder/ver_respuestas.html', {'formulario': formulario, 'respuestas': respuestas})

@login_required
def importar_formulario(request):
    if request.method == 'POST':
        archivo = request.FILES.get('archivo_json')
        if not archivo:
            messages.error(request, "No se seleccionó ningún archivo.")
            return redirect('formbuilder:crear_formulario')
        try:
            data = json.load(archivo)
            nombre = data.get('nombre')
            descripcion = data.get('descripcion', '')
            fields = data.get('fields', [])
            if not nombre or not isinstance(fields, list):
                messages.error(request, "Archivo JSON inválido.")
                return redirect('formbuilder:crear_formulario')
            Formulario.objects.create(nombre=nombre, descripcion=descripcion, fields=fields)
            messages.success(request, "Formulario importado correctamente.")
            return redirect('formbuilder:formulario_creado')
        except Exception as e:
            messages.error(request, f"Error al importar JSON: {str(e)}")
            return redirect('formbuilder:crear_formulario')
    return redirect('formbuilder:crear_formulario')

@login_required
def exportar_formulario(request, formulario_id):
    formulario = get_object_or_404(Formulario, id=formulario_id)
    data = {
        'nombre': formulario.nombre,
        'descripcion': formulario.descripcion,
        'fields': formulario.fields,
    }
    response = HttpResponse(
        json.dumps(data, ensure_ascii=False, indent=2),
        content_type='application/json'
    )
    filename = f"{formulario.nombre or 'formulario'}.json".replace(" ", "_")
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response