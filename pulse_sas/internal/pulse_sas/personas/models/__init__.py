"""Modelos de dominio de `personas`, partidos en varios archivos por
tamaño (ver PLAN_REFACTOR_ARQUITECTURA_POR_ROL.md). Se reexporta todo
acá para que `from ...personas.models import Persona` siga funcionando
igual en todo el proyecto, y para que Django descubra los modelos.

Partir `models.py` en un paquete NO genera migraciones nuevas: Django
identifica cada modelo por `app_label` + nombre de clase, no por archivo."""

from .catalogo import Ciudad, Pais, PaisCiudad, Rol, TipoSangre
from .persona import Persona, RolPersona, TipoSangrePersona
from .historia_clinica import (
    Antecedente,
    DatosAdministrativos,
    Diagnostico,
    ExamenComplementario,
    ExamenFisico,
    HistoriaClinica,
    HistoriaClinicaPersona,
    HistoriaEnfermedadActual,
    ItemReceta,
    MotivoConsulta,
    PlanManejo,
    Receta,
)
from .otros import Convenio, ContactoEmergencia, Jornada, SolicitudRegistroPaciente

__all__ = [
    'Ciudad', 'Pais', 'PaisCiudad', 'Rol', 'TipoSangre',
    'Persona', 'RolPersona', 'TipoSangrePersona',
    'Antecedente', 'DatosAdministrativos', 'Diagnostico', 'ExamenComplementario',
    'ExamenFisico', 'HistoriaClinica', 'HistoriaClinicaPersona',
    'HistoriaEnfermedadActual', 'ItemReceta', 'MotivoConsulta', 'PlanManejo', 'Receta',
    'Convenio', 'ContactoEmergencia', 'Jornada', 'SolicitudRegistroPaciente',
]
