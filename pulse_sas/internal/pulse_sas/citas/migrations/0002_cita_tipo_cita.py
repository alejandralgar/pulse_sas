from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cita',
            name='tipo_cita',
            field=models.CharField(
                'tipo de cita',
                max_length=50,
                blank=True,
                choices=[
                    ('consulta_general', 'Consulta general'),
                    ('control', 'Control'),
                    ('urgencia', 'Urgencia'),
                    ('especialista', 'Especialista'),
                    ('laboratorio', 'Laboratorio / Examen'),
                ],
            ),
        ),
    ]
