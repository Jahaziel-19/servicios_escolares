from django.db.models import ForeignKey
from difflib import get_close_matches

# Campos comunes a buscar en modelos relacionados
FK_LOOKUP_FIELDS = ['clave', 'nombre', 'codigo']

def obtener_instancia_relacionada(modelo_relacionado, valor_excel):
    valor = str(valor_excel).strip()

    # Filtrar solo campos que realmente existen en el modelo
    campos_modelo = [f.name for f in modelo_relacionado._meta.get_fields()]
    campos_a_buscar = [campo for campo in FK_LOOKUP_FIELDS if campo in campos_modelo]

    # Buscar coincidencia exacta solo en campos válidos
    for campo in campos_a_buscar:
        try:
            instancia = modelo_relacionado.objects.get(**{f"{campo}__iexact": valor})
            return instancia
        except modelo_relacionado.DoesNotExist:
            print(f"No existe {modelo_relacionado.__name__} con {campo} = '{valor}'")
            continue


    # Búsqueda por similitud (opcional)
    posibles = []
    for campo in campos_a_buscar:
        posibles += list(modelo_relacionado.objects.values_list(campo, flat=True))

    coincidencias = get_close_matches(valor, [str(x) for x in posibles], n=1, cutoff=0.85)
    if coincidencias:
        for campo in campos_a_buscar:
            try:
                return modelo_relacionado.objects.get(**{f"{campo}__iexact": coincidencias[0]})
            except modelo_relacionado.DoesNotExist:
                continue

    return None
