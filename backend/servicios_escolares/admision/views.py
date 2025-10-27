from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from .models import (
    PeriodoAdmision, FormularioAdmision, SolicitudAdmision, 
    FichaAdmision, ConfiguracionAdmision
)
from .forms import FormularioDinamicoAdmision, SolicitudAdmisionForm
import re
import json


def solicitud_admision(request):
    """Vista principal para que los aspirantes llenen su solicitud"""
    # Obtener el período activo
    periodo_activo = PeriodoAdmision.objects.filter(activo=True).first()
    
    if not periodo_activo:
        return render(request, 'admision/no_periodo_activo.html')
    
    if not periodo_activo.esta_abierto:
        return render(request, 'admision/periodo_cerrado.html', {
            'periodo': periodo_activo
        })
    
    # Verificar que el período tenga formulario base configurado
    if not periodo_activo.formulario_base or not periodo_activo.formulario_base.get('campos'):
        return render(request, 'admision/formulario_no_configurado.html', {
            'periodo': periodo_activo
        })
    
    if request.method == 'POST':
        return _procesar_solicitud_post(request, periodo_activo)
    
    # GET: Mostrar formulario usando formulario_base
    form = FormularioDinamicoAdmision(periodo=periodo_activo)
    
    return render(request, 'admision/solicitud_form.html', {
        'form': form,
        'periodo': periodo_activo,
        'formulario_config': periodo_activo.formulario_base
    })


def _procesar_solicitud_post(request, periodo):
    """Procesa el envío del formulario de solicitud"""
    form = FormularioDinamicoAdmision(request.POST, request.FILES, periodo=periodo)
    
    if form.is_valid():
        try:
            with transaction.atomic():
                # Crear la solicitud
                solicitud = SolicitudAdmision(
                    periodo=periodo,
                    curp=form.cleaned_data.get('curp', '').upper(),
                    email=form.cleaned_data.get('email', ''),
                    respuestas_json=form.get_respuestas_json(),
                    estado='enviada',
                    ip_registro=_get_client_ip(request)
                )
                solicitud.save()
                
                # Generar ficha automáticamente
                ficha = FichaAdmision.objects.create(solicitud=solicitud)
                
                messages.success(request, f'¡Solicitud enviada exitosamente! Tu folio es: {solicitud.folio}')
                return redirect('admision:solicitud_exitosa', folio=solicitud.folio)
                
        except ValidationError as e:
            for field, errors in e.message_dict.items():
                for error in errors:
                    form.add_error(field, error)
        except Exception as e:
            messages.error(request, f'Error al procesar la solicitud: {str(e)}')
    
    return render(request, 'admision/solicitud_form.html', {
        'form': form,
        'periodo': periodo_activo,
        'formulario_config': periodo_activo.formulario_base
    })


def solicitud_exitosa(request, folio):
    """Vista de confirmación después de enviar la solicitud"""
    solicitud = get_object_or_404(SolicitudAdmision, folio=folio)
    
    return render(request, 'admision/solicitud_exitosa.html', {
        'solicitud': solicitud
    })


def consultar_solicitud(request):
    """Vista para que los aspirantes consulten su solicitud"""
    solicitud = None
    
    if request.method == 'POST':
        folio = request.POST.get('folio', '').strip().upper()
        curp = request.POST.get('curp', '').strip().upper()
        
        if folio and curp:
            # Normalizar el folio para aceptar variaciones con/sin guiones
            folio_nodash = re.sub(r'[^A-Z0-9]', '', folio)
            candidatos = [folio]
            # Si el folio sin guiones coincide con ADMYYYY######, reconstruir el formato con guiones
            if re.match(r'^ADM\d{4}\d{6}$', folio_nodash):
                candidatos.append(f"ADM-{folio_nodash[3:7]}-{folio_nodash[7:]}")
            # Intentar también sin guiones
            candidatos.append(folio_nodash)
            
            encontrada = False
            for f in candidatos:
                try:
                    solicitud = SolicitudAdmision.objects.get(folio=f, curp=curp)
                    encontrada = True
                    break
                except SolicitudAdmision.DoesNotExist:
                    continue
            if not encontrada:
                messages.error(request, 'No se encontró una solicitud con esos datos.')
    
    return render(request, 'admision/consultar_solicitud.html', {
        'solicitud': solicitud
    })


