from datos_academicos.models import Alumno, Calificacion, Materia, MateriaCarrera, PeriodoEscolar
from docsbuilder.models import Plantilla, VariablePlantilla
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from docxtpl import DocxTemplate, RichText
from datetime import datetime, date
from io import BytesIO
from servicios_escolares.utils import obtener_periodo_activo


def armar_contexto_para_alumno(alumno, variables):
    contexto = {}

    for var in variables:
        #print(f"Procesando variable: {var.nombre} de tipo {var.tipo}")
        if var.tipo == 'simple' and var.campo:
            #print(f"Procesando variable simple: {var.nombre} con campo '{var.campo}'")
            valor = getattr(alumno, var.campo, '')
            if hasattr(valor, 'nombre'):  # por si es clave foránea
                valor = valor.nombre
            contexto[var.nombre] = valor

        elif var.tipo == 'especial':
            #print(f"Procesando variable especial: {var.nombre} con opción '{var.especial_opcion}'")
            if var.especial_opcion == 'fecha_emision':
                contexto[var.nombre] = datetime.now().strftime('%d/%m/%Y')
            elif var.especial_opcion == 'nombre_completo':
                contexto[var.nombre] = f"{alumno.nombre} {alumno.apellido_paterno or ''} {alumno.apellido_materno or ''}".strip()
            elif var.especial_opcion == 'periodo_completo':
                # Obtener periodo activo automáticamente
                periodo_activo = obtener_periodo_activo()
                if periodo_activo:
                    contexto[var.nombre] = f"{periodo_activo.ciclo} {periodo_activo.año}"
                else:
                    contexto[var.nombre] = "Periodo no definido"

        elif var.tipo == 'tabla':
            print(f"Procesando variable de tipo tabla: {var.nombre}")
            continue
            '''            
                        # Obtener materias a través de la relación MateriaCarrera
                        materias_carrera = MateriaCarrera.objects.filter(carrera=alumno.carrera).select_related('materia').order_by('materia__semestre', 'materia__clave')
                        materias = [mc.materia for mc in materias_carrera]
                        califs = Calificacion.objects.filter(alumno=alumno).order_by('-fecha_registro')
                        calif_dict = {c.materia_id: c for c in califs}

                        texto_tabla = ""
                        semestre_actual = None

                        # Anchuras para las columnas
                        w_clave = 10
                        w_nombre = 38  # ahora más corto y controlado
                        w_creditos = 10
                        w_calificacion = 15
                        w_acreditacion = 15

                        for materia in materias:
                            if materia.semestre != semestre_actual:
                                semestre_actual = materia.semestre
                                texto_tabla += f"\n\n{semestre_actual}° SEMESTRE\n"
                                texto_tabla += (
                                    f"{'CLAVE'.ljust(w_clave)}"
                                    f"{'NOMBRE'.ljust(w_nombre)}"
                                    f"{'CRÉDITOS'.center(w_creditos)}"
                                    f"{'CALIFICACIÓN'.center(w_calificacion)}"
                                    f"{'ACREDITACIÓN'.center(w_acreditacion)}\n"
                                )
                                texto_tabla += "-" * (w_clave + w_nombre + w_creditos + w_calificacion + w_acreditacion) + "\n"

                            calif = calif_dict.get(materia.id)

                            nombre_limpio = materia.nombre.strip()
                            if len(nombre_limpio) > w_nombre:
                                nombre_limpio = nombre_limpio[:w_nombre - 1] + "…"

                            texto_tabla += (
                                f"{materia.clave.ljust(w_clave)}"
                                f"{nombre_limpio.ljust(w_nombre)}"
                                f"{str(materia.creditos).center(w_creditos)}"
                                f"{str(calif.calificacion).center(w_calificacion) if calif else '—'.center(w_calificacion)}"
                                f"{str(calif.acreditacion).center(w_acreditacion) if calif else '—'.center(w_acreditacion)}\n"
                            )

                        contexto[var.nombre] = texto_tabla.strip()
            '''


    return contexto


def armar_contexto_para_boleta(alumno, periodo_escolar, variables):
    """
    Arma el contexto específico para boletas de calificaciones
    usando el patrón de variables de docsbuilder
    """
    contexto = {}

    # Obtener calificaciones del alumno para el periodo específico
    from datos_academicos.models import Calificacion
    calificaciones = Calificacion.objects.filter(
        alumno=alumno,
        periodo_escolar=periodo_escolar,
        materia__materiacarrera__carrera=alumno.carrera
    ).select_related('materia').order_by('materia__clave')

    # Calcular promedio del periodo
    if calificaciones.exists():
        total_creditos = sum(calif.creditos for calif in calificaciones)
        suma_ponderada = sum(calif.calificacion * calif.creditos for calif in calificaciones)
        promedio_periodo = suma_ponderada / total_creditos if total_creditos > 0 else 0
    else:
        promedio_periodo = 0

    for var in variables:
        if var.tipo == 'simple' and var.campo:
            # Variables simples del alumno
            if hasattr(alumno, var.campo):
                valor = getattr(alumno, var.campo, '')
                if hasattr(valor, 'nombre'):  # por si es clave foránea
                    valor = valor.nombre
                contexto[var.nombre] = valor
            # Variables específicas del periodo
            elif var.campo == 'periodo_escolar':
                contexto[var.nombre] = str(periodo_escolar)
            elif var.campo == 'promedio_periodo':
                contexto[var.nombre] = f"{promedio_periodo:.2f}"

        elif var.tipo == 'especial':
            if var.especial_opcion == 'fecha_emision':
                contexto[var.nombre] = datetime.now().strftime('%d/%m/%Y')
            elif var.especial_opcion == 'nombre_completo':
                contexto[var.nombre] = f"{alumno.nombre} {alumno.apellido_paterno or ''} {alumno.apellido_materno or ''}".strip()
            elif var.especial_opcion == 'periodo_completo':
                contexto[var.nombre] = f"{periodo_escolar.ciclo} {periodo_escolar.año}"

        elif var.tipo == 'tabla' and var.nombre == 'calificaciones':
            # Generar tabla de calificaciones usando <<>>
            tabla_calificaciones = []
            for calif in calificaciones:
                # Determinar nivel de desempeño
                if calif.calificacion is None or calif.calificacion == 0:
                    nivel_desempeno = "DI"
                elif calif.calificacion < 60:
                    nivel_desempeno = "DI"
                elif calif.calificacion < 70:
                    nivel_desempeno = "S"
                elif calif.calificacion < 80:
                    nivel_desempeno = "B"
                elif calif.calificacion < 90:
                    nivel_desempeno = "N"
                else:
                    nivel_desempeno = "E"
                
                fila = {
                    'clave': calif.materia.clave,
                    'nombre': calif.materia.nombre,
                    'nivel_desempeno': nivel_desempeno,
                    'creditos': str(calif.creditos),
                    'calificacion': str(calif.calificacion),
                    'acreditacion': calif.acreditacion[0] if calif.acreditacion else ''
                }
                tabla_calificaciones.append(fila)
            
            contexto[var.nombre] = tabla_calificaciones

    return contexto

    '''
        """
        Contexto simplificado para kardex usando variables individuales
        (por si prefieres usar variables separadas en lugar de tabla)
        """
        # Obtener materias a través de la relación MateriaCarrera
        materias_carrera = MateriaCarrera.objects.filter(carrera=alumno.carrera).select_related('materia').order_by('materia__semestre', 'materia__clave')
        materias = [mc.materia for mc in materias_carrera]
        califs = Calificacion.objects.filter(alumno=alumno)
        calif_dict = {c.materia_id: c for c in califs}

        contexto = {
            'nombre': alumno.nombre,
            'apellido_paterno': alumno.apellido_paterno or '',
            'apellido_materno': alumno.apellido_materno or '',
            'matricula': alumno.matricula,
            'carrera': alumno.carrera.nombre,
            'semestre': str(alumno.semestre),
            'fecha_emision': datetime.now().strftime('%d/%m/%Y'),
        }
        
        # Agregar variables individuales por fila
        fila = 1
        for materia in materias:
            calif = calif_dict.get(materia.id)
            contexto[f'SEM_{fila}'] = str(materia.semestre)
            contexto[f'CLAVE_{fila}'] = materia.clave
            contexto[f'NOMBRE_{fila}'] = materia.nombre
            contexto[f'CRED_{fila}'] = str(materia.creditos)
            contexto[f'CALIF_{fila}'] = str(calif.calificacion) if calif else ''
            contexto[f'TIPO_{fila}'] = calif.acreditacion if calif else ''
            fila += 1
        
        # Completar filas vacías si la plantilla tiene más filas
        for f in range(fila, 61):  # Completar hasta 60 filas
            contexto[f'SEM_{f}'] = ''
            contexto[f'CLAVE_{f}'] = ''
            contexto[f'NOMBRE_{f}'] = ''
            contexto[f'CRED_{f}'] = ''
            contexto[f'CALIF_{f}'] = ''
            contexto[f'TIPO_{f}'] = ''
        
        return contexto
'''