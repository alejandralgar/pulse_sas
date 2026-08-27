from datetime import date

from django.contrib.auth.models import User

from pulse_sas.internal.pulse_sas.personas.models import Persona


def _crear_persona(*, username, nombre, apellido, cedula, sexo='M', correo=''):
    user = User.objects.create_user(username=username, password='x12345678')
    return Persona.objects.create(
        usuario=user, nombre=nombre, apellido=apellido, cedula=cedula,
        fecha_nacimiento=date(1985, 1, 1), sexo=sexo, correo=correo,
    )


def _datos_consulta(**overrides):
    """Payload base que replica el <form> real de atender_cita.html /
    editar_historia -- todos los campos, incluyendo los opcionales, tal
    como los manda el navegador."""
    data = {
        'motivo_consulta': 'Dolor en el pecho',
        'padecimiento_actual': 'Le duele el pecho',
        'factores_desencadenantes': 'tose sangre',
        'tratamientos_previos': 'Dejar de fumar',
        'antecedentes_familiares': 'cancer de pulmon',
        'antecedentes_personales_patologicos': '',
        'antecedentes_no_patologicos': 'Asma',
        'tratamiento': 'tiene un silvido que puede ser cancer de pulmon',
        'presion_arterial': '150',
        'frecuencia_cardiaca': '0',
        'impresion_diagnostica': 'silvido en el pecho',
        'diagnostico_confirmado': 'cancer de pulmon',
        'tratamiento_indicado': 'dejar de fumar, vapores',
        'recomendaciones': 'dejar de fumar',
        'fecha_proxima_cita': '',
    }
    data.update(overrides)
    return data


def _formset_management(total, initial=0):
    return {
        'medicamentos-TOTAL_FORMS': str(total),
        'medicamentos-INITIAL_FORMS': str(initial),
        'medicamentos-MIN_NUM_FORMS': '0',
        'medicamentos-MAX_NUM_FORMS': '1000',
    }
