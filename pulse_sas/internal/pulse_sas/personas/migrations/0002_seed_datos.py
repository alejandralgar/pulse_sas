from django.db import migrations

ROLES = [
    ('admin', 'admin'),
    ('cliente_paciente', 'cliente_paciente'),
    ('empresa', 'empresa'),
    ('gerente', 'administrativo'),
    ('supervisor', 'administrativo'),
    ('medico', 'administrativo'),
    ('enfermera', 'administrativo'),
    ('contadora', 'administrativo'),
    ('recepcionista', 'administrativo'),
]

TIPOS_SANGRE = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']

PAISES = [
    ('Afganistán', 'AF'), ('Albania', 'AL'), ('Alemania', 'DE'), ('Andorra', 'AD'),
    ('Angola', 'AO'), ('Antigua y Barbuda', 'AG'), ('Arabia Saudita', 'SA'), ('Argelia', 'DZ'),
    ('Argentina', 'AR'), ('Armenia', 'AM'), ('Australia', 'AU'), ('Austria', 'AT'),
    ('Azerbaiyán', 'AZ'), ('Bahamas', 'BS'), ('Bangladés', 'BD'), ('Baréin', 'BH'),
    ('Barbados', 'BB'), ('Bélgica', 'BE'), ('Belice', 'BZ'), ('Benín', 'BJ'),
    ('Bielorrusia', 'BY'), ('Birmania', 'MM'), ('Bolivia', 'BO'), ('Bosnia y Herzegovina', 'BA'),
    ('Botsuana', 'BW'), ('Brasil', 'BR'), ('Brunéi', 'BN'), ('Bulgaria', 'BG'),
    ('Burkina Faso', 'BF'), ('Burundi', 'BI'), ('Bután', 'BT'), ('Cabo Verde', 'CV'),
    ('Camboya', 'KH'), ('Camerún', 'CM'), ('Canadá', 'CA'), ('Catar', 'QA'),
    ('Chad', 'TD'), ('Chile', 'CL'), ('China', 'CN'), ('Chipre', 'CY'),
    ('Ciudad del Vaticano', 'VA'), ('Colombia', 'CO'), ('Comoras', 'KM'), ('Corea del Norte', 'KP'),
    ('Corea del Sur', 'KR'), ('Costa de Marfil', 'CI'), ('Costa Rica', 'CR'), ('Croacia', 'HR'),
    ('Cuba', 'CU'), ('Dinamarca', 'DK'), ('Dominica', 'DM'), ('Ecuador', 'EC'),
    ('Egipto', 'EG'), ('El Salvador', 'SV'), ('Emiratos Árabes Unidos', 'AE'), ('Eritrea', 'ER'),
    ('Eslovaquia', 'SK'), ('Eslovenia', 'SI'), ('España', 'ES'), ('Estados Unidos', 'US'),
    ('Estonia', 'EE'), ('Etiopía', 'ET'), ('Filipinas', 'PH'), ('Finlandia', 'FI'),
    ('Fiyi', 'FJ'), ('Francia', 'FR'), ('Gabón', 'GA'), ('Gambia', 'GM'),
    ('Georgia', 'GE'), ('Ghana', 'GH'), ('Granada', 'GD'), ('Grecia', 'GR'),
    ('Guatemala', 'GT'), ('Guyana', 'GY'), ('Guinea', 'GN'), ('Guinea-Bisáu', 'GW'),
    ('Guinea Ecuatorial', 'GQ'), ('Haití', 'HT'), ('Honduras', 'HN'), ('Hungría', 'HU'),
    ('India', 'IN'), ('Indonesia', 'ID'), ('Irak', 'IQ'), ('Irán', 'IR'),
    ('Irlanda', 'IE'), ('Islandia', 'IS'), ('Islas Marshall', 'MH'), ('Islas Salomón', 'SB'),
    ('Israel', 'IL'), ('Italia', 'IT'), ('Jamaica', 'JM'), ('Japón', 'JP'),
    ('Jordania', 'JO'), ('Kazajistán', 'KZ'), ('Kenia', 'KE'), ('Kirguistán', 'KG'),
    ('Kiribati', 'KI'), ('Kosovo', 'XK'), ('Kuwait', 'KW'), ('Laos', 'LA'),
    ('Lesoto', 'LS'), ('Letonia', 'LV'), ('Líbano', 'LB'), ('Liberia', 'LR'),
    ('Libia', 'LY'), ('Liechtenstein', 'LI'), ('Lituania', 'LT'), ('Luxemburgo', 'LU'),
    ('Madagascar', 'MG'), ('Malasia', 'MY'), ('Malaui', 'MW'), ('Maldivas', 'MV'),
    ('Malí', 'ML'), ('Malta', 'MT'), ('Marruecos', 'MA'), ('Mauricio', 'MU'),
    ('Mauritania', 'MR'), ('México', 'MX'), ('Micronesia', 'FM'), ('Moldavia', 'MD'),
    ('Mónaco', 'MC'), ('Mongolia', 'MN'), ('Montenegro', 'ME'), ('Mozambique', 'MZ'),
    ('Namibia', 'NA'), ('Nauru', 'NR'), ('Nepal', 'NP'), ('Nicaragua', 'NI'),
    ('Níger', 'NE'), ('Nigeria', 'NG'), ('Noruega', 'NO'), ('Nueva Zelanda', 'NZ'),
    ('Omán', 'OM'), ('Países Bajos', 'NL'), ('Pakistán', 'PK'), ('Palaos', 'PW'),
    ('Palestina', 'PS'), ('Panamá', 'PA'), ('Papúa Nueva Guinea', 'PG'), ('Paraguay', 'PY'),
    ('Perú', 'PE'), ('Polonia', 'PL'), ('Portugal', 'PT'), ('Reino Unido', 'GB'),
    ('República Centroafricana', 'CF'), ('República Checa', 'CZ'), ('República del Congo', 'CG'),
    ('República Democrática del Congo', 'CD'), ('República Dominicana', 'DO'), ('Ruanda', 'RW'),
    ('Rumanía', 'RO'), ('Rusia', 'RU'), ('Samoa', 'WS'), ('San Cristóbal y Nieves', 'KN'),
    ('San Marino', 'SM'), ('San Vicente y las Granadinas', 'VC'), ('Santa Lucía', 'LC'),
    ('Santo Tomé y Príncipe', 'ST'), ('Senegal', 'SN'), ('Serbia', 'RS'), ('Seychelles', 'SC'),
    ('Sierra Leona', 'SL'), ('Singapur', 'SG'), ('Siria', 'SY'), ('Somalia', 'SO'),
    ('Sri Lanka', 'LK'), ('Suazilandia', 'SZ'), ('Sudáfrica', 'ZA'), ('Sudán', 'SD'),
    ('Sudán del Sur', 'SS'), ('Suecia', 'SE'), ('Suiza', 'CH'), ('Surinam', 'SR'),
    ('Tailandia', 'TH'), ('Tanzania', 'TZ'), ('Tayikistán', 'TJ'), ('Timor Oriental', 'TL'),
    ('Togo', 'TG'), ('Tonga', 'TO'), ('Trinidad y Tobago', 'TT'), ('Túnez', 'TN'),
    ('Turkmenistán', 'TM'), ('Turquía', 'TR'), ('Tuvalu', 'TV'), ('Ucrania', 'UA'),
    ('Uganda', 'UG'), ('Uruguay', 'UY'), ('Uzbekistán', 'UZ'), ('Vanuatu', 'VU'),
    ('Venezuela', 'VE'), ('Vietnam', 'VN'), ('Yemen', 'YE'), ('Yibuti', 'DJ'),
    ('Zambia', 'ZM'), ('Zimbabue', 'ZW'), ('Taiwán', 'TW'),
]


def seed(apps, schema_editor):
    Rol = apps.get_model('personas', 'Rol')
    TipoSangre = apps.get_model('personas', 'TipoSangre')
    Pais = apps.get_model('personas', 'Pais')

    for nombre, categoria in ROLES:
        Rol.objects.get_or_create(nombre=nombre, defaults={'categoria': categoria})

    for nombre in TIPOS_SANGRE:
        TipoSangre.objects.get_or_create(nombre=nombre)

    for nombre, codigo in PAISES:
        Pais.objects.get_or_create(nombre=nombre, defaults={'codigo_iso': codigo})


def eliminar(apps, schema_editor):
    Rol = apps.get_model('personas', 'Rol')
    TipoSangre = apps.get_model('personas', 'TipoSangre')
    Pais = apps.get_model('personas', 'Pais')
    Rol.objects.filter(nombre__in=[r[0] for r in ROLES]).delete()
    TipoSangre.objects.filter(nombre__in=TIPOS_SANGRE).delete()
    Pais.objects.filter(nombre__in=[p[0] for p in PAISES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('personas', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, eliminar),
    ]
