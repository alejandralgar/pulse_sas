from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from pulse_sas.internal.pulse_sas.accounts.permissions import _usuario_tiene_rol
from pulse_sas.internal.pulse_sas.personas.models import Rol


@login_required
def vista_guardia(request):
    if not _usuario_tiene_rol(request.user, Rol.Categoria.GUARDIA):
        messages.error(request, 'No tienes permisos de guardia.')
        return redirect('dashboard')
    return render(request, 'guardia/dashboard.html')
