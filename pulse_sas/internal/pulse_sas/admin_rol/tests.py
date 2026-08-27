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


class VistaAdminTests(TestCase):
    """Cubre cada acción real de `vista_admin` -- crear rol, crear
    usuario, crear convenio, editar usuario, cambiar contraseña,
    eliminar usuario, activar/desactivar. Todas usan `accion=` en el
    mismo `<form>`/POST, ver `admin_rol/views.py::vista_admin`."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin_test', password='x12345678', email='admin@example.com',
        )
        self.client = Client()
        self.client.login(username='admin_test', password='x12345678')

    def test_crear_rol(self):
        resp = self.client.post('/dashboard/admin/', {
            'accion': 'crear_rol', 'nombre': 'rol_nuevo_test', 'categoria': Rol.Categoria.GERENTE,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Rol.objects.filter(nombre='rol_nuevo_test').exists())

    def test_crear_rol_duplicado_no_guarda(self):
        Rol.objects.create(nombre='rol_dup_test', categoria=Rol.Categoria.GERENTE)
        resp = self.client.post('/dashboard/admin/', {
            'accion': 'crear_rol', 'nombre': 'rol_dup_test', 'categoria': Rol.Categoria.MEDICO,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Rol.objects.filter(nombre='rol_dup_test').count(), 1)

    def test_crear_usuario(self):
        rol = Rol.objects.create(nombre='rol_crear_usuario_test', categoria=Rol.Categoria.MEDICO)
        resp = self.client.post('/dashboard/admin/', {
            'accion': 'crear_usuario',
            'username': 'nuevo_medico', 'email': 'nuevo@example.com',
            'password1': 'x12345678', 'password2': 'x12345678',
            'nombre': 'Nuevo', 'apellido': 'Medico', 'tipo_documento': 'CC', 'cedula': '5000000002',
            'fecha_nacimiento': '1990-01-01', 'especialidad': 'Pediatría',
            'roles': [rol.id],
        })
        self.assertEqual(resp.status_code, 302)
        persona = Persona.objects.get(cedula='5000000002')
        self.assertEqual(persona.usuario.username, 'nuevo_medico')
        self.assertIn(rol, persona.roles.all())

    def test_crear_usuario_passwords_distintas_no_guarda(self):
        rol = Rol.objects.create(nombre='rol_pw_test', categoria=Rol.Categoria.MEDICO)
        resp = self.client.post('/dashboard/admin/', {
            'accion': 'crear_usuario',
            'username': 'pw_mismatch', 'email': 'pw@example.com',
            'password1': 'x12345678', 'password2': 'diferente123',
            'nombre': 'Pw', 'apellido': 'Mismatch', 'cedula': '5000000003',
            'fecha_nacimiento': '1990-01-01', 'especialidad': '',
            'roles': [rol.id],
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='pw_mismatch').exists())

    def test_crear_convenio(self):
        resp = self.client.post('/dashboard/admin/', {
            'accion': 'crear_convenio',
            'nombre': 'EPS Test', 'nit': '900123456-1', 'telefono': '3001234567',
            'especialidad': 'Medicina general',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Convenio.objects.filter(nombre='EPS Test').exists())

    def test_editar_usuario(self):
        rol = Rol.objects.create(nombre='rol_editar_test', categoria=Rol.Categoria.MEDICO)
        persona = _crear_persona(username='a_editar', nombre='Antes', apellido='Editar', cedula='5000000004')
        persona.roles.add(rol)
        resp = self.client.post('/dashboard/admin/', {
            'accion': 'editar_usuario', 'persona_id': persona.id,
            'nombre': 'Despues', 'apellido': 'Editar', 'tipo_documento': 'CC', 'cedula': '5000000004',
            'fecha_nacimiento': '1985-01-01', 'correo': 'editado@example.com', 'especialidad': '',
            'roles': [rol.id],
        })
        self.assertEqual(resp.status_code, 302)
        persona.refresh_from_db()
        self.assertEqual(persona.nombre, 'Despues')
        self.assertEqual(persona.correo, 'editado@example.com')

    def test_cambiar_password(self):
        persona = _crear_persona(username='cambiar_pw', nombre='Cambiar', apellido='Pw', cedula='5000000005')
        resp = self.client.post('/dashboard/admin/', {
            'accion': 'cambiar_password', 'persona_id': persona.id,
            'new_password1': 'nuevaPass123!', 'new_password2': 'nuevaPass123!',
        })
        self.assertEqual(resp.status_code, 302)
        persona.usuario.refresh_from_db()
        self.assertTrue(persona.usuario.check_password('nuevaPass123!'))

    def test_eliminar_usuario(self):
        persona = _crear_persona(username='a_eliminar', nombre='A', apellido='Eliminar', cedula='5000000006')
        user_id = persona.usuario_id
        resp = self.client.post('/dashboard/admin/', {'accion': 'eliminar_usuario', 'persona_id': persona.id})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Persona.objects.filter(id=persona.id).exists())
        user = User.objects.get(id=user_id)
        self.assertFalse(user.is_active)

    def test_no_puede_eliminarse_a_si_mismo(self):
        persona_admin = _crear_persona(username='admin_self', nombre='Admin', apellido='Self', cedula='5000000007')
        persona_admin.usuario = self.admin_user
        persona_admin.save(update_fields=['usuario'])
        resp = self.client.post('/dashboard/admin/', {'accion': 'eliminar_usuario', 'persona_id': persona_admin.id})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Persona.objects.filter(id=persona_admin.id).exists())

    def test_toggle_activo(self):
        persona = _crear_persona(username='a_togglear', nombre='A', apellido='Togglear', cedula='5000000008')
        self.assertTrue(persona.usuario.is_active)
        resp = self.client.post('/dashboard/admin/', {'accion': 'toggle_activo', 'persona_id': persona.id})
        self.assertEqual(resp.status_code, 302)
        persona.usuario.refresh_from_db()
        self.assertFalse(persona.usuario.is_active)

    def test_no_admin_no_accede(self):
        _crear_persona(username='no_admin', nombre='No', apellido='Admin', cedula='5000000009')
        client2 = Client()
        client2.login(username='no_admin', password='x12345678')
        resp = client2.get('/dashboard/admin/')
        self.assertEqual(resp.status_code, 302)
