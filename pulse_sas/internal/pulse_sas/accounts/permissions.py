def _usuario_tiene_rol(user, categoria):
    """True si `user` es superuser o tiene `categoria` entre sus roles
    reales en BD (Persona.roles). Único punto de verdad para permisos por
    rol — no confiar en lo que el usuario eligió en un <select>.

    Vive en su propio módulo (no en accounts/views.py) para que las apps
    de cada rol (gerente, recepcionista, medico, etc.) puedan importarlo
    sin generar un import circular con accounts/views.py, que a su vez
    importa las vistas de esas apps para armar VISTA_POR_ROL."""
    if user.is_superuser:
        return True
    from pulse_sas.internal.pulse_sas.personas.models import Rol
    return Rol.objects.filter(categoria=categoria, personas__usuario=user).exists()
