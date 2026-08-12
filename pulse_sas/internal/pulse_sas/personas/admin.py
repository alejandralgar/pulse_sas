from django.contrib import admin

from .models import (
    Antecedente,
    Ciudad,
    ContactoEmergencia,
    Convenio,
    DatosAdministrativos,
    Diagnostico,
    ExamenComplementario,
    ExamenFisico,
    HistoriaClinica,
    HistoriaClinicaPersona,
    HistoriaEnfermedadActual,
    Jornada,
    MotivoConsulta,
    Pais,
    PaisCiudad,
    Persona,
    PlanManejo,
    Rol,
    RolPersona,
    TipoSangre,
    TipoSangrePersona,
)

admin.site.register(Pais)
admin.site.register(Ciudad)
admin.site.register(PaisCiudad)
admin.site.register(TipoSangre)
admin.site.register(Rol)
admin.site.register(Persona)
admin.site.register(RolPersona)
admin.site.register(TipoSangrePersona)
admin.site.register(HistoriaClinica)
admin.site.register(HistoriaClinicaPersona)
admin.site.register(Antecedente)
admin.site.register(MotivoConsulta)
admin.site.register(HistoriaEnfermedadActual)
admin.site.register(ExamenFisico)
admin.site.register(ExamenComplementario)
admin.site.register(Diagnostico)
admin.site.register(PlanManejo)
admin.site.register(DatosAdministrativos)
admin.site.register(ContactoEmergencia)
admin.site.register(Jornada)
admin.site.register(Convenio)