def editar_solicitud(request, folio):
    """Vista para editar una solicitud existente (solo si está en borrador)"""
    solicitud = get_object_or_404(SolicitudAdmision, folio=folio)
    
    # Solo permitir edición si está en borrador y el período está abierto
    if solicitud.estado != 'borrador':
        messages.error(request, 'Esta solicitud ya no puede ser editada.')
        return redirect('admision:consultar_solicitud')
    
    if not solicitud.periodo.esta_abierto:
        messages.error(request, 'El período de admisión ha cerrado.')
        return redirect('admision:consultar_solicitud')
    
    if request.method == 'POST':
        form = FormularioDinamicoAdmision(
            request.POST, request.FILES, 
            periodo=solicitud.periodo, 
            solicitud=solicitud
        )
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    solicitud.curp = form.cleaned_data.get('curp', '').upper()
                    solicitud.email = form.cleaned_data.get('email', '')
                    solicitud.respuestas_json = form.get_respuestas_json()
                    solicitud.save()
                    
                    messages.success(request, 'Solicitud actualizada exitosamente.')
                    return redirect('admision:consultar_solicitud')
                    
            except ValidationError as e:
                for field, errors in e.message_dict.items():
                    for error in errors:
                        form.add_error(field, error)
    else:
        form = FormularioDinamicoAdmision(
            periodo=solicitud.periodo, 
            solicitud=solicitud
        )
    
    return render(request, 'admision/editar_solicitud.html', {
        'form': form,
        'solicitud': solicitud,
        'periodo': solicitud.periodo,
        'formulario_config': solicitud.periodo.formulario_base
    })


@login_required
def admin_visualizar_formulario(request, formulario_id):
    """Vista moderna para visualizar un formulario con interfaz mejorada"""
    from formbuilder.models import Formulario
    import json
    
    formulario = get_object_or_404(Formulario, id=formulario_id)
    
    # Parsear campos JSON
    campos_parseados = []
    if formulario.fields:
        try:
            campos_parseados = json.loads(formulario.fields) if isinstance(formulario.fields, str) else formulario.fields
        except (json.JSONDecodeError, TypeError):
            campos_parseados = []
    
    # Obtener estadísticas básicas
    total_campos = len(campos_parseados)
    campos_requeridos = 0
    tipos_campos = {}
    
    if campos_parseados:
        for campo in campos_parseados:
            if campo.get('required', False):
                campos_requeridos += 1
            
            tipo = campo.get('type', 'unknown')
            tipos_campos[tipo] = tipos_campos.get(tipo, 0) + 1
    
    # Obtener respuestas relacionadas
    respuestas_count = formulario.respuestas.count() if hasattr(formulario, 'respuestas') else 0
    
    context = {
        'formulario': formulario,
        'total_campos': total_campos,
        'campos_requeridos': campos_requeridos,
        'tipos_campos': tipos_campos,
        'respuestas_count': respuestas_count,
        'campos_json': json.dumps(campos_parseados),
    }
    
    return render(request, 'admision/admin/visualizar_formulario.html', context)


@login_required
def admin_dashboard(request):
    """Dashboard administrativo para el sistema de admisión"""
    # Estadísticas generales
    periodo_activo = PeriodoAdmision.objects.filter(activo=True).first()
    
    stats = {
        'total_solicitudes': SolicitudAdmision.objects.count(),
        'solicitudes_periodo_activo': 0,
        'fichas_generadas': FichaAdmision.objects.count(),
        'emails_enviados': FichaAdmision.objects.filter(email_enviado=True).count(),
    }
    
    if periodo_activo:
        stats['solicitudes_periodo_activo'] = SolicitudAdmision.objects.filter(
            periodo=periodo_activo
        ).count()
    
    # Conteo por estado para gráfica y resumen
    estados = SolicitudAdmision.ESTADOS
    conteos_estados = []
    resumen_por_estado = {}
    for code, _name in estados:
        count = SolicitudAdmision.objects.filter(estado=code).count()
        conteos_estados.append(count)
        resumen_por_estado[code] = count
    
    # Solicitudes recientes
    solicitudes_recientes = SolicitudAdmision.objects.select_related('periodo').order_by('-fecha_registro')[:10]
    
    return render(request, 'admision/admin/dashboard.html', {
        'stats': stats,
        'periodo_activo': periodo_activo,
        'solicitudes_recientes': solicitudes_recientes,
        'estados': estados,
        'conteos_estados': conteos_estados,
        'resumen_por_estado': resumen_por_estado,
    })


