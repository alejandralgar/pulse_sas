from django.db import migrations

CIUDADES_COLOMBIA = [
    'Bogotá', 'Medellín', 'Cali', 'Barranquilla', 'Cartagena de Indias', 'Cúcuta',
    'Bucaramanga', 'Pereira', 'Santa Marta', 'Ibagué', 'Pasto', 'Manizales', 'Neiva',
    'Villavicencio', 'Armenia', 'Valledupar', 'Montería', 'Sincelejo', 'Popayán', 'Tunja',
    'Riohacha', 'Quibdó', 'Florencia', 'Yopal', 'Arauca', 'Mocoa', 'San José del Guaviare',
    'Mitú', 'Puerto Carreño', 'Inírida', 'Leticia', 'San Andrés',
]


def seed(apps, schema_editor):
    Pais = apps.get_model('personas', 'Pais')
    Ciudad = apps.get_model('personas', 'Ciudad')
    PaisCiudad = apps.get_model('personas', 'PaisCiudad')

    Pais.objects.exclude(nombre='Colombia').delete()
    Ciudad.objects.all().delete()

    colombia, _ = Pais.objects.get_or_create(nombre='Colombia', defaults={'codigo_iso': 'CO'})

    for nombre_ciudad in CIUDADES_COLOMBIA:
        ciudad, _ = Ciudad.objects.get_or_create(nombre=nombre_ciudad)
        PaisCiudad.objects.get_or_create(pais=colombia, ciudad=ciudad)


class Migration(migrations.Migration):

    dependencies = [
        ('personas', '0004_seed_capitales'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
