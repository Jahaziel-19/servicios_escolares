import os
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.utils.html import strip_tags
from .utils import generar_ficha_admision_pdf
import logging

logger = logging.getLogger(__name__)


def enviar_ficha_por_email(solicitud, usuario_que_envia=None):
    """
    Envía la ficha de admisión por correo electrónico al aspirante
    
    Args:
        solicitud: Instancia de SolicitudAdmision
        usuario_que_envia: Usuario que solicita el envío (opcional)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Verificar existencia de ficha de forma segura para OneToOne
        from .models import FichaAdmision
        if not FichaAdmision.objects.filter(solicitud=solicitud).exists():
            return False, "La solicitud no tiene una ficha generada"
        
        ficha = solicitud.ficha
        
        # Generar el PDF de la ficha
        pdf_content = generar_ficha_admision_pdf(solicitud)
        
        # Preparar el contexto para el template del email
        context = {
            'solicitud': solicitud,
            'ficha': ficha,
            'periodo': solicitud.periodo,
            'fecha_envio': timezone.now(),
            'institucion': getattr(settings, 'INSTITUCION_NOMBRE', 'Institución Educativa'),
            'contacto_email': getattr(settings, 'CONTACTO_ADMISIONES_EMAIL', 'admisiones@institucion.edu'),
            'contacto_telefono': getattr(settings, 'CONTACTO_ADMISIONES_TELEFONO', 'N/A'),
        }
        
        # Renderizar el template del email
        subject = f"Ficha de Admisión - {solicitud.folio} - {solicitud.periodo.nombre}"
        html_message = render_to_string('admision/emails/ficha_admision.html', context)
        text_message = render_to_string('admision/emails/ficha_admision.txt', context)
        
        # Crear el email como multipart (texto + HTML)
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@institucion.edu'),
            to=[solicitud.email],
            reply_to=[getattr(settings, 'CONTACTO_ADMISIONES_EMAIL', 'admisiones@institucion.edu')]
        )
        email.attach_alternative(html_message, "text/html")
        
        # Adjuntar el PDF de la ficha
        filename = f"Ficha_Admision_{ficha.numero_ficha}.pdf"
        email.attach(filename, pdf_content, 'application/pdf')
        
        # Enviar el email
        email.send()
        
        # Actualizar el registro de la ficha
        ficha.email_enviado = True
        ficha.fecha_envio_email = timezone.now()
        # Campo enviado_por no existe en el modelo; solo guardar cambios válidos
        ficha.save()
        
        return True, f"Ficha enviada exitosamente a {solicitud.email}"
        
    except Exception as e:
        return False, f"Error al enviar el email: {str(e)}"


def enviar_notificacion_estado_solicitud(solicitud, estado_anterior, usuario_que_cambio=None):
    """
    Envía una notificación por email cuando cambia el estado de una solicitud
    
    Args:
        solicitud: Instancia de SolicitudAdmision
        estado_anterior: Estado anterior de la solicitud
        usuario_que_cambio: Usuario que realizó el cambio (opcional)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Solo enviar notificaciones para ciertos estados
        estados_notificables = ['aceptada', 'rechazada']
        if solicitud.estado not in estados_notificables:
            return True, "Estado no requiere notificación"
        
        # Preparar el contexto para el template del email
        context = {
            'solicitud': solicitud,
            'estado_anterior': estado_anterior,
            'estado_actual': solicitud.get_estado_display(),
            'periodo': solicitud.periodo,
            'fecha_cambio': timezone.now(),
            'institucion': getattr(settings, 'INSTITUCION_NOMBRE', 'Institución Educativa'),
            'contacto_email': getattr(settings, 'CONTACTO_ADMISIONES_EMAIL', 'admisiones@institucion.edu'),
            'contacto_telefono': getattr(settings, 'CONTACTO_ADMISIONES_TELEFONO', 'N/A'),
        }
        
        # Renderizar el template del email
        subject = f"Actualización de Solicitud - {solicitud.folio} - {solicitud.get_estado_display()}"
        html_message = render_to_string('admision/emails/cambio_estado.html', context)
        text_message = render_to_string('admision/emails/cambio_estado.txt', context)
        
        # Crear el email
        email = EmailMessage(
            subject=subject,
            body=text_message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@institucion.edu'),
            to=[solicitud.email],
            reply_to=[getattr(settings, 'CONTACTO_ADMISIONES_EMAIL', 'admisiones@institucion.edu')]
        )
        
        # Agregar versión HTML
        email.attach_alternative(html_message, "text/html")
        
        # Si está aceptada y tiene ficha, adjuntarla
        if solicitud.estado == 'aceptada' and hasattr(solicitud, 'ficha'):
            try:
                pdf_content = generar_ficha_admision_pdf(solicitud)
                filename = f"Ficha_Admision_{solicitud.ficha.numero_ficha}.pdf"
                email.attach(filename, pdf_content, 'application/pdf')
            except Exception:
                pass  # Si no se puede generar el PDF, enviar sin adjunto
        
        # Enviar el email
        email.send()
        
        return True, f"Notificación enviada a {solicitud.email}"
        
    except Exception as e:
        return False, f"Error al enviar la notificación: {str(e)}"


