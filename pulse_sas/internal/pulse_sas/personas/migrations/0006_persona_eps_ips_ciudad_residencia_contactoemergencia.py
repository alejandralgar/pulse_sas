import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personas', '0005_solo_colombia'),
    ]

    operations = [
        migrations.AddField(
            model_name='persona',
            name='eps_ips',
            field=models.CharField('EPS / IPS', max_length=150, blank=True),
        ),
        migrations.AddField(
            model_name='persona',
            name='ciudad_residencia',
            field=models.ForeignKey(
                'personas.Ciudad',
                on_delete=django.db.models.deletion.SET_NULL,
                null=True, blank=True,
                related_name='residentes',
                verbose_name='ciudad de residencia',
            ),
        ),
        migrations.CreateModel(
            name='ContactoEmergencia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_completo', models.CharField('nombre completo', max_length=200)),
                ('cedula', models.CharField('cédula / identificación', max_length=20, blank=True)),
                ('correo', models.EmailField('correo electrónico', blank=True)),
                ('telefono', models.CharField('teléfono', max_length=20)),
                ('parentesco', models.CharField(max_length=80)),
                ('ciudad_residencia', models.ForeignKey(
                    'personas.Ciudad',
                    on_delete=django.db.models.deletion.SET_NULL,
                    null=True, blank=True,
                    related_name='contactos_emergencia',
                    verbose_name='ciudad de residencia',
                )),
                ('paciente', models.ForeignKey(
                    'personas.Persona',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='contactos_emergencia',
                    verbose_name='paciente',
                )),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'contacto de emergencia',
                'verbose_name_plural': 'contactos de emergencia',
                'ordering': ['-creado_en'],
            },
        ),
    ]
