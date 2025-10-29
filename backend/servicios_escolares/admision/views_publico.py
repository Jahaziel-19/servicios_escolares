from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.db import transaction
import json
import logging

from .models import PeriodoAdmision, SolicitudAdmision
from .forms_publico import RegistroAspiranteForm, ConsultaSolicitudForm
from .email_utils import enviar_confirmacion_registro
import re

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Obtiene la IP del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@never_cache
def registro_aspirante(request):
    """
    Vista principal para el registro de aspirantes
    Formulario público, moderno y fácil de usar
    """
    # Obtener el período de admisión activo
    try:
        periodo_activo = PeriodoAdmision.objects.get(activo=True)
    except PeriodoAdmision.DoesNotExist:
        return render(request, 'admision/no_periodo_activo.html', {
            'title': 'Proceso de Admisión No Disponible'
        })
    
    # Verificar si el período está abierto
    if not periodo_activo.esta_abierto:
        return render(request, 'admision/periodo_cerrado.html', {
            'periodo': periodo_activo,
            'title': 'Periodo de Admisión Cerrado'
        })
    
    form = RegistroAspiranteForm(periodo=periodo_activo)
    form_errors_json = None
    form_errors_json_str = None
    
    if request.method == 'POST':
        form = RegistroAspiranteForm(request.POST, periodo=periodo_activo)
        
        if form.is_valid():
            # Prevenir duplicados de CURP en el mismo período (constraint de modelo)
            if SolicitudAdmision.objects.filter(periodo=periodo_activo, curp=form.cleaned_data['curp']).exists():
                form.add_error('curp', 'Ya existe una solicitud registrada con este CURP en el período actual.')
                messages.error(request, 'Ya existe una solicitud registrada con este CURP en el período actual.')
                logger.warning(f"Intento duplicado de registro para CURP {form.cleaned_data['curp']} en período {periodo_activo}")
            else:
                try:
                    with transaction.atomic():
                        # Crear la solicitud de admisión
                        solicitud = SolicitudAdmision(
                            periodo=periodo_activo,
                            curp=form.cleaned_data['curp'],
                            email=form.cleaned_data['email'],
                            respuestas_json=form.get_respuestas_json(),
                            ip_registro=get_client_ip(request),
                            estado='enviada'  # Cambiar de 'borrador' a 'enviada'
                        )
                        solicitud.save()
                        
                        # Enviar correo de confirmación
                        try:
                            enviar_confirmacion_registro(solicitud)
                            logger.info(f"Correo de confirmación enviado para solicitud {solicitud.folio}")
                        except Exception as e:
                            logger.error(f"Error enviando correo de confirmación: {str(e)}")
                            # No fallar el registro por error de email
                        
                        # Mensaje de éxito
                        messages.success(
                            request, 
                            f'¡Registro exitoso! Tu folio es: {solicitud.folio}. '
                            f'Revisa tu correo electrónico para más información.'
                        )
                        
                        return redirect('admision:admision_publico:registro_exitoso', folio=solicitud.folio)
                        
                except Exception as e:
                    logger.error(f"Error en registro de aspirante: {str(e)}")
                    messages.error(
                        request, 
                        'Ocurrió un error al procesar tu registro. Por favor, intenta nuevamente.'
                    )
        else:
            messages.error(
                request, 
                'Por favor, corrige los errores en el formulario.'
            )
            # Preparar errores en JSON para mostrarlos en la interfaz
            try:
                form_errors_json = form.errors.get_json_data()
                form_errors_json_str = json.dumps(form_errors_json, ensure_ascii=False)
            except Exception:
                form_errors_json = None
                form_errors_json_str = None
            # Añadir mensajes específicos por campo para mayor claridad
            try:
                for field_name, error_list in form.errors.items():
                    # Obtener etiqueta amigable
                    label = form.fields.get(field_name).label if field_name in form.fields else field_name
                    # Unir mensajes
                    mensajes = ', '.join([str(e) for e in error_list])
                    messages.error(request, f"{label}: {mensajes}")
            except Exception:
                pass
    
    # Estadísticas para mostrar en la página
    estadisticas = {
        'total_solicitudes': SolicitudAdmision.objects.filter(periodo=periodo_activo).count(),
        'solicitudes_hoy': SolicitudAdmision.objects.filter(
            periodo=periodo_activo,
            fecha_registro__date=timezone.now().date()
        ).count(),
        'dias_restantes': max(0, (periodo_activo.fecha_fin.date() - timezone.now().date()).days)
    }
    
    context = {
        'form': form,
        'periodo': periodo_activo,
        'form_errors_json': form_errors_json,
        'form_errors_json_str': form_errors_json_str,
        'estadisticas': estadisticas,
        'title': f'Registro de Aspirantes - {periodo_activo.nombre}',
        'meta_description': f'Regístrate para el proceso de admisión {periodo_activo.nombre}. Formulario oficial y seguro.'
    }
    
    return render(request, 'admision/publico/registro_aspirante.html', context)