def enviar_confirmacion_registro(solicitud):
    """
    Envía un email de confirmación cuando se registra una nueva solicitud
    
    Args:
        solicitud: Instancia de SolicitudAdmision recién creada
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Preparar el contexto para el template del email
        context = {
            'solicitud': solicitud,
            'periodo': solicitud.periodo,
            'fecha_registro': solicitud.fecha_registro,
            'institucion': getattr(settings, 'INSTITUCION_NOMBRE', 'Institución Educativa'),
            'contacto_email': getattr(settings, 'CONTACTO_ADMISIONES_EMAIL', 'admisiones@institucion.edu'),
            'contacto_telefono': getattr(settings, 'CONTACTO_ADMISIONES_TELEFONO', 'N/A'),
            'url_consulta': f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/admision/consultar/",
        }
        
        # Renderizar el template del email
        subject = f"Confirmación de Registro - {solicitud.folio} - {solicitud.periodo.nombre}"
        html_message = render_to_string('admision/emails/confirmacion_registro.html', context)
        text_message = render_to_string('admision/emails/confirmacion_registro.txt', context)
        
        # Crear el email
        email = EmailMessage(
            subject=subject,
            body=text_message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@institucion.edu'),
            to=[solicitud.email],
            reply_to=[getattr(settings, 'CONTACTO_ADMISIONES_EMAIL', 'admisiones@institucion.edu')]
        )
        
        # Agregar versión HTML
        email.attach_alternative(html_message, "text/html")
        
        # Enviar el email
        email.send()
        
        return True, f"Confirmación enviada a {solicitud.email}"
        
    except Exception as e:
        return False, f"Error al enviar la confirmación: {str(e)}"


def test_configuracion_email():
    """
    Función para probar la configuración de email
    
    Returns:
        dict: Resultado de la prueba con detalles de configuración
    """
    try:
        from django.core.mail import get_connection
        
        # Verificar configuración básica
        config = {
            'EMAIL_BACKEND': getattr(settings, 'EMAIL_BACKEND', 'No configurado'),
            'EMAIL_HOST': getattr(settings, 'EMAIL_HOST', 'No configurado'),
            'EMAIL_PORT': getattr(settings, 'EMAIL_PORT', 'No configurado'),
            'EMAIL_USE_TLS': getattr(settings, 'EMAIL_USE_TLS', False),
            'EMAIL_USE_SSL': getattr(settings, 'EMAIL_USE_SSL', False),
            'DEFAULT_FROM_EMAIL': getattr(settings, 'DEFAULT_FROM_EMAIL', 'No configurado'),
        }
        
        # Intentar crear conexión
        connection = get_connection()
        
        return {
            'success': True,
            'message': 'Configuración de email válida',
            'config': config
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Error en configuración de email: {str(e)}',
            'config': {}
        }


def enviar_confirmacion_registro(solicitud):
    """
    Envía correo de confirmación de registro al aspirante
    """
    try:
        # Contexto para el template del email
        context = {
            'solicitud': solicitud,
            'nombre_completo': solicitud.get_nombre_completo(),
            'periodo': solicitud.periodo,
            'folio': solicitud.folio,
            'fecha_registro': solicitud.fecha_registro,
            'site_name': getattr(settings, 'SITE_NAME', 'Sistema de Admisiones'),
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        }
        
        # Renderizar templates
        html_content = render_to_string('admision/emails/confirmacion_registro.html', context)
        text_content = render_to_string('admision/emails/confirmacion_registro.txt', context)
        
        # Configurar email
        subject = f'Confirmación de Registro - Folio {solicitud.folio}'
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tecnm.mx')
        to_email = [solicitud.email]
        
        # Crear email con versión HTML y texto
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=to_email
        )
        email.attach_alternative(html_content, "text/html")
        
        # Enviar email
        email.send()
        
        logger.info(f"Correo de confirmación enviado exitosamente a {solicitud.email} para folio {solicitud.folio}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando correo de confirmación para folio {solicitud.folio}: {str(e)}")
        raise e


def enviar_notificacion_cambio_estado(solicitud, estado_anterior):
    """
    Envía notificación cuando cambia el estado de una solicitud
    """
    try:
        # Solo enviar para ciertos cambios de estado
        estados_notificar = ['aceptada', 'rechazada', 'en_revision', 'documentos_pendientes']
        
        if solicitud.estado not in estados_notificar:
            return False
        
        # Contexto para el template del email
        context = {
            'solicitud': solicitud,
            'nombre_completo': solicitud.get_nombre_completo(),
            'periodo': solicitud.periodo,
            'folio': solicitud.folio,
            'estado_anterior': estado_anterior,
            'estado_actual': solicitud.estado,
            'fecha_cambio': solicitud.fecha_modificacion,
            'site_name': getattr(settings, 'SITE_NAME', 'Sistema de Admisiones'),
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        }
        
        # Renderizar templates
        html_content = render_to_string('admision/emails/cambio_estado.html', context)
        text_content = render_to_string('admision/emails/cambio_estado.txt', context)
        
        # Configurar email
        estados_nombres = {
            'enviada': 'Enviada',
            'en_revision': 'En Revisión',
            'aceptada': 'Aceptada',
            'rechazada': 'Rechazada',
            'documentos_pendientes': 'Documentos Pendientes',
            'ficha_generada': 'Ficha Generada'
        }
        
        estado_nombre = estados_nombres.get(solicitud.estado, solicitud.estado.title())
        subject = f'Actualización de Solicitud - {estado_nombre} - Folio {solicitud.folio}'
        
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tecnm.mx')
        to_email = [solicitud.email]
        
        # Crear email con versión HTML y texto
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=to_email
        )
        email.attach_alternative(html_content, "text/html")
        
        # Enviar email
        email.send()
        
        logger.info(f"Notificación de cambio de estado enviada a {solicitud.email} para folio {solicitud.folio}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando notificación de cambio de estado para folio {solicitud.folio}: {str(e)}")
        raise e


def enviar_notificacion_admin_nueva_solicitud(solicitud):
    """
    Envía notificación a administradores sobre nueva solicitud
    """
    try:
        # Obtener emails de administradores
        admin_emails = getattr(settings, 'ADMISION_ADMIN_EMAILS', [])
        
        if not admin_emails:
            logger.warning("No hay emails de administradores configurados para notificaciones")
            return False
        
        # Contexto para el template del email
        context = {
            'solicitud': solicitud,
            'nombre_completo': solicitud.get_nombre_completo(),
            'periodo': solicitud.periodo,
            'folio': solicitud.folio,
            'fecha_registro': solicitud.fecha_registro,
            'admin_url': f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/admision/admin/solicitudes/{solicitud.id}/",
        }
        
        # Renderizar templates
        html_content = render_to_string('admision/emails/admin_nueva_solicitud.html', context)
        text_content = render_to_string('admision/emails/admin_nueva_solicitud.txt', context)
        
        # Configurar email
        subject = f'Nueva Solicitud de Admisión - Folio {solicitud.folio}'
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tecnm.mx')
        
        # Crear email con versión HTML y texto
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=admin_emails
        )
        email.attach_alternative(html_content, "text/html")
        
        # Enviar email
        email.send()
        
        logger.info(f"Notificación de nueva solicitud enviada a administradores para folio {solicitud.folio}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando notificación a administradores para folio {solicitud.folio}: {str(e)}")
        return False