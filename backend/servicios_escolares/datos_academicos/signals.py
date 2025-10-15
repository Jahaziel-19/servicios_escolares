from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Calificacion


@receiver(post_save, sender=Calificacion)
def actualizar_datos_alumno_post_save(sender, instance, created, **kwargs):
    """
    Signal que se ejecuta después de guardar una calificación.
    Actualiza automáticamente el promedio y créditos aprobados del alumno.
    """
    if instance.alumno:
        instance.alumno.actualizar_datos_academicos()


@receiver(post_delete, sender=Calificacion)
def actualizar_datos_alumno_post_delete(sender, instance, **kwargs):
    """
    Signal que se ejecuta después de eliminar una calificación.
    Actualiza automáticamente el promedio y créditos aprobados del alumno.
    """
    if instance.alumno:
        instance.alumno.actualizar_datos_academicos()