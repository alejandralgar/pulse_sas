from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from pulse_sas.internal.pulse_sas.personas.models import Persona, Rol, RolPersona

User = get_user_model()

DEMO_PASSWORD = 'Pulsesas123'

# (username, nombre_rol, categoria, nombre, apellido, cedula, especialidad)
DEMO_PERSONAS = [
    ('demo_admin', 'admin', Rol.Categoria.ADMIN, 'Ana', 'Admin', '900000001', ''),
    ('demo_recepcion', 'recepcionista', Rol.Categoria.RECEPCIONISTA, 'Rita', 'Recepción', '900000002', ''),
    ('demo_gerente', 'gerente', Rol.Categoria.GERENTE, 'Gina', 'Gerente', '900000008', ''),
    ('demo_medico', 'medico', Rol.Categoria.MEDICO, 'Marco', 'Médico', '900000003', 'Medicina general'),
    ('demo_enfermera', 'enfermera', Rol.Categoria.ENFERMERA, 'Elena', 'Enfermera', '900000004', ''),
    ('demo_guardia', 'guardia', Rol.Categoria.GUARDIA, 'Gustavo', 'Guardia', '900000005', ''),
    ('demo_paciente', 'cliente_paciente', Rol.Categoria.CLIENTE_PACIENTE, 'Pedro', 'Paciente', '900000006', ''),
    ('demo_empresa', 'empresa', Rol.Categoria.EMPRESA, 'Empresa', 'Convenio', '900000007', ''),
]


class Command(BaseCommand):
    help = 'Crea usuarios demo (uno por rol) con Persona y RolPersona enlazados, pa poder loguear y probar cada dashboard local. Idempotente: se puede correr varias veces.'

    def handle(self, *args, **options):
        with transaction.atomic():
            self._fix_roles()
            for username, nombre_rol, categoria, nombre, apellido, cedula, especialidad in DEMO_PERSONAS:
                self._crear_persona_demo(
                    username, nombre_rol, categoria, nombre, apellido, cedula, especialidad
                )
            self._crear_superuser()

        self.stdout.write(self.style.SUCCESS(
            f'\nListo. Password para todas las cuentas demo: {DEMO_PASSWORD}'
        ))

    def _fix_roles(self):
        # 0002_seed_datos.py guardó 'medico' y 'enfermera' con categoria='administrativo'
        # (bug de la migración original: 0007 cambió el choices pero no los datos ya insertados).
        # update_or_create autocorrige la categoria sin importar el estado previo de la fila.
        for _, nombre_rol, categoria, *_ in DEMO_PERSONAS:
            Rol.objects.update_or_create(nombre=nombre_rol, defaults={'categoria': categoria})

    def _crear_persona_demo(self, username, nombre_rol, categoria, nombre, apellido, cedula, especialidad):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={'email': f'{username}@pulsesas.local'},
        )
        user.set_password(DEMO_PASSWORD)
        user.email = f'{username}@pulsesas.local'
        user.save()

        persona, _ = Persona.objects.update_or_create(
            cedula=cedula,
            defaults={
                'usuario': user,
                'nombre': nombre,
                'apellido': apellido,
                'fecha_nacimiento': date(1990, 1, 1),
                'correo': f'{username}@pulsesas.local',
                'especialidad': especialidad,
            },
        )

        rol = Rol.objects.get(nombre=nombre_rol)
        RolPersona.objects.get_or_create(persona=persona, rol=rol)

        self.stdout.write(f'  {username} -> rol "{categoria}" (Persona #{persona.pk})')

    def _crear_superuser(self):
        user, created = User.objects.get_or_create(
            username='demo_superuser',
            defaults={'email': 'demo_superuser@pulsesas.local', 'is_staff': True, 'is_superuser': True},
        )
        if not created:
            user.is_staff = True
            user.is_superuser = True
        user.set_password(DEMO_PASSWORD)
        user.save()
        self.stdout.write(f'  demo_superuser -> superuser (panel /django-admin/)')
