from datetime import date

from django.contrib.auth.models import User
from django.test import Client, TestCase

from pulse_sas.internal.pulse_sas.personas.models import Persona, Rol


def _crear_persona(*, username, nombre, apellido, cedula, sexo='M', correo='', password='x12345678'):
    user = User.objects.create_user(username=username, password=password)
    return Persona.objects.create(
        usuario=user, nombre=nombre, apellido=apellido, cedula=cedula,
        fecha_nacimiento=date(1985, 1, 1), sexo=sexo, correo=correo,
    )


class VistaRecepcionistaTests(TestCase):
    """Cubre `vista_recepcionista` -- registrar paciente, asignar médico
    a una cita pendiente."""

    def setUp(self):
        self.rol_recepcionista = Rol.objects.get_or_create(
            nombre='recepcionista', defaults={'categoria': Rol.Categoria.RECEPCIONISTA}
        )[0]
        self.persona = _crear_persona(
            username='recepcionista1', nombre='Rec', apellido='Uno', cedula='6000000001',
        )
        self.persona.roles.add(self.rol_recepcionista)
        self.client = Client()
        self.client.login(username='recepcionista1', password='x12345678')

    def test_asignar_medico_a_cita_pendiente(self):
        from pulse_sas.internal.pulse_sas.citas.models import Cita
        from django.utils import timezone

        rol_medico = Rol.objects.create(nombre='rol_asignar_test', categoria=Rol.Categoria.MEDICO)
        medico = _crear_persona(username='medico_asignar', nombre='Med', apellido='Asignar', cedula='6000000004')
        medico.roles.add(rol_medico)
        paciente = _crear_persona(username='pac_asignar', nombre='Pac', apellido='Asignar', cedula='6000000005')
        cita = Cita.objects.create(
            persona=paciente, fecha_hora=timezone.now(), estado=Cita.Estado.PENDIENTE,
            tipo_cita=Cita.TipoCita.CONSULTA_GENERAL, motivo='chequeo',
        )
        resp = self.client.post('/dashboard/recepcionista/', {
            'accion': 'asignar_medico', 'cita_id': cita.id, 'medico_id': medico.id,
        })
        self.assertEqual(resp.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.medico_id, medico.id)
        self.assertEqual(cita.estado, Cita.Estado.CONFIRMADA)

    def test_crear_paciente(self):
        rol_paciente = Rol.objects.get_or_create(
            nombre='cliente_paciente', defaults={'categoria': Rol.Categoria.CLIENTE_PACIENTE}
        )[0]
        resp = self.client.post('/dashboard/recepcionista/', {
            'accion': 'crear_paciente',
            'username': 'nuevo_paciente_test', 'email': 'paciente@example.com',
            'password1': 'x12345678', 'password2': 'x12345678',
            'nombre': 'Nuevo', 'apellido': 'Paciente', 'tipo_documento': 'CC', 'cedula': '6000000009',
            'fecha_nacimiento': '1990-01-01', 'especialidad': '',
            'roles': [rol_paciente.id],
            'nombre_completo': 'Contacto Emergencia', 'telefono': '3001234567', 'parentesco': 'Madre',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Persona.objects.filter(cedula='6000000009').exists())
        persona = Persona.objects.get(cedula='6000000009')
        self.assertTrue(persona.contactos_emergencia.filter(nombre_completo='Contacto Emergencia').exists())
        self.assertEqual(persona.registrado_por_id, self.persona.id)

    def test_gerente_no_puede_registrar_paciente(self):
        rol_gerente = Rol.objects.get_or_create(
            nombre='gerente', defaults={'categoria': Rol.Categoria.GERENTE}
        )[0]
        gerente = _crear_persona(
            username='gerente_no_paciente', nombre='Ger', apellido='NoPaciente', cedula='6000000010',
        )
        gerente.roles.add(rol_gerente)
        self.client.login(username='gerente_no_paciente', password='x12345678')

        resp = self.client.get('/dashboard/recepcionista/')
        self.assertEqual(resp.status_code, 302)
