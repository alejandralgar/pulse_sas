from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personas', '0010_persona_telefonos_pais_correo_recuperacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='persona',
            name='especialidad',
            field=models.CharField(
                blank=True, help_text='Solo aplica a personas con rol médico.',
                max_length=150, verbose_name='especialidad médica',
            ),
        ),
    ]
