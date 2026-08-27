from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from pulse_sas.internal.pulse_sas.accounts.permissions import _usuario_tiene_rol
from pulse_sas.internal.pulse_sas.personas.forms import ConvenioForm
from pulse_sas.internal.pulse_sas.personas.models import Convenio, Persona, Rol

from .forms import EMPLEADO_CATEGORIAS, EmpleadoRegistroForm


@login_required
def vista_gerente(request):
    """Gerente: manejo administrativo/financiero -- registrar empleados
    (médicos, enfermeras, guardias, recepcionistas, otros gerentes) y
    gestionar convenios/empresas. Ver personas/models.py::Rol.Categoria."""
    if not _usuario_tiene_rol(request.user, Rol.Categoria.GERENTE):
        messages.error(request, 'No tienes permisos de gerente.')
        return redirect('dashboard')

    try:
        persona_gerente = request.user.persona
    except Exception:
        persona_gerente = None

    convenio_form = ConvenioForm()
    empleado_form = EmpleadoRegistroForm()

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'crear_convenio':
            convenio_form = ConvenioForm(request.POST)
            if convenio_form.is_valid():
                convenio_form.save()
                messages.success(request, 'Convenio registrado correctamente.')
                return redirect(reverse('dashboard_gerente') + '?seccion=convenios')

        elif accion == 'crear_empleado':
            empleado_form = EmpleadoRegistroForm(request.POST)
            if empleado_form.is_valid():
                empleado_form.save(registrado_por=persona_gerente)
                messages.success(request, 'Empleado registrado correctamente.')
                return redirect(reverse('dashboard_gerente') + '?seccion=empleados')

    empleados = Persona.objects.filter(
        roles__categoria__in=EMPLEADO_CATEGORIAS
    ).prefetch_related('roles').distinct().order_by('-fecha_creacion')

    ctx = {
        'convenio_form': convenio_form,
        'convenios': Convenio.objects.all().order_by('nombre'),
        'empleado_form': empleado_form,
        'empleados': empleados,
        'seccion_activa': request.GET.get('seccion', 'resumen'),
    }
    return render(request, 'gerente/dashboard.html', ctx)
