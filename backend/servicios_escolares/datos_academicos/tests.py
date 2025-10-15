from django.test import TestCase
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta
from .models import Alumno, Carrera, Materia, Calificacion, PeriodoEscolar, MateriaCarrera


class AlumnoDataUpdateTestCase(TestCase):
    def setUp(self):
        """Configuración inicial para las pruebas"""
        # Crear carrera
        self.carrera = Carrera.objects.create(
            clave='ISC',
            nombre='Ingeniería en Sistemas Computacionales',
            creditos_totales=300
        )
        
        # Crear materias
        self.materia1 = Materia.objects.create(
            clave='MAT001',
            nombre='Matemáticas I',
            creditos=8,
            cuenta_promedio=True
        )
        
        self.materia2 = Materia.objects.create(
            clave='PRG001',
            nombre='Programación I',
            creditos=6,
            cuenta_promedio=True
        )
        
        self.materia3 = Materia.objects.create(
            clave='ACT001',
            nombre='Actividad Deportiva',
            creditos=2,
            cuenta_promedio=False,  # No cuenta para promedio
            tipo='Actividad'
        )
        
        # Crear relaciones MateriaCarrera
        MateriaCarrera.objects.create(materia=self.materia1, carrera=self.carrera, semestre=1)
        MateriaCarrera.objects.create(materia=self.materia2, carrera=self.carrera, semestre=1)
        MateriaCarrera.objects.create(materia=self.materia3, carrera=self.carrera, semestre=1)
        
        # Crear periodo escolar con fechas válidas
        hoy = date.today()
        self.periodo = PeriodoEscolar.objects.create(
            ciclo='Enero-Junio',
            año=2024,
            fecha_inicio=hoy - timedelta(days=30),
            fecha_fin=hoy + timedelta(days=30),
            activo=True
        )
        
        # Crear alumno
        self.alumno = Alumno.objects.create(
            matricula='20240001',
            nombre='Juan',
            apellido_paterno='Pérez',
            carrera=self.carrera,
            semestre=1
        )
    
    def test_calculo_promedio_solo_materias_que_cuentan(self):
        """Prueba que el promedio solo incluya materias que cuentan para promedio"""
        # Crear calificaciones
        Calificacion.objects.create(
            alumno=self.alumno,
            materia=self.materia1,
            periodo_escolar=self.periodo,
            calificacion=85,
            creditos=8
        )
        
        Calificacion.objects.create(
            alumno=self.alumno,
            materia=self.materia2,
            periodo_escolar=self.periodo,
            calificacion=90,
            creditos=6
        )
        
        # Esta calificación NO debe contar para el promedio
        Calificacion.objects.create(
            alumno=self.alumno,
            materia=self.materia3,
            periodo_escolar=self.periodo,
            calificacion=100,
            creditos=2
        )
        
        # Calcular promedio manualmente
        promedio_esperado = (85 + 90) / 2  # Solo materias que cuentan para promedio
        promedio_calculado = self.alumno.calcular_promedio()
        
        self.assertEqual(float(promedio_calculado), promedio_esperado)
    
    def test_calculo_creditos_aprobados(self):
        """Prueba el cálculo de créditos aprobados"""
        # Crear calificaciones aprobadas
        Calificacion.objects.create(
            alumno=self.alumno,
            materia=self.materia1,
            periodo_escolar=self.periodo,
            calificacion=85,
            creditos=8
        )
        
        Calificacion.objects.create(
            alumno=self.alumno,
            materia=self.materia2,
            periodo_escolar=self.periodo,
            calificacion=75,
            creditos=6
        )
        
        # Calificación reprobada (no debe contar)
        Calificacion.objects.create(
            alumno=self.alumno,
            materia=self.materia3,
            periodo_escolar=self.periodo,
            calificacion=5.5,
            creditos=2
        )
        
        creditos_esperados = 8 + 6  # Solo materias aprobadas (>=6.0)
        creditos_calculados = self.alumno.calcular_creditos_aprobados()
        
        self.assertEqual(creditos_calculados, creditos_esperados)
    
    def test_actualizacion_automatica_con_signals(self):
        """Prueba que los signals actualicen automáticamente los datos del alumno"""
        # Verificar valores iniciales
        self.assertEqual(float(self.alumno.promedio), 0.0)
        self.assertEqual(self.alumno.creditos_aprobados, 0)
        
        # Crear una calificación (debe disparar el signal)
        calificacion = Calificacion.objects.create(
            alumno=self.alumno,
            materia=self.materia1,
            periodo_escolar=self.periodo,
            calificacion=85,
            creditos=8
        )
        
        # Recargar el alumno desde la base de datos
        self.alumno.refresh_from_db()
        
        # Verificar que se actualizaron los datos
        self.assertEqual(float(self.alumno.promedio), 85.0)
        self.assertEqual(self.alumno.creditos_aprobados, 8)
        self.assertEqual(self.alumno.creditos_totales, 300)  # Desde la carrera
        
        # Agregar otra calificación
        Calificacion.objects.create(
            alumno=self.alumno,
            materia=self.materia2,
            periodo_escolar=self.periodo,
            calificacion=90,
            creditos=6
        )
        
        # Recargar y verificar
        self.alumno.refresh_from_db()
        promedio_esperado = (85 + 90) / 2
        self.assertEqual(float(self.alumno.promedio), promedio_esperado)
        self.assertEqual(self.alumno.creditos_aprobados, 14)
    
    def test_actualizacion_al_modificar_calificacion(self):
        """Prueba que se actualicen los datos al modificar una calificación"""
        # Crear calificación inicial
        calificacion = Calificacion.objects.create(
            alumno=self.alumno,
            materia=self.materia1,
            periodo_escolar=self.periodo,
            calificacion=70,
            creditos=8
        )
        
        self.alumno.refresh_from_db()
        self.assertEqual(float(self.alumno.promedio), 70.0)
        self.assertEqual(self.alumno.creditos_aprobados, 8)
        
        # Modificar la calificación
        calificacion.calificacion = 85
        calificacion.save()
        
        # Verificar actualización
        self.alumno.refresh_from_db()
        self.assertEqual(float(self.alumno.promedio), 85.0)
        self.assertEqual(self.alumno.creditos_aprobados, 8)
    
    def test_actualizacion_al_eliminar_calificacion(self):
        """Prueba que se actualicen los datos al eliminar una calificación"""
        # Crear dos calificaciones
        cal1 = Calificacion.objects.create(
            alumno=self.alumno,
            materia=self.materia1,
            periodo_escolar=self.periodo,
            calificacion=80,
            creditos=8
        )
        
        cal2 = Calificacion.objects.create(
            alumno=self.alumno,
            materia=self.materia2,
            periodo_escolar=self.periodo,
            calificacion=90,
            creditos=6
        )
        
        self.alumno.refresh_from_db()
        promedio_inicial = (80 + 90) / 2
        self.assertEqual(float(self.alumno.promedio), promedio_inicial)
        self.assertEqual(self.alumno.creditos_aprobados, 14)
        
        # Eliminar una calificación
        cal1.delete()
        
        # Verificar actualización
        self.alumno.refresh_from_db()
        self.assertEqual(float(self.alumno.promedio), 90.0)
        self.assertEqual(self.alumno.creditos_aprobados, 6)
    
    def test_solo_materias_de_carrera_del_alumno(self):
        """Prueba que solo se consideren materias de la carrera del alumno"""
        # Crear otra carrera
        otra_carrera = Carrera.objects.create(
            clave='IND',
            nombre='Ingeniería Industrial',
            creditos_totales=280
        )
        
        # Crear materia de otra carrera
        materia_otra_carrera = Materia.objects.create(
            clave='IND001',
            nombre='Procesos Industriales',
            creditos=7,
            cuenta_promedio=True
        )
        
        MateriaCarrera.objects.create(
            materia=materia_otra_carrera, 
            carrera=otra_carrera, 
            semestre=1
        )
        
        # Crear calificación en materia de la carrera del alumno
        Calificacion.objects.create(
            alumno=self.alumno,
            materia=self.materia1,
            periodo_escolar=self.periodo,
            calificacion=85,
            creditos=8
        )
        
        # Crear calificación en materia de otra carrera (no debe contar)
        Calificacion.objects.create(
            alumno=self.alumno,
            materia=materia_otra_carrera,
            periodo_escolar=self.periodo,
            calificacion=95,
            creditos=7
        )
        
        # El promedio debe ser solo de la materia de su carrera
        self.alumno.refresh_from_db()
        self.assertEqual(float(self.alumno.promedio), 85.0)
        self.assertEqual(self.alumno.creditos_aprobados, 8)


