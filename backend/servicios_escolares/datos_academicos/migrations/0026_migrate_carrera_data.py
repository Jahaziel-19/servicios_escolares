# Generated manually to migrate existing carrera data to many-to-many relationship

from django.db import migrations


def migrate_carrera_to_carreras(apps, schema_editor):
    """
    Migra los datos existentes de carrera (ForeignKey) a carreras (ManyToMany)
    """
    # No podemos hacer esta migración automáticamente porque el campo carrera ya fue eliminado
    # Los datos se perderán y tendrán que ser reasignados manualmente
    pass


def reverse_migrate_carreras_to_carrera(apps, schema_editor):
    """
    Reversa la migración (no implementada)
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('datos_academicos', '0025_remove_materia_carrera_materia_carreras_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_carrera_to_carreras, reverse_migrate_carreras_to_carrera),
    ]