import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personas', '0011_persona_especialidad'),
    ]

    operations = [
        migrations.CreateModel(
            name='Receta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('indicaciones_generales', models.TextField(blank=True)),
                ('fecha_emision', models.DateTimeField(auto_now_add=True)),
                ('historia_clinica', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE, related_name='receta',
                    to='personas.historiaclinica',
                )),
            ],
            options={
                'verbose_name': 'receta médica',
                'verbose_name_plural': 'recetas médicas',
            },
        ),
        migrations.CreateModel(
            name='ItemReceta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('medicamento', models.CharField(max_length=150)),
                ('dosis', models.CharField(blank=True, max_length=100)),
                ('frecuencia', models.CharField(blank=True, max_length=100)),
                ('duracion', models.CharField(blank=True, max_length=100)),
                ('indicaciones', models.CharField(blank=True, max_length=255)),
                ('receta', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='medicamentos',
                    to='personas.receta',
                )),
            ],
            options={
                'verbose_name': 'medicamento recetado',
                'verbose_name_plural': 'medicamentos recetados',
            },
        ),
    ]