@never_cache
def registro_exitoso(request, folio):
    """
    Página de confirmación después del registro exitoso
    """
    try:
        solicitud = get_object_or_404(SolicitudAdmision, folio=folio)
    except Http404:
        messages.error(request, 'No se encontró la solicitud especificada.')
        return redirect('admision:registro_aspirante')
    
    context = {
        'solicitud': solicitud,
        'title': 'Registro Exitoso',
        'nombre_completo': solicitud.get_nombre_completo()
    }
    
    return render(request, 'admision/publico/registro_exitoso.html', context)


@never_cache
def consultar_solicitud(request):
    """
    Vista para que los aspirantes consulten el estado de su solicitud
    """
    form = ConsultaSolicitudForm()
    solicitud = None
    
    if request.method == 'POST':
        form = ConsultaSolicitudForm(request.POST)
        
        if form.is_valid():
            tipo = form.cleaned_data['tipo_busqueda']
            valor = form.cleaned_data['valor_busqueda'].strip().upper()
            
            try:
                if tipo == 'folio':
                    # Normalizar el folio para aceptar variaciones con/sin guiones
                    valor_nodash = re.sub(r'[^A-Z0-9]', '', valor)
                    candidatos = [valor]
                    if re.match(r'^ADM\d{4}\d{6}$', valor_nodash):
                        candidatos.append(f"ADM-{valor_nodash[3:7]}-{valor_nodash[7:]}")
                    candidatos.append(valor_nodash)
                    encontrada = False
                    for f in candidatos:
                        try:
                            solicitud = SolicitudAdmision.objects.get(folio=f)
                            encontrada = True
                            break
                        except SolicitudAdmision.DoesNotExist:
                            continue
                    if not encontrada:
                        raise SolicitudAdmision.DoesNotExist
                else:  # tipo == 'curp'
                    solicitud = SolicitudAdmision.objects.get(curp=valor)
                    
            except SolicitudAdmision.DoesNotExist:
                messages.error(
                    request, 
                    'No se encontró ninguna solicitud con los datos proporcionados.'
                )
            except SolicitudAdmision.MultipleObjectsReturned:
                messages.error(
                    request, 
                    'Se encontraron múltiples solicitudes. Por favor, contacta al departamento de admisiones.'
                )
    
    context = {
        'form': form,
        'solicitud': solicitud,
        'title': 'Consultar Solicitud de Admisión'
    }
    
    return render(request, 'admision/publico/consultar_solicitud.html', context)


