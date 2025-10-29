from django.db import migrations


def deduplicate_reinscripcion(apps, schema_editor):
    Reinscripcion = apps.get_model('datos_academicos', 'Reinscripcion')
    from django.db.models import Count

    duplicates = (
        Reinscripcion.objects.values('alumno_id', 'periodo_escolar_id')
        .annotate(c=Count('id')).filter(c__gt=1)
    )
    for dup in duplicates:
        qs = Reinscripcion.objects.filter(
            alumno_id=dup['alumno_id'], periodo_escolar_id=dup['periodo_escolar_id']
        ).order_by('-fecha_solicitud', '-id')
        keep = qs.first()
        to_delete = qs.exclude(id=keep.id)
        to_delete.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('datos_academicos', '0044_rename_fecha_aprobacion_reinscripcion_fecha_asignacion_materias_and_more'),
    ]

    operations = [
        migrations.RunPython(deduplicate_reinscripcion, migrations.RunPython.noop),
    ]