import os
from django.core.mail import EmailMessage, EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.utils.html import strip_tags
from .utils import generar_ficha_admision_pdf
import logging

logger = logging.getLogger(__name__)


# Helper centralizado para enviar emails con fallback en desarrollo
def send_email_safe(email_obj):
    try:
        email_obj.send()
        return True
    except Exception as e:
        logger.error(f"Fallo envío SMTP: {str(e)}")
        # Si estamos en DEBUG, intentar backend de consola
        if getattr(settings, 'DEBUG', False):
            try:
                conn = get_connection('django.core.mail.backends.console.EmailBackend')
                email_obj.connection = conn
                email_obj.send(fail_silently=True)
                logger.info("Correo enviado por backend de consola (fallback)")
                return True
            except Exception as e2:
                logger.error(f"También falló el backend de consola: {str(e2)}")
        return False


def enviar_ficha_por_email(solicitud, usuario_que_envia=None, adjuntos=None):
    """
    Envía la ficha de admisión por correo electrónico al aspirante
    
    Args:
        solicitud: Instancia de SolicitudAdmision
        usuario_que_envia: Usuario que solicita el envío (opcional)
        adjuntos: Lista de archivos adicionales (UploadedFile) a adjuntar (opcional)
    
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
            'institucion': getattr(settings, 'INSTITUCION_NOMBRE', 'INSTITUTO SUPERIOR TECNOLÓGICO DE TLAXCO'),
            'contacto_email': getattr(settings, 'CONTACTO_EMAIL', 'contacto@institucion.edu'),
            'contacto_telefono': getattr(settings, 'CONTACTO_TELEFONO', 'N/A'),
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
        
        # Adjuntar archivos adicionales si se proporcionan
        if adjuntos:
            for archivo in adjuntos:
                try:
                    email.attach(archivo.name, archivo.read(), archivo.content_type or 'application/octet-stream')
                except Exception:
                    # Si hay problema con un adjunto, continuar con los demás
                    continue
        
        # Enviar el email
        if not send_email_safe(email):
            return False, "No se pudo enviar la ficha por email"
        
        # Actualizar el registro de la ficha
        ficha.email_enviado = True
        ficha.fecha_envio_email = timezone.now()
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
        estados_notificables = ['aceptada', 'rechazada', 'seleccionado', 'no_seleccionado']
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
        html_content = render_to_string('admision/emails/cambio_estado.html', context)
        text_content = render_to_string('admision/emails/cambio_estado.txt', context)
        
        # Configurar email
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tecnm.mx')
        to_email = [solicitud.email]
        
        email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        email.attach_alternative(html_content, "text/html")
        if not send_email_safe(email):
            return False, "No se pudo enviar la notificación por email"
        
        logger.info(f"Notificación enviada a {solicitud.email} por cambio de estado a {solicitud.estado}")
        return True, "Notificación enviada"
    except Exception as e:
        logger.error(f"Error enviando notificación de estado para folio {solicitud.folio}: {str(e)}")
        return False, str(e)


def enviar_notificacion_cambio_estado(solicitud, estado_anterior):
    """
    Envía notificación cuando cambia el estado de una solicitud
    """
    try:
        # Solo enviar para ciertos cambios de estado
        estados_notificar = ['aceptada', 'rechazada', 'en_revision', 'documentos_pendientes', 'seleccionado', 'no_seleccionado']
        
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
            'fecha_cambio': timezone.now(),
            'site_name': getattr(settings, 'SITE_NAME', 'Sistema de Admisiones'),
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
            'institucion': getattr(settings, 'INSTITUCION_NOMBRE', 'Institución Educativa'),
            'contacto_email': getattr(settings, 'CONTACTO_EMAIL', 'contacto@institucion.edu'),
            'contacto_telefono': getattr(settings, 'CONTACTO_TELEFONO', 'N/A'),
        }
        
        # Renderizar templates por separado con fallback y logging
        try:
            html_content = render_to_string('admision/emails/cambio_estado.html', context)
        except Exception as e:
            logger.error(f"Error renderizando HTML cambio_estado: {str(e)}")
            html_content = (
                f"""
                <html><body style=\"font-family:Arial,sans-serif\">
                <div style=\"background:#f8f9fa;padding:16px;border:1px solid #dee2e6;border-radius:8px\">
                  <h2 style=\"margin:0 0 8px 0\">Actualización de Solicitud</h2>
                  <p style=\"margin:0\"><strong>Folio:</strong> {solicitud.folio}</p>
                  <p style=\"margin:0\"><strong>Nuevo estado:</strong> {solicitud.estado}</p>
                </div>
                </body></html>
                """.strip()
            )
        
        try:
            text_content = render_to_string('admision/emails/cambio_estado.txt', context)
        except Exception as e:
            logger.error(f"Error renderizando TXT cambio_estado: {str(e)}")
            text_content = (
                f"Su solicitud cambió de estado.\n"
                f"Folio: {solicitud.folio}\n"
                f"Nuevo estado: {solicitud.estado}\n"
            )
        
        # Configurar email
        estados_nombres = {
            'enviada': 'Enviada',
            'en_revision': 'En Revisión',
            'aceptada': 'Aceptada',
            'rechazada': 'Rechazada',
            'documentos_pendientes': 'Documentos Pendientes',
            'ficha_generada': 'Ficha Generada',
            'seleccionado': 'Seleccionado',
            'no_seleccionado': 'No seleccionado',
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
        if not send_email_safe(email):
            return False
        
        logger.info(f"Notificación de cambio de estado enviada a {solicitud.email} para folio {solicitud.folio}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando notificación de cambio de estado para folio {solicitud.folio}: {str(e)}")
        return False


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
        if not send_email_safe(email):
            return False
        
        logger.info(f"Notificación de nueva solicitud enviada a administradores para folio {solicitud.folio}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando notificación a administradores para folio {solicitud.folio}: {str(e)}")
        return False


def enviar_confirmacion_registro(solicitud):
    """
    Envía confirmación de registro al correo del solicitante en formato HTML y texto
    """
    try:
        from django.urls import reverse
        institucion = getattr(settings, 'INSTITUCION_NOMBRE', 'Institución Educativa')
        contacto_email = getattr(settings, 'CONTACTO_ADMISIONES_EMAIL', 'admisiones@institucion.edu')
        contacto_telefono = getattr(settings, 'CONTACTO_ADMISIONES_TELEFONO', 'N/A')
        fecha_envio = timezone.now()
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')

        # Construir URL de consulta
        try:
            url_consulta = f"{site_url}{reverse('admision:admision_publico:consultar_solicitud')}"
        except Exception:
            url_consulta = site_url

        # Contexto para las plantillas
        context = {
            'solicitud': solicitud,
            'institucion': institucion,
            'contacto_email': contacto_email,
            'contacto_telefono': contacto_telefono,
            'fecha_envio': fecha_envio,
            'periodo': solicitud.periodo,
            'fecha_registro': solicitud.fecha_registro,
            'url_consulta': url_consulta,
        }

        # Renderizar templates HTML y texto
        html_content = render_to_string('admision/emails/confirmacion_registro.html', context)
        text_content = render_to_string('admision/emails/confirmacion_registro.txt', context)

        # Asunto y remitente
        subject = f"Confirmación de Registro - {solicitud.folio} - {solicitud.periodo.nombre}"
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tecnm.mx')

        # Crear correo multipart (texto + HTML)
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[solicitud.email]
        )
        email.attach_alternative(html_content, "text/html")

        # Enviar con helper centralizado
        if not send_email_safe(email):
            return False

        logger.info(f"Confirmación de registro enviada a {solicitud.email} para folio {solicitud.folio}")
        return True
    except Exception as e:
        logger.error(f"Error enviando confirmación de registro para folio {solicitud.folio}: {str(e)}")
        return False