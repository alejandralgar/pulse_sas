from pulse_sas.internal.pulse_sas.personas.forms.registro import (
    _EditarPersonaBaseForm, _RegistroUsuarioBaseForm,
)
from pulse_sas.internal.pulse_sas.personas.models import Rol

EMPLEADO_CATEGORIAS = [
    Rol.Categoria.GERENTE, Rol.Categoria.RECEPCIONISTA,
    Rol.Categoria.MEDICO, Rol.Categoria.ENFERMERA, Rol.Categoria.GUARDIA,
]


class EmpleadoRegistroForm(_RegistroUsuarioBaseForm):
    """R003 — Gerente registra empleados: médico, enfermera, gerencia,
    recepción, guardia. No puede crear Admin ni Paciente desde acá."""

    roles_queryset = Rol.objects.filter(categoria__in=EMPLEADO_CATEGORIAS)


class EmpleadoEditForm(_EditarPersonaBaseForm):
    """R003 — Gerente edita empleados, solo roles de empleado."""

    roles_queryset = Rol.objects.filter(categoria__in=EMPLEADO_CATEGORIAS)