def informacion_proceso(request):
    """
    Página informativa sobre el proceso de admisión
    """
    try:
        periodo_activo = PeriodoAdmision.objects.get(activo=True)
    except PeriodoAdmision.DoesNotExist:
        periodo_activo = None
    
    context = {
        'periodo': periodo_activo,
        'title': 'Información del Proceso de Admisión',
        'carreras': [
            {
                'codigo': 'IEM',
                'nombre': 'Ingeniería Electromecánica',
                'descripcion': 'Integra conocimientos eléctricos y mecánicos para sistemas automatizados.',
                'duracion': '9 semestres',
                'modalidades': ['Presencial']
            },
            {
                'codigo': 'IGEM',
                'nombre': 'Ingeniería en Gestión Empresarial',
                'descripcion': 'Desarrolla habilidades gerenciales y empresariales con enfoque tecnológico.',
                'duracion': '9 semestres',
                'modalidades': ['Presencial', 'Sabatino']
            },
            {
                'codigo': 'ILOG',
                'nombre': 'Ingeniería en Logística',
                'descripcion': 'Optimiza cadenas de suministro y procesos logísticos empresariales.',
                'duracion': '9 semestres',
                'modalidades': ['Presencial']
            },
            {
                'codigo': 'IQUI',
                'nombre': 'Ingeniería Química',
                'descripcion': 'Estudia y desarrolla procesos químicos para aplicaciones industriales.',
                'duracion': '9 semestres',
                'modalidades': ['Presencial']
            },            
            {
                'codigo': 'IMAT',
                'nombre': 'Ingeniería en Materiales',
                'descripcion': 'Investiga y desarrolla nuevos materiales para aplicaciones industriales.',
                'duracion': '9 semestres',
                'modalidades': ['Presencial']
            }
        ]
    }
    
    return render(request, 'admision/publico/informacion_proceso.html', context)


# ========== VISTAS AJAX ==========

@csrf_protect
def ajax_validar_curp(request):
    """
    Valida si un CURP ya está registrado (AJAX)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    curp = request.POST.get('curp', '').upper().strip()
    
    if not curp or len(curp) != 18:
        return JsonResponse({
            'valido': False,
            'mensaje': 'CURP debe tener 18 caracteres'
        })
    
    try:
        periodo_activo = PeriodoAdmision.objects.get(activo=True)
        existe = SolicitudAdmision.objects.filter(
            curp=curp,
            periodo=periodo_activo
        ).exists()
        
        if existe:
            return JsonResponse({
                'valido': False,
                'mensaje': 'Este CURP ya está registrado en el proceso actual'
            })
        else:
            return JsonResponse({
                'valido': True,
                'mensaje': 'CURP disponible'
            })
            
    except PeriodoAdmision.DoesNotExist:
        return JsonResponse({
            'valido': False,
            'mensaje': 'No hay proceso de admisión activo'
        })
    except Exception as e:
        logger.error(f"Error validando CURP: {str(e)}")
        return JsonResponse({
            'valido': False,
            'mensaje': 'Error interno del servidor'
        })


@csrf_protect
def ajax_validar_email(request):
    """
    Valida si un email ya está registrado (AJAX)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    email = request.POST.get('email', '').lower().strip()
    
    if not email:
        return JsonResponse({
            'valido': False,
            'mensaje': 'Email requerido'
        })
    
    try:
        periodo_activo = PeriodoAdmision.objects.get(activo=True)
        existe = SolicitudAdmision.objects.filter(
            email=email,
            periodo=periodo_activo
        ).exists()
        
        if existe:
            return JsonResponse({
                'valido': False,
                'mensaje': 'Este correo ya está registrado en el proceso actual'
            })
        else:
            return JsonResponse({
                'valido': True,
                'mensaje': 'Email disponible'
            })
            
    except PeriodoAdmision.DoesNotExist:
        return JsonResponse({
            'valido': False,
            'mensaje': 'No hay proceso de admisión activo'
        })
    except Exception as e:
        logger.error(f"Error validando email: {str(e)}")
        return JsonResponse({
            'valido': False,
            'mensaje': 'Error interno del servidor'
        })


