from django.db import models
from django.utils import timezone

class Formulario(models.Model):
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    fields = models.JSONField(default=list)  # Lista de campos, cada campo es dict con id, label, type, required, options
    activo = models.BooleanField(default=True, help_text="Indica si el formulario está activo y puede recibir respuestas")
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

    class Meta:
        ordering = ['-fecha_modificacion']

class RespuestaFormulario(models.Model):
    formulario = models.ForeignKey(Formulario, on_delete=models.CASCADE, related_name='respuestas')
    fecha_respuesta = models.DateTimeField(auto_now_add=True)
    datos = models.JSONField()  # Diccionario con respuestas: {campo_id: valor}

    def __str__(self):
        return f"Respuesta a {self.formulario.nombre} - {self.fecha_respuesta.strftime('%Y-%m-%d %H:%M:%S')}"
