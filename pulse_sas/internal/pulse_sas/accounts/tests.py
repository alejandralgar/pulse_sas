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


class LoginViewTests(TestCase):
    """Cubre `LoginConRolForm` / `login_view` -- el selector de rol del
    login debe validar contra `Persona.roles` en BD, no confiar en lo
    que el usuario elige en el `<select>` (ver 3_DECISIONES.md, "bypass
    de rol")."""

    def setUp(self):
        self.rol_medico = Rol.objects.create(nombre='medico_login_test', categoria=Rol.Categoria.MEDICO)
        self.persona = _crear_persona(
            username='medico_login', nombre='Med', apellido='Login', cedula='5000000001',
        )
        self.persona.roles.add(self.rol_medico)
        self.client = Client()

    def test_login_con_rol_asignado_entra(self):
        resp = self.client.post('/login/', {
            'username': 'medico_login', 'password': 'x12345678', 'rol': 'medico',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.wsgi_request.user.is_authenticated if hasattr(resp, 'wsgi_request') else True)

    def test_login_con_rol_no_asignado_se_queda_en_login(self):
        resp = self.client.post('/login/', {
            'username': 'medico_login', 'password': 'x12345678', 'rol': 'admin',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['form'].is_valid())
        self.assertIn('rol', resp.context['form'].errors)

    def test_login_sin_elegir_rol_falla(self):
        resp = self.client.post('/login/', {'username': 'medico_login', 'password': 'x12345678', 'rol': ''})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('rol', resp.context['form'].errors)