def ajax_estadisticas_proceso(request):
    """
    Devuelve estadísticas del proceso de admisión en tiempo real (AJAX)
    """
    try:
        periodo_activo = PeriodoAdmision.objects.get(activo=True)
        
        estadisticas = {
            'total_solicitudes': SolicitudAdmision.objects.filter(periodo=periodo_activo).count(),
            'solicitudes_enviadas': SolicitudAdmision.objects.filter(
                periodo=periodo_activo, 
                estado='enviada'
            ).count(),
            'solicitudes_en_revision': SolicitudAdmision.objects.filter(
                periodo=periodo_activo, 
                estado='en_revision'
            ).count(),
            'solicitudes_aceptadas': SolicitudAdmision.objects.filter(
                periodo=periodo_activo, 
                estado='aceptada'
            ).count(),
            'dias_restantes': max(0, (periodo_activo.fecha_fin.date() - timezone.now().date()).days),
            'proceso_abierto': periodo_activo.esta_abierto
        }
        
        return JsonResponse(estadisticas)
        
    except PeriodoAdmision.DoesNotExist:
        return JsonResponse({
            'error': 'No hay proceso de admisión activo'
        }, status=404)
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        return JsonResponse({
            'error': 'Error interno del servidor'
        }, status=500)


@csrf_protect
def ajax_reenviar_ficha(request):
    """
    Reenvía la ficha de admisión por correo electrónico (AJAX)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    folio = request.POST.get('folio', '').strip()
    
    if not folio:
        return JsonResponse({
            'success': False,
            'message': 'Folio requerido'
        })
    
    try:
        # Buscar la solicitud
        solicitud = SolicitudAdmision.objects.get(folio=folio)
        
        # Verificar que la solicitud esté aceptada
        if solicitud.estado != 'aceptada':
            return JsonResponse({
                'success': False,
                'message': 'Solo se pueden enviar fichas de solicitudes aceptadas'
            })
        
        # Verificar si ya tiene ficha generada
        try:
            ficha = solicitud.ficha
        except:
            # Si no tiene ficha, crear una nueva
            from .models import FichaAdmision
            from django.utils import timezone
            from datetime import timedelta
            
            ficha = FichaAdmision.objects.create(
                solicitud=solicitud,
                fecha_examen=timezone.now().date() + timedelta(days=30),
                hora_examen=timezone.now().time().replace(hour=9, minute=0),
                lugar_examen='Por definir'
            )
        
        # Enviar por email
        from .email_utils import enviar_ficha_por_email
        
        try:
            enviar_ficha_por_email(solicitud)
            
            # Marcar como enviado
            ficha.email_enviado = True
            ficha.fecha_envio_email = timezone.now()
            ficha.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Ficha enviada exitosamente a tu correo electrónico'
            })
            
        except Exception as e:
            logger.error(f"Error enviando ficha por email: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Error al enviar el correo. Inténtalo más tarde.'
            })
            
    except SolicitudAdmision.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Solicitud no encontrada'
        })
    except Exception as e:
        logger.error(f"Error reenviando ficha: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Error interno del servidor'
        })


@never_cache
def correccion_seleccionado_inicio(request):
    """
    Paso 1: Página para ingresar el folio y validar que el aspirante
    tiene estado 'seleccionado'. Si es válido, redirige al formulario.
    """
    if request.method == 'POST':
        folio = request.POST.get('folio', '').strip().upper()
        if not folio:
            messages.error(request, 'Ingresa tu folio para continuar.')
            return render(request, 'admision/publico/correccion_seleccionado_inicio.html', {
                'title': 'Corrección de Datos (Seleccionados)'
            })
        # Normalizar variaciones de folio con/sin guiones
        valor_nodash = re.sub(r'[^A-Z0-9]', '', folio)
        candidatos = [folio]
        if re.match(r'^ADM\d{4}\d{6}$', valor_nodash):
            candidatos.append(f"ADM-{valor_nodash[3:7]}-{valor_nodash[7:]}")
        candidatos.append(valor_nodash)
        solicitud = None
        for f in candidatos:
            try:
                solicitud = SolicitudAdmision.objects.get(folio=f)
                break
            except SolicitudAdmision.DoesNotExist:
                continue
        if not solicitud:
            messages.error(request, 'No encontramos una solicitud con ese folio.')
            return render(request, 'admision/publico/correccion_seleccionado_inicio.html', {
                'title': 'Corrección de Datos (Seleccionados)'
            })
        if solicitud.estado != 'seleccionado':
            messages.warning(request, 'Esta opción solo está disponible para aspirantes con estado "Seleccionado".')
            return render(request, 'admision/publico/correccion_seleccionado_inicio.html', {
                'title': 'Corrección de Datos (Seleccionados)'
            })
        return redirect('admision:admision_publico:correccion_seleccionado_form', folio=solicitud.folio)
    # GET
    return render(request, 'admision/publico/correccion_seleccionado_inicio.html', {
        'title': 'Corrección de Datos (Seleccionados)'
    })


@never_cache
def correccion_seleccionado_form(request, folio):
    """
    Paso 2: Formulario con estilo de RegistroAspirante, autocompletado
    con los datos existentes de la solicitud (respuestas_json) para permitir
    correcciones. Solo válido para estado 'seleccionado'.
    """
    solicitud = get_object_or_404(SolicitudAdmision, folio=folio)
    if solicitud.estado != 'seleccionado':
        messages.warning(request, 'Esta opción solo está disponible para aspirantes con estado "Seleccionado".')
        return redirect('admision:admision_publico:correccion_seleccionado_inicio')

    # Preparar datos iniciales desde respuestas_json
    initial = dict(solicitud.respuestas_json or {})
    # Asegurar curp y email de nivel superior
    initial['curp'] = solicitud.curp or initial.get('curp', '')
    initial['email'] = solicitud.email or initial.get('email', '')

    # Cargar form
    if request.method == 'POST':
        form = RegistroAspiranteForm(request.POST, periodo=solicitud.periodo)
        form_errors_json = None
        form_errors_json_str = None
        if form.is_valid():
            try:
                solicitud.curp = form.cleaned_data.get('curp', '').upper()
                solicitud.email = form.cleaned_data.get('email', '')
                solicitud.respuestas_json = form.get_respuestas_json()
                solicitud.save()
                messages.success(request, 'Tus datos han sido actualizados correctamente.')
                return redirect('admision:admision_publico:correccion_exitoso', folio=solicitud.folio)
            except Exception as e:
                logger.error(f"Error al guardar corrección: {str(e)}")
                messages.error(request, 'Ocurrió un error al guardar tus cambios. Intenta nuevamente.')
                # Preparar errores JSON si es posible
                try:
                    form_errors_json = form.errors.get_json_data()
                    form_errors_json_str = json.dumps(form_errors_json, ensure_ascii=False)
                except Exception:
                    pass
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
            try:
                form_errors_json = form.errors.get_json_data()
                form_errors_json_str = json.dumps(form_errors_json, ensure_ascii=False)
            except Exception:
                pass
        return render(request, 'admision/publico/registro_aspirante.html', {
            'form': form,
            'title': 'Corrección de Datos de Aspirante',
            'form_errors_json': form_errors_json,
            'form_errors_json_str': form_errors_json_str,
        })
    else:
        form = RegistroAspiranteForm(periodo=solicitud.periodo, initial=initial)
        return render(request, 'admision/publico/registro_aspirante.html', {
            'form': form,
            'title': 'Corrección de Datos de Aspirante'
        })


@never_cache
def correccion_exitoso(request, folio):
    """
    Confirmación estilizada después de guardar correcciones.
    """
    solicitud = get_object_or_404(SolicitudAdmision, folio=folio)
    return render(request, 'admision/publico/correccion_exitoso.html', {
        'solicitud': solicitud,
        'title': 'Corrección Exitosa'
    })