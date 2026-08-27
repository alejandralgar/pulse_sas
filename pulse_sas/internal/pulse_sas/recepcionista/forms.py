from pulse_sas.internal.pulse_sas.personas.forms.registro import _RegistroUsuarioBaseForm
from pulse_sas.internal.pulse_sas.personas.models import Rol


class PacienteRegistroForm(_RegistroUsuarioBaseForm):
    """R003 — Recepcionista registra pacientes. Solo rol Cliente/Paciente."""

    roles_queryset = Rol.objects.filter(categoria=Rol.Categoria.CLIENTE_PACIENTE)
