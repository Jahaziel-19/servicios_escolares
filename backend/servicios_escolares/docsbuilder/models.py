from django.db import models

TIPO_DATO_CHOICES = [
    ('simple', 'Simple'),
    ('especial', 'Especial'),
    ('tabla', 'Tabla/Lista'),
]

class Plantilla(models.Model):
    nombre = models.CharField(max_length=200)
    archivo = models.FileField(upload_to='plantillas/')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class VariablePlantilla(models.Model):
    plantilla = models.ForeignKey(Plantilla, on_delete=models.CASCADE, related_name='variables')
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_DATO_CHOICES, default='simple')
    campo = models.CharField(max_length=100, blank=True, null=True)  # Solo campo del alumno para simples
    especial_opcion = models.CharField(max_length=50, blank=True, null=True)  # ej: fecha_emision

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"