@login_required
def admin_solicitudes(request):
    """Vista para administrar todas las solicitudes"""
    # Filtros
    periodo_id = request.GET.get('periodo')
    estado = request.GET.get('estado')
    busqueda = request.GET.get('q')
    
    solicitudes = SolicitudAdmision.objects.select_related('periodo').order_by('-fecha_registro')
    
    if periodo_id:
        solicitudes = solicitudes.filter(periodo_id=periodo_id)
    
    if estado:
        solicitudes = solicitudes.filter(estado=estado)
    
    if busqueda:
        solicitudes = solicitudes.filter(
            models.Q(folio__icontains=busqueda) |
            models.Q(curp__icontains=busqueda) |
            models.Q(email__icontains=busqueda)
        )
    
    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(solicitudes, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Datos para filtros
    periodos = PeriodoAdmision.objects.filter(activo=True).order_by('-año')
    estados = SolicitudAdmision.ESTADOS
    
    return render(request, 'admision/admin/solicitudes.html', {
        'page_obj': page_obj,
        'periodos': periodos,
        'estados': estados,
        'filtros': {
            'periodo_id': periodo_id,
            'estado': estado,
            'busqueda': busqueda
        },
        'puede_accion_masiva': (
            request.user.is_staff or request.user.is_superuser or request.user.groups.filter(name__in=['ServiciosEscolares','Servicios Escolares']).exists()
        )
    })


@login_required
def admin_ver_solicitud(request, solicitud_id):
    """Vista detallada de una solicitud específica"""
    solicitud = get_object_or_404(SolicitudAdmision, id=solicitud_id)
    
    # Obtener la estructura del formulario para mostrar las respuestas
    formulario_config = solicitud.periodo.formulario_base
    
    return render(request, 'admision/admin/ver_solicitud.html', {
        'solicitud': solicitud,
        'formulario_config': formulario_config,
        'estados': SolicitudAdmision.ESTADOS
    })


@login_required
def admin_cambiar_estado_solicitud(request, solicitud_id):
    """Cambiar el estado de una solicitud"""
    if request.method != 'POST':
        return redirect('admision:admin_ver_solicitud', solicitud_id=solicitud_id)
    
    solicitud = get_object_or_404(SolicitudAdmision, id=solicitud_id)
    nuevo_estado = request.POST.get('nuevo_estado')
    
    # Validar que el estado sea válido
    estados_validos = [estado[0] for estado in SolicitudAdmision.ESTADOS]
    if nuevo_estado not in estados_validos:
        messages.error(request, 'Estado no válido.')
        return redirect('admision:admin_ver_solicitud', solicitud_id=solicitud_id)
    
    # Actualizar el estado
    estado_anterior = solicitud.get_estado_display()
    solicitud.estado = nuevo_estado
    solicitud.save()
    
    # Mensaje de confirmación
    nuevo_estado_display = dict(SolicitudAdmision.ESTADOS)[nuevo_estado]
    messages.success(
        request, 
        f'Estado cambiado de "{estado_anterior}" a "{nuevo_estado_display}" exitosamente.'
    )
    
    return redirect('admision:admin_ver_solicitud', solicitud_id=solicitud_id)


@login_required
def admin_generar_ficha(request, solicitud_id):
    """Generar ficha de admisión para una solicitud"""
    from .utils import generar_ficha_admision_pdf
    from django.core.files.base import ContentFile
    
    solicitud = get_object_or_404(SolicitudAdmision, id=solicitud_id)
    
    try:
        # Verificar si ya tiene ficha (hasattr siempre es True en OneToOne)
        if FichaAdmision.objects.filter(solicitud=solicitud).exists():
            messages.info(request, 'Esta solicitud ya tiene una ficha generada.')
        else:
            # Crear la ficha
            ficha = FichaAdmision.objects.create(
                solicitud=solicitud,
                generada_por=request.user
            )
            
            # Generar el PDF y guardarlo
            pdf_content = generar_ficha_admision_pdf(solicitud)
            filename = f"ficha_{ficha.numero_ficha}.pdf"
            
            # Guardar el archivo PDF en el modelo
            ficha.archivo_pdf.save(
                filename,
                ContentFile(pdf_content),
                save=True
            )
            
            messages.success(request, f'Ficha generada: {ficha.numero_ficha}. Puede descargarla o enviarla por email.')
    
    except Exception as e:
        messages.error(request, f'Error al generar la ficha: {str(e)}')
    
    return redirect('admision:admin_ver_solicitud', solicitud_id=solicitud.id)


@login_required
def admin_descargar_ficha(request, ficha_id):
    """Descargar ficha de admisión en PDF"""
    from .utils import crear_respuesta_pdf_ficha
    
    ficha = get_object_or_404(FichaAdmision, id=ficha_id)
    
    try:
        # Generar y retornar el PDF
        return crear_respuesta_pdf_ficha(
            ficha.solicitud, 
            filename=f"Ficha_Admision_{ficha.numero_ficha}.pdf"
        )
    except Exception as e:
        messages.error(request, f'Error al generar el PDF: {str(e)}')
        return redirect('admision:admin_ver_solicitud', solicitud_id=ficha.solicitud.id)


@login_required
def admin_enviar_ficha_email(request, solicitud_id):
    """Enviar ficha de admisión por email desde el panel admin (con adjuntos opcionales)"""
    solicitud = get_object_or_404(SolicitudAdmision, id=solicitud_id)
    from .email_utils import enviar_ficha_por_email
    
    if request.method == 'POST':
        adjuntos = request.FILES.getlist('adjuntos')
        try:
            ok, msg = enviar_ficha_por_email(solicitud, usuario_que_envia=request.user, adjuntos=adjuntos)
            if ok:
                messages.success(request, msg)
            else:
                messages.warning(request, msg)
            return redirect('admision:admin_ver_solicitud', solicitud_id=solicitud.id)
        except Exception as e:
            messages.error(request, f'Error al enviar la ficha por email: {str(e)}')
            return redirect('admision:admin_ver_solicitud', solicitud_id=solicitud.id)
    
    # GET: Renderizar formulario para adjuntar PDFs adicionales
    return render(request, 'admision/admin/enviar_ficha_email.html', {
        'solicitud': solicitud,
    })


def _get_client_ip(request):
    """Obtiene la IP del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# API Views para funcionalidades AJAX

@csrf_exempt
@require_http_methods(["POST"])
def api_validar_curp(request):
    """API para validar CURP en tiempo real"""
    data = json.loads(request.body)
    curp = data.get('curp', '').upper()
    periodo_id = data.get('periodo_id')
    
    if not curp or not periodo_id:
        return JsonResponse({'valido': False, 'mensaje': 'Datos incompletos'})
    
    try:
        periodo = PeriodoAdmision.objects.get(id=periodo_id)
        existe = SolicitudAdmision.objects.filter(curp=curp, periodo=periodo).exists()
        
        return JsonResponse({
            'valido': not existe,
            'mensaje': 'CURP ya registrado en este período' if existe else 'CURP disponible'
        })
    
    except PeriodoAdmision.DoesNotExist:
        return JsonResponse({'valido': False, 'mensaje': 'Período no válido'})


@login_required
def api_estadisticas_periodo(request, periodo_id):
    """API para obtener estadísticas de un período específico"""
    periodo = get_object_or_404(PeriodoAdmision, id=periodo_id)
    
    solicitudes = SolicitudAdmision.objects.filter(periodo=periodo)
    
    stats = {
        'total_solicitudes': solicitudes.count(),
        'por_estado': {},
        'fichas_generadas': FichaAdmision.objects.filter(solicitud__periodo=periodo).count(),
        'emails_enviados': FichaAdmision.objects.filter(
            solicitud__periodo=periodo, 
            email_enviado=True
        ).count()
    }
    
    # Contar por estado
    for estado_code, estado_name in SolicitudAdmision.ESTADOS:
        stats['por_estado'][estado_name] = solicitudes.filter(estado=estado_code).count()
    
    return JsonResponse(stats)


# Vistas para gestión de formularios

@login_required
def admin_formularios(request):
    """Vista para listar todos los períodos de admisión con su formulario único"""
    
    # Obtener todos los períodos de admisión
    periodos = PeriodoAdmision.objects.all().order_by('-año', '-fecha_inicio')
    
    # Filtros opcionales
    search = request.GET.get('search', '')
    if search:
        periodos = periodos.filter(nombre__icontains=search)
    
    # Paginación directa sobre el QuerySet
    paginator = Paginator(periodos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Preparar información de formularios para la página actual
    periodos_con_formularios = []
    for periodo in page_obj:
        # Contar campos en el formulario base (excluyendo secciones)
        campos_count = 0
        if periodo.formulario_base and periodo.formulario_base.get('campos'):
            campos_count = len([
                campo for campo in periodo.formulario_base.get('campos', [])
                if campo.get('type') != 'section'
            ])
        
        periodos_con_formularios.append({
            'periodo': periodo,
            'campos_count': campos_count,
            'tiene_formulario': bool(periodo.formulario_base and periodo.formulario_base.get('campos')),
            'formulario_configurado': bool(periodo.formulario_base and periodo.formulario_base.get('campos'))
        })
    
    # Crear un objeto que simule el comportamiento de page_obj pero con nuestros datos procesados
    class PaginatedPeriodos:
        def __init__(self, page_obj, periodos_data):
            self.object_list = periodos_data
            self.has_next = page_obj.has_next
            self.has_previous = page_obj.has_previous
            self.has_other_pages = page_obj.has_other_pages
            self.next_page_number = page_obj.next_page_number if page_obj.has_next() else None
            self.previous_page_number = page_obj.previous_page_number if page_obj.has_previous() else None
            self.number = page_obj.number
            self.paginator = page_obj.paginator
        
        def __iter__(self):
            """Hacer el objeto iterable para las plantillas Django"""
            return iter(self.object_list)
        
        def __len__(self):
            """Devolver la longitud de la lista"""
            return len(self.object_list)
    
    paginated_periodos = PaginatedPeriodos(page_obj, periodos_con_formularios)
    
    context = {
        'periodos_con_formularios': paginated_periodos,
        'total_periodos': paginator.count,
        'search': search,
    }
    
    return render(request, 'admision/admin/formularios.html', context)


@login_required
def admin_crear_formulario(request):
    """Vista para crear/editar el formulario base de un período de admisión"""
    import json
    
    # Obtener el período específico si se proporciona
    periodo_id = request.GET.get('periodo_id') or request.POST.get('periodo_id')
    periodo = None
    
    if periodo_id:
        periodo = get_object_or_404(PeriodoAdmision, id=periodo_id)
    
    if request.method == 'POST':
        campos_json = request.POST.get('campos_json', '[]')
        
        try:
            campos = json.loads(campos_json)
        except json.JSONDecodeError:
            campos = []
            messages.error(request, 'Error en el formato de los campos JSON.')
        
        if periodo:
            # Actualizar el formulario base del período
            periodo.formulario_base = {
                'nombre': f'Formulario de Admisión - {periodo.nombre}',
                'descripcion': f'Formulario específico para el proceso de admisión {periodo.nombre}',
                'campos': campos
            }
            periodo.save()
            
            messages.success(request, f'Formulario del período "{periodo.nombre}" actualizado exitosamente.')
            return redirect('admision:admin_editar_formulario', periodo_id=periodo.id)
        else:
            messages.error(request, 'Debe seleccionar un período de admisión.')
    
    # Obtener todos los períodos para selección
    periodos_disponibles = PeriodoAdmision.objects.all().order_by('-año', '-fecha_inicio')
    
    # Si hay un período seleccionado, obtener sus campos actuales
    campos_actuales = []
    if periodo and periodo.formulario_base:
        campos_actuales = periodo.formulario_base.get('campos', [])
    
    context = {
        'titulo': 'Configurar Formulario de Período',
        'accion': 'Configurar',
        'periodos_disponibles': periodos_disponibles,
        'periodo_seleccionado': periodo,
        'campos_actuales': campos_actuales,
        'campos_json': json.dumps(campos_actuales),
    }
    
    return render(request, 'admision/admin/crear_formulario.html', context)
    
    return render(request, 'admision/admin/crear_formulario.html', context)


@login_required
def admin_editar_formulario(request, periodo_id):
    """Vista para editar el formulario base de un período específico"""
    import json
    
    periodo = get_object_or_404(PeriodoAdmision, id=periodo_id)
    
    if request.method == 'POST':
        campos_json = request.POST.get('campos', '[]')  # Cambiado de 'campos_json' a 'campos'
        
        try:
            campos = json.loads(campos_json)
        except json.JSONDecodeError:
            campos = []
            messages.error(request, 'Error en el formato de los campos JSON.')
        
        # Actualizar el formulario base del período
        periodo.formulario_base = {
            'nombre': f'Formulario de Admisión - {periodo.nombre}',
            'descripcion': f'Formulario específico para el proceso de admisión {periodo.nombre}',
            'campos': campos
        }
        periodo.save()
        
        messages.success(request, f'Formulario del período "{periodo.nombre}" actualizado exitosamente.')
        return redirect('admision:admin_editar_formulario', periodo_id=periodo.id)
    
    # Obtener campos actuales del formulario base
    campos_actuales = []
    if periodo.formulario_base:
        campos_actuales = periodo.formulario_base.get('campos', [])
    
    context = {
        'titulo': f'Editar Formulario - {periodo.nombre}',
        'accion': 'Editar',
        'periodo': periodo,
        'campos': campos_actuales,
        'campos_json': json.dumps(campos_actuales),
    }
    
    return render(request, 'admision/admin/editar_formulario.html', context)


@login_required
def admin_ver_formulario(request, periodo_id):
    """Vista para ver el formulario base de un período específico"""
    import json
    
    periodo = get_object_or_404(PeriodoAdmision, id=periodo_id)
    
    # Obtener campos del formulario base
    campos_parseados = []
    if periodo.formulario_base:
        campos_parseados = periodo.formulario_base.get('campos', [])
    
    context = {
        'periodo': periodo,
        'campos': campos_parseados,
        'campos_json': json.dumps(campos_parseados),
        'titulo': f'Formulario - {periodo.nombre}',
    }
    
    return render(request, 'admision/admin/ver_formulario.html', context)


@login_required
def admin_preview_formulario(request, periodo_id):
    """Vista para previsualizar el formulario base de un período"""
    import json
    
    periodo = get_object_or_404(PeriodoAdmision, id=periodo_id)
    
    # Parsear campos del formulario base
    campos_parseados = []
    if periodo.formulario_base:
        campos_parseados = periodo.formulario_base.get('campos', [])
    
    context = {
        'periodo': periodo,
        'campos': campos_parseados,
        'campos_json': json.dumps(campos_parseados),
        'es_preview': True,
    }
    
    return render(request, 'admision/admin/preview_formulario.html', context)


# Fin de las vistas de gestión de formularios


@login_required
def admin_toggle_formulario_status(request, formulario_id):
    """Vista para activar/desactivar un formulario"""
    from formbuilder.models import Formulario
    import json
    
    if request.method == 'POST':
        formulario = get_object_or_404(Formulario, id=formulario_id)
        data = json.loads(request.body)
        nuevo_estado = data.get('activo', True)
        
        formulario.activo = nuevo_estado
        formulario.save()
        
        estado_texto = "activado" if nuevo_estado else "desactivado"
        
        return JsonResponse({
            'success': True,
            'message': f'Formulario {estado_texto} exitosamente.',
            'activo': formulario.activo
        })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)