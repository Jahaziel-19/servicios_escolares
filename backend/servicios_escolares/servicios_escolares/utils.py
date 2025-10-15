from datetime import date, timedelta
from django.utils.timezone import now
from datos_academicos.models import PeriodoEscolar

def obtener_periodo_activo():
    """
    Devuelve el periodo activo si su rango contiene hoy.
    - Si hay un registro con activo=True que contiene hoy, lo devuelve.
    - Si hay activo=True pero no contiene hoy lo considera inexistente (None).
    - Si no hay activo=True busca cualquier periodo cuyo rango contenga hoy y lo marca activo.
    """
    hoy = date.today()
    periodo_activo = PeriodoEscolar.objects.filter(activo=True).first()
    if periodo_activo:
        if periodo_activo.fecha_inicio and periodo_activo.fecha_fin and periodo_activo.fecha_inicio <= hoy <= periodo_activo.fecha_fin:
            return periodo_activo
        # si el marcado no contiene hoy lo ignoramos (será tratado como no existente)
        return None

    # buscar por rango (no marcado pero válido)
    por_rango = PeriodoEscolar.objects.filter(fecha_inicio__lte=hoy, fecha_fin__gte=hoy).first()
    if por_rango:
        por_rango.activo = True
        por_rango.save()
        return por_rango

    return None

def necesita_crear_periodo():
    return obtener_periodo_activo() is None