from django.db import models

# Create your models here.
class Carrera(models.Model):    
    nombre = models.CharField(max_length=100, unique=True)
    clave = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.nombre

class Materia(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    clave = models.CharField(max_length=10, unique=True)
    creditos = models.IntegerField(default=0)
    #carrera = models.ForeignKey(Carreras, on_delete=models.CASCADE, related_name='materias')
    
    def __str__(self):
        return self.nombre