from django import forms

from pulse_sas.internal.pulse_sas.personas.forms.registro import (
    _EditarPersonaBaseForm, _RegistroUsuarioBaseForm,
)
from pulse_sas.internal.pulse_sas.personas.models import Rol


class RolForm(forms.ModelForm):
    class Meta:
        model = Rol
        fields = ['nombre', 'categoria']


class AdminRegistroUsuarioForm(_RegistroUsuarioBaseForm):
    """R002 — Admin registra cualquier usuario (incluye otros admins)."""

    roles_queryset = Rol.objects.all()


class AdminEditarUsuarioForm(_EditarPersonaBaseForm):
    """R004 — Admin edita cualquier usuario, con cualquier rol."""

    roles_queryset = Rol.objects.all()