class CarreraCreditosTotalesTestCase(TestCase):
    def setUp(self):
        """Configuración inicial para las pruebas de créditos totales de carrera"""
        # Crear carrera
        self.carrera = Carrera.objects.create(
            clave='ISC',
            nombre='Ingeniería en Sistemas Computacionales',
            creditos_totales=0  # Inicialmente en 0
        )
        
        # Crear materias con diferentes créditos
        self.materia1 = Materia.objects.create(
            clave='MAT001',
            nombre='Matemáticas I',
            creditos=8
        )
        
        self.materia2 = Materia.objects.create(
            clave='PRG001',
            nombre='Programación I',
            creditos=6
        )
        
        self.materia3 = Materia.objects.create(
            clave='FIS001',
            nombre='Física I',
            creditos=7
        )
        
        # Crear relaciones MateriaCarrera
        MateriaCarrera.objects.create(materia=self.materia1, carrera=self.carrera, semestre=1)
        MateriaCarrera.objects.create(materia=self.materia2, carrera=self.carrera, semestre=1)
        MateriaCarrera.objects.create(materia=self.materia3, carrera=self.carrera, semestre=2)

    def test_calcular_creditos_totales(self):
        """Prueba el cálculo de créditos totales de una carrera"""
        creditos_esperados = 8 + 6 + 7  # Suma de todas las materias
        creditos_calculados = self.carrera.calcular_creditos_totales()
        
        self.assertEqual(creditos_calculados, creditos_esperados)

    def test_carrera_sin_materias(self):
        """Prueba el cálculo de créditos para una carrera sin materias"""
        carrera_vacia = Carrera.objects.create(
            clave='EMPTY',
            nombre='Carrera Vacía',
            creditos_totales=0
        )
        
        creditos_calculados = carrera_vacia.calcular_creditos_totales()
        self.assertEqual(creditos_calculados, 0)

    def test_actualizar_creditos_totales_campo(self):
        """Prueba que se puede actualizar el campo creditos_totales"""
        # Calcular y actualizar
        creditos_calculados = self.carrera.calcular_creditos_totales()
        self.carrera.creditos_totales = creditos_calculados
        self.carrera.save()
        
        # Verificar que se guardó correctamente
        self.carrera.refresh_from_db()
        self.assertEqual(self.carrera.creditos_totales, 21)  # 8 + 6 + 7

    def test_agregar_materia_actualiza_creditos(self):
        """Prueba que agregar una nueva materia afecta el cálculo de créditos"""
        # Créditos iniciales
        creditos_iniciales = self.carrera.calcular_creditos_totales()
        
        # Agregar nueva materia
        nueva_materia = Materia.objects.create(
            clave='QUI001',
            nombre='Química I',
            creditos=5
        )
        MateriaCarrera.objects.create(materia=nueva_materia, carrera=self.carrera, semestre=2)
        
        # Verificar que los créditos aumentaron
        creditos_nuevos = self.carrera.calcular_creditos_totales()
        self.assertEqual(creditos_nuevos, creditos_iniciales + 5)
