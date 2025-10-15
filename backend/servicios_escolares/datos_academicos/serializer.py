from rest_framework import serializers
from .models import Carrera, Materia, Alumno, Docente, PeriodoEscolar, Grupo, PlanEstudio, Tramite

class PeriodoEscolarSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodoEscolar
        fields = '__all__'

class CarreraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrera
        fields = '__all__'

class MateriaSerializer(serializers.ModelSerializer):
    carrera = CarreraSerializer(read_only=True)

    class Meta:
        model = Materia
        fields = '__all__'


class PlanEstudioSerializer(serializers.ModelSerializer):
    carrera = CarreraSerializer(read_only=True)

    class Meta:
        model = PlanEstudio
        fields = '__all__'

class GrupoSerializer(serializers.ModelSerializer):
    ciclo_escolar = PeriodoEscolarSerializer(read_only=True)
    carrera = CarreraSerializer(read_only=True)

    class Meta:
        model = Grupo
        fields = '__all__'

class AlumnoSerializer(serializers.ModelSerializer):
    grupo = GrupoSerializer(read_only=True)

    class Meta:
        model = Alumno
        fields = '__all__'

class DocenteSerializer(serializers.ModelSerializer):
    grupo = GrupoSerializer(read_only=True)

    class Meta:
        model = Docente
        fields = '__all__'

class TramiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tramite
        fields = '__all__'
