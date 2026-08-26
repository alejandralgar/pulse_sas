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


class VistaAdminTests(TestCase):
    """Cubre cada acción real de `vista_admin` -- crear rol, crear
    usuario, crear convenio, editar usuario, cambiar contraseña,
    eliminar usuario, activar/desactivar. Todas usan `accion=` en el
    mismo `<form>`/POST, ver `accounts/views.py::vista_admin`."""

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
