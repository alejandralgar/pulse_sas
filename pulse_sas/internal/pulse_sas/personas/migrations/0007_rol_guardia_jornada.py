import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personas', '0006_persona_eps_ips_ciudad_residencia_contactoemergencia'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rol',
            name='categoria',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('admin', 'Admin'),
                    ('cliente_paciente', 'Cliente / paciente'),
                    ('empresa', 'Empresa'),
                    ('administrativo', 'Administrativo'),
                    ('medico', 'Médico'),
                    ('enfermera', 'Enfermera'),
                    ('guardia', 'Guardia de seguridad'),
                ],
            ),
        ),
        migrations.CreateModel(
            name='Jornada',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField()),
                ('hora_inicio', models.TimeField()),
                ('hora_fin', models.TimeField()),
                ('tipo_jornada', models.CharField(
                    max_length=10,
                    choices=[('manana', 'Mañana'), ('tarde', 'Tarde'), ('noche', 'Noche')],
                )),
                ('persona', models.ForeignKey(
                    'personas.Persona',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='jornadas',
                    verbose_name='persona',
                )),
            ],
            options={
                'verbose_name': 'jornada',
                'verbose_name_plural': 'jornadas',
                'ordering': ['-fecha', 'hora_inicio'],
            },
        ),
    ]
