from django.db import models
from django.apps import apps

class ModeloAutorizado(models.Model):
    nombre_app = models.CharField(max_length=100, default=None, blank=True)
    nombre_modelo = models.CharField(max_length=100, default=None, blank=True)
    descripcion = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.nombre_app}.{self.nombre_modelo}"

    def get_model_class(self):
        return apps.get_model(self.nombre_app, self.nombre_modelo)
