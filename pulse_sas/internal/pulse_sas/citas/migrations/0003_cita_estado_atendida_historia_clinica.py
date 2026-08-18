import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0002_cita_tipo_cita'),
        ('personas', '0012_receta_itemreceta'),
    ]

    operations = [
        migrations.AddField(
            model_name='cita',
            name='historia_clinica',
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='cita', to='personas.historiaclinica',
            ),
        ),
        migrations.AlterField(
            model_name='cita',
            name='estado',
            field=models.CharField(
                choices=[
                    ('pendiente', 'Pendiente'), ('confirmada', 'Confirmada'),
                    ('atendida', 'Atendida'), ('cancelada', 'Cancelada'),
                    ('reprogramada', 'Reprogramada'),
                ],
                default='pendiente', max_length=20,
            ),
        ),
    ]
