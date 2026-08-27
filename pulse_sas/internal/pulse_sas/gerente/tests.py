from datetime import date

from django.contrib.auth.models import User
from django.test import Client, TestCase

from pulse_sas.internal.pulse_sas.personas.models import Convenio, Persona, Rol


def _crear_persona(*, username, nombre, apellido, cedula, sexo='M', correo='', password='x12345678'):
    user = User.objects.create_user(username=username, password=password)
    return Persona.objects.create(
        usuario=user, nombre=nombre, apellido=apellido, cedula=cedula,
        fecha_nacimiento=date(1985, 1, 1), sexo=sexo, correo=correo,
    )


class VistaGerenteTests(TestCase):
    """Cubre `vista_gerente` -- crear convenio, crear empleado (roles
    acotados a empleado). Gerente y Recepcionista son categorías
    separadas desde 2026-08-25 (antes sub-roles de 'administrativo')."""

    def setUp(self):
        self.rol_gerente = Rol.objects.get_or_create(
            nombre='gerente', defaults={'categoria': Rol.Categoria.GERENTE}
        )[0]
        self.persona = _crear_persona(
            username='gerente1', nombre='Ger', apellido='Uno', cedula='6000000006',
        )
        self.persona.roles.add(self.rol_gerente)
        self.client = Client()
        self.client.login(username='gerente1', password='x12345678')

    def test_crear_convenio(self):
        resp = self.client.post('/dashboard/gerente/', {
            'accion': 'crear_convenio',
            'nombre': 'Convenio Admin Test', 'nit': '900999888-1', 'telefono': '3009998887',
            'especialidad': 'Odontología',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Convenio.objects.filter(nombre='Convenio Admin Test').exists())

    def test_crear_empleado(self):
        rol_medico = Rol.objects.create(nombre='rol_empleado_test', categoria=Rol.Categoria.MEDICO)
        resp = self.client.post('/dashboard/gerente/', {
            'accion': 'crear_empleado',
            'username': 'nuevo_empleado', 'email': 'empleado@example.com',
            'password1': 'x12345678', 'password2': 'x12345678',
            'nombre': 'Nuevo', 'apellido': 'Empleado', 'tipo_documento': 'CC', 'cedula': '6000000002',
            'fecha_nacimiento': '1990-01-01', 'especialidad': '',
            'roles': [rol_medico.id],
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Persona.objects.filter(cedula='6000000002').exists())

    def test_crear_empleado_no_puede_asignar_rol_admin(self):
        """`EmpleadoRegistroForm.roles_queryset` está acotado a roles de
        empleado -- un rol Admin en el POST debe ser rechazado."""
        rol_admin = Rol.objects.get_or_create(nombre='admin', defaults={'categoria': Rol.Categoria.ADMIN})[0]
        resp = self.client.post('/dashboard/gerente/', {
            'accion': 'crear_empleado',
            'username': 'hack_admin', 'email': 'hack@example.com',
            'password1': 'x12345678', 'password2': 'x12345678',
            'nombre': 'Hack', 'apellido': 'Admin', 'tipo_documento': 'CC', 'cedula': '6000000003',
            'fecha_nacimiento': '1990-01-01', 'especialidad': '',
            'roles': [rol_admin.id],
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='hack_admin').exists())

    def test_recepcionista_no_puede_registrar_empleado(self):
        """Recepcionista no es Gerente -- rechazado por `_usuario_tiene_rol`
        antes de llegar al form."""
        rol_recepcionista = Rol.objects.get_or_create(
            nombre='recepcionista', defaults={'categoria': Rol.Categoria.RECEPCIONISTA}
        )[0]
        recepcionista = _crear_persona(
            username='recep_no_empleado', nombre='Rec', apellido='NoEmpleado', cedula='6000000008',
        )
        recepcionista.roles.add(rol_recepcionista)
        self.client.login(username='recep_no_empleado', password='x12345678')

        resp = self.client.get('/dashboard/gerente/')
        self.assertEqual(resp.status_code, 302)
