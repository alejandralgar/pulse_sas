from django.db import migrations

CAPITALES = {
    'Afganistán': 'Kabul', 'Albania': 'Tirana', 'Alemania': 'Berlín', 'Andorra': 'Andorra la Vieja',
    'Angola': 'Luanda', 'Antigua y Barbuda': "Saint John's", 'Arabia Saudita': 'Riad', 'Argelia': 'Argel',
    'Argentina': 'Buenos Aires', 'Armenia': 'Ereván', 'Australia': 'Canberra', 'Austria': 'Viena',
    'Azerbaiyán': 'Bakú', 'Bahamas': 'Nasáu', 'Bangladés': 'Daca', 'Baréin': 'Manama',
    'Barbados': 'Bridgetown', 'Bélgica': 'Bruselas', 'Belice': 'Belmopán', 'Benín': 'Porto Novo',
    'Bielorrusia': 'Minsk', 'Birmania': 'Naipyidó', 'Bolivia': 'Sucre', 'Bosnia y Herzegovina': 'Sarajevo',
    'Botsuana': 'Gaborone', 'Brasil': 'Brasilia', 'Brunéi': 'Bandar Seri Begawan', 'Bulgaria': 'Sofía',
    'Burkina Faso': 'Uagadugú', 'Burundi': 'Buyumbura', 'Bután': 'Timbu', 'Cabo Verde': 'Praia',
    'Camboya': 'Nom Pen', 'Camerún': 'Yaundé', 'Canadá': 'Ottawa', 'Catar': 'Doha',
    'Chad': 'Yamena', 'Chile': 'Santiago', 'China': 'Pekín', 'Chipre': 'Nicosia',
    'Ciudad del Vaticano': 'Ciudad del Vaticano', 'Colombia': 'Bogotá', 'Comoras': 'Moroni',
    'Corea del Norte': 'Pionyang', 'Corea del Sur': 'Seúl', 'Costa de Marfil': 'Yamusukro',
    'Costa Rica': 'San José', 'Croacia': 'Zagreb', 'Cuba': 'La Habana', 'Dinamarca': 'Copenhague',
    'Dominica': 'Roseau', 'Ecuador': 'Quito', 'Egipto': 'El Cairo', 'El Salvador': 'San Salvador',
    'Emiratos Árabes Unidos': 'Abu Dabi', 'Eritrea': 'Asmara', 'Eslovaquia': 'Bratislava',
    'Eslovenia': 'Liubliana', 'España': 'Madrid', 'Estados Unidos': 'Washington D. C.',
    'Estonia': 'Tallin', 'Etiopía': 'Adís Abeba', 'Filipinas': 'Manila', 'Finlandia': 'Helsinki',
    'Fiyi': 'Suva', 'Francia': 'París', 'Gabón': 'Libreville', 'Gambia': 'Banjul',
    'Georgia': 'Tiflis', 'Ghana': 'Acra', 'Granada': "Saint George's", 'Grecia': 'Atenas',
    'Guatemala': 'Ciudad de Guatemala', 'Guyana': 'Georgetown', 'Guinea': 'Conakry',
    'Guinea-Bisáu': 'Bisáu', 'Guinea Ecuatorial': 'Malabo', 'Haití': 'Puerto Príncipe',
    'Honduras': 'Tegucigalpa', 'Hungría': 'Budapest', 'India': 'Nueva Delhi', 'Indonesia': 'Yakarta',
    'Irak': 'Bagdad', 'Irán': 'Teherán', 'Irlanda': 'Dublín', 'Islandia': 'Reikiavik',
    'Islas Marshall': 'Majuro', 'Islas Salomón': 'Honiara', 'Israel': 'Jerusalén', 'Italia': 'Roma',
    'Jamaica': 'Kingston', 'Japón': 'Tokio', 'Jordania': 'Amán', 'Kazajistán': 'Astaná',
    'Kenia': 'Nairobi', 'Kirguistán': 'Biskek', 'Kiribati': 'Tarawa Sur', 'Kosovo': 'Pristina',
    'Kuwait': 'Ciudad de Kuwait', 'Laos': 'Vientián', 'Lesoto': 'Maseru', 'Letonia': 'Riga',
    'Líbano': 'Beirut', 'Liberia': 'Monrovia', 'Libia': 'Trípoli', 'Liechtenstein': 'Vaduz',
    'Lituania': 'Vilna', 'Luxemburgo': 'Luxemburgo', 'Madagascar': 'Antananarivo',
    'Malasia': 'Kuala Lumpur', 'Malaui': 'Lilongüe', 'Maldivas': 'Malé', 'Malí': 'Bamako',
    'Malta': 'La Valeta', 'Marruecos': 'Rabat', 'Mauricio': 'Port Louis', 'Mauritania': 'Nuakchot',
    'México': 'Ciudad de México', 'Micronesia': 'Palikir', 'Moldavia': 'Chisináu', 'Mónaco': 'Mónaco',
    'Mongolia': 'Ulán Bator', 'Montenegro': 'Podgorica', 'Mozambique': 'Maputo', 'Namibia': 'Windhoek',
    'Nauru': 'Yaren', 'Nepal': 'Katmandú', 'Nicaragua': 'Managua', 'Níger': 'Niamey',
    'Nigeria': 'Abuya', 'Noruega': 'Oslo', 'Nueva Zelanda': 'Wellington', 'Omán': 'Mascate',
    'Países Bajos': 'Ámsterdam', 'Pakistán': 'Islamabad', 'Palaos': 'Ngerulmud', 'Palestina': 'Ramala',
    'Panamá': 'Ciudad de Panamá', 'Papúa Nueva Guinea': 'Port Moresby', 'Paraguay': 'Asunción',
    'Perú': 'Lima', 'Polonia': 'Varsovia', 'Portugal': 'Lisboa', 'Reino Unido': 'Londres',
    'República Centroafricana': 'Bangui', 'República Checa': 'Praga', 'República del Congo': 'Brazzaville',
    'República Democrática del Congo': 'Kinsasa', 'República Dominicana': 'Santo Domingo',
    'Ruanda': 'Kigali', 'Rumanía': 'Bucarest', 'Rusia': 'Moscú', 'Samoa': 'Apia',
    'San Cristóbal y Nieves': 'Basseterre', 'San Marino': 'San Marino',
    'San Vicente y las Granadinas': 'Kingstown', 'Santa Lucía': 'Castries',
    'Santo Tomé y Príncipe': 'Santo Tomé', 'Senegal': 'Dakar', 'Serbia': 'Belgrado',
    'Seychelles': 'Victoria', 'Sierra Leona': 'Freetown', 'Singapur': 'Singapur', 'Siria': 'Damasco',
    'Somalia': 'Mogadiscio', 'Sri Lanka': 'Sri Jayawardenapura Kotte', 'Suazilandia': 'Mbabane',
    'Sudáfrica': 'Pretoria', 'Sudán': 'Jartum', 'Sudán del Sur': 'Yuba', 'Suecia': 'Estocolmo',
    'Suiza': 'Berna', 'Surinam': 'Paramaribo', 'Tailandia': 'Bangkok', 'Tanzania': 'Dodoma',
    'Tayikistán': 'Dusambé', 'Timor Oriental': 'Dili', 'Togo': 'Lomé', 'Tonga': 'Nukualofa',
    'Trinidad y Tobago': 'Puerto España', 'Túnez': 'Túnez', 'Turkmenistán': 'Asjabad',
    'Turquía': 'Ankara', 'Tuvalu': 'Funafuti', 'Ucrania': 'Kiev', 'Uganda': 'Kampala',
    'Uruguay': 'Montevideo', 'Uzbekistán': 'Taskent', 'Vanuatu': 'Port Vila', 'Venezuela': 'Caracas',
    'Vietnam': 'Hanói', 'Yemen': 'Saná', 'Yibuti': 'Yibuti', 'Zambia': 'Lusaka',
    'Zimbabue': 'Harare', 'Taiwán': 'Taipéi',
}


def seed(apps, schema_editor):
    Pais = apps.get_model('personas', 'Pais')
    Ciudad = apps.get_model('personas', 'Ciudad')
    PaisCiudad = apps.get_model('personas', 'PaisCiudad')

    for nombre_pais, nombre_capital in CAPITALES.items():
        try:
            pais = Pais.objects.get(nombre=nombre_pais)
        except Pais.DoesNotExist:
            continue
        ciudad, _ = Ciudad.objects.get_or_create(nombre=nombre_capital)
        PaisCiudad.objects.get_or_create(pais=pais, ciudad=ciudad)


def eliminar(apps, schema_editor):
    Ciudad = apps.get_model('personas', 'Ciudad')
    Ciudad.objects.filter(nombre__in=set(CAPITALES.values())).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('personas', '0003_historiaclinica_ocupacion_and_more'),
    ]

    operations = [
        migrations.RunPython(seed, eliminar),
    ]
