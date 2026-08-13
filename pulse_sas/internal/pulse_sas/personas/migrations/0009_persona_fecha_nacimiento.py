import datetime

from django.db import migrations, models


def backfill_fecha_nacimiento(apps, schema_editor):
    """Convierte la `edad` (entero) de cada Persona ya existente en una
    fecha de nacimiento aproximada (hoy menos esos años). No es la fecha
    real -- no se puede derivar de una edad sola -- pero deja el dato
    obligatorio poblado en vez de vacío. Corregir a mano cuando se sepa la
    fecha real de cada persona."""
    Persona = apps.get_model('personas', 'Persona')
    hoy = datetime.date.today()
    for persona in Persona.objects.all():
        anio_nacimiento = hoy.year - persona.edad
        try:
            persona.fecha_nacimiento = hoy.replace(year=anio_nacimiento)
        except ValueError:
            # 29 de febrero en un año no bisiesto
            persona.fecha_nacimiento = hoy.replace(year=anio_nacimiento, day=28)
        persona.save(update_fields=['fecha_nacimiento'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('personas', '0008_convenio_persona_fecha_creacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='persona',
            name='fecha_nacimiento',
            field=models.DateField(null=True),
        ),
        migrations.RunPython(backfill_fecha_nacimiento, noop),
        migrations.AlterField(
            model_name='persona',
            name='fecha_nacimiento',
            field=models.DateField(),
        ),
        migrations.RemoveField(
            model_name='persona',
            name='edad',
        ),
    ]
