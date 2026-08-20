from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone

from pulse_sas.internal.pulse_sas.personas.models import Persona

from .models import Cita


def _crear_paciente(*, username, cedula, password='x12345678'):
    user = User.objects.create_user(username=username, password=password)
    return Persona.objects.create(
        usuario=user, nombre='Pac', apellido='Test', cedula=cedula,
        fecha_nacimiento=date(1990, 1, 1), sexo='F', correo='',
    )


class SolicitarCitaFormTests(TestCase):
    """Cubre `SolicitarCitaForm` / `citas/views.py::solicitar_cita` --
    único formulario real que tiene el Paciente para pedir cita."""

    def setUp(self):
        self.paciente = _crear_paciente(username='paciente_cita', cedula='7000000001')
        self.client = Client()
        self.client.login(username='paciente_cita', password='x12345678')
        self.manana = timezone.localdate() + timedelta(days=1)

    def test_solicitar_cita_crea_pendiente(self):
        resp = self.client.post('/cliente/cita/solicitar/', {
            'tipo_cita': Cita.TipoCita.CONSULTA_GENERAL,
            'fecha': self.manana.isoformat(), 'hora': '09:00', 'motivo': 'chequeo general',
        })
        self.assertEqual(resp.status_code, 302)
        cita = Cita.objects.get(persona=self.paciente)
        self.assertEqual(cita.estado, Cita.Estado.PENDIENTE)
        self.assertIsNone(cita.medico)

    def test_solicitar_cita_fecha_pasada_no_guarda(self):
        ayer = timezone.localdate() - timedelta(days=1)
        resp = self.client.post('/cliente/cita/solicitar/', {
            'tipo_cita': Cita.TipoCita.CONSULTA_GENERAL,
            'fecha': ayer.isoformat(), 'hora': '09:00', 'motivo': '',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Cita.objects.filter(persona=self.paciente).exists())

    def test_solicitar_cita_horario_ocupado_no_guarda(self):
        fecha_hora = timezone.make_aware(
            timezone.datetime.combine(self.manana, timezone.datetime.min.time().replace(hour=9))
        )
        otro = _crear_paciente(username='paciente_cita_otro', cedula='7000000002')
        Cita.objects.create(
            persona=otro, fecha_hora=fecha_hora, estado=Cita.Estado.PENDIENTE,
            tipo_cita=Cita.TipoCita.CONSULTA_GENERAL, motivo='primero',
        )
        resp = self.client.post('/cliente/cita/solicitar/', {
            'tipo_cita': Cita.TipoCita.CONSULTA_GENERAL,
            'fecha': self.manana.isoformat(), 'hora': '09:00', 'motivo': '',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Cita.objects.filter(persona=self.paciente).count(), 0)

    def test_solicitar_cita_sin_tipo_ni_hora_no_guarda(self):
        resp = self.client.post('/cliente/cita/solicitar/', {
            'tipo_cita': '', 'fecha': self.manana.isoformat(), 'hora': '', 'motivo': '',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Cita.objects.filter(persona=self.paciente).exists())


class HorariosDisponiblesViewTests(TestCase):
    """Cubre `citas/views.py::horarios_disponibles`, el endpoint JSON que
    usa el calendario de "Solicitar Cita" del paciente."""

    def setUp(self):
        self.paciente = _crear_paciente(username='paciente_horarios', cedula='7000000003')
        self.client = Client()
        self.client.login(username='paciente_horarios', password='x12345678')
        self.fecha = timezone.localdate() + timedelta(days=2)

    def test_devuelve_horas_ocupadas_de_la_fecha(self):
        fecha_hora = timezone.make_aware(
            timezone.datetime.combine(self.fecha, timezone.datetime.min.time().replace(hour=10))
        )
        Cita.objects.create(
            persona=self.paciente, fecha_hora=fecha_hora, estado=Cita.Estado.CONFIRMADA,
            tipo_cita=Cita.TipoCita.CONSULTA_GENERAL, motivo='x',
        )
        resp = self.client.get('/cliente/cita/horarios/', {'fecha': self.fecha.isoformat()})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['ocupados'], ['10:00'])

    def test_fecha_sin_citas_devuelve_vacio(self):
        resp = self.client.get('/cliente/cita/horarios/', {'fecha': self.fecha.isoformat()})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['ocupados'], [])
