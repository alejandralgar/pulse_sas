from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from pulse_sas.internal.pulse_sas.admin_rol.views import vista_admin
from pulse_sas.internal.pulse_sas.cliente.views_dashboard import vista_cliente
from pulse_sas.internal.pulse_sas.empresa.views import vista_empresa
from pulse_sas.internal.pulse_sas.enfermera.views import vista_enfermera
from pulse_sas.internal.pulse_sas.gerente.views import vista_gerente
from pulse_sas.internal.pulse_sas.guardia.views import vista_guardia
from pulse_sas.internal.pulse_sas.medico.views_dashboard import vista_medico
from pulse_sas.internal.pulse_sas.recepcionista.views import vista_recepcionista

from .forms import LoginConRolForm
from .permissions import _usuario_tiene_rol

# Despacho rol activo -> vista del dashboard de ese rol. Cada `vista_*`
# vuelve a validar el rol contra BD (`_usuario_tiene_rol`).
VISTA_POR_ROL = {
    'admin':            vista_admin,
    'gerente':          vista_gerente,
    'recepcionista':    vista_recepcionista,
    'medico':           vista_medico,
    'enfermera':        vista_enfermera,
    'guardia':          vista_guardia,
    'cliente_paciente': vista_cliente,
    'empresa':          vista_empresa,
}


class AccountsLogoutView(LogoutView):
    next_page = reverse_lazy('login')


def landing_view(request):
    """Página de bienvenida y portal informativo público de Pulse SAS."""
    return render(request, 'portal/landing.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginConRolForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            rol  = form.cleaned_data['rol']
            if not _usuario_tiene_rol(user, rol):
                form.add_error('rol', 'Tu usuario no tiene asignado ese rol.')
            else:
                login(request, user)
                # Guardar el rol elegido en sesión para usarlo en dashboard
                request.session['rol_activo'] = rol
                return redirect('dashboard')
    else:
        form = LoginConRolForm(request)

    return render(request, 'login/login.html', {'form': form})


@login_required
def dashboard(request):
    user = request.user

    # 1. Superusuario siempre es admin
    if user.is_superuser:
        return vista_admin(request)

    # 2. Rol guardado en sesión (login con selector de rol) — despacha a la
    #    vista_* correspondiente, que vuelve a validar el rol contra BD.
    rol_sesion = request.session.get('rol_activo')
    if rol_sesion in VISTA_POR_ROL:
        return VISTA_POR_ROL[rol_sesion](request)

    # 3. Rol guardado en DB (persona -> roles)
    try:
        categorias = user.persona.roles.values_list('categoria', flat=True)
        for cat in categorias:
            if cat in VISTA_POR_ROL:
                return VISTA_POR_ROL[cat](request)
    except Exception:
        pass

    # 4. Sin rol: mostrar selector
    return render(request, 'login/selector.html')
