import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personas', '0009_persona_fecha_nacimiento'),
    ]

    operations = [
        migrations.RenameField(
            model_name='persona',
            old_name='telefono_acompanante',
            new_name='telefono_familiar1',
        ),
        migrations.AlterField(
            model_name='persona',
            name='telefono_familiar1',
            field=models.CharField(blank=True, max_length=20, verbose_name='teléfono familiar 1'),
        ),
        migrations.AddField(
            model_name='persona',
            name='telefono_familiar2',
            field=models.CharField(blank=True, max_length=20, verbose_name='teléfono familiar 2'),
        ),
        migrations.AddField(
            model_name='persona',
            name='telefono_personal_pais',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='telefonos_personales', to='personas.pais',
                verbose_name='país del teléfono personal',
            ),
        ),
        migrations.AddField(
            model_name='persona',
            name='telefono_familiar1_pais',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='telefonos_familiar1', to='personas.pais',
                verbose_name='país del teléfono familiar 1',
            ),
        ),
        migrations.AddField(
            model_name='persona',
            name='telefono_familiar2_pais',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='telefonos_familiar2', to='personas.pais',
                verbose_name='país del teléfono familiar 2',
            ),
        ),
        migrations.AddField(
            model_name='persona',
            name='correo_recuperacion',
            field=models.EmailField(blank=True, max_length=254, verbose_name='correo de recuperación'),
        ),
        migrations.AddField(
            model_name='persona',
            name='pais_residencia',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='personas_residentes', to='personas.pais',
                verbose_name='país de residencia',
            ),
        ),
        migrations.AlterField(
            model_name='persona',
            name='correo',
            field=models.EmailField(max_length=254, verbose_name='correo electrónico personal'),
        ),
    ]
