from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import LoginConRolForm, RegistroForm

# Mapa categoria -> template
ROLE_TEMPLATE_MAP = {
    'admin':            'admin_rol/dashboard.html',
    'administrativo':   'administrativo/dasboard.html',
    'medico':           'medico/dashboard.html',
    'enfermera':        'enfermera/dashboard.html',
    'guardia':          'guardia/dashboard.html',
    'cliente_paciente': 'cliente/dasboard.html',
    'empresa':          'empresa/convenios/dashboard.html',
}


class AccountsLogoutView(LogoutView):
    next_page = reverse_lazy('login')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginConRolForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            rol  = form.cleaned_data['rol']
            login(request, user)
            # Guardar el rol elegido en sesión para usarlo en dashboard
            request.session['rol_activo'] = rol
            return redirect('dashboard')
    else:
        form = LoginConRolForm(request)

    return render(request, 'login/login.html', {'form': form})


def registro(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Crear/asociar Persona con el rol en DB
            _crear_persona_con_rol(user, form.cleaned_data)

            # No hacer auto-login: redirigir al login para que el usuario entre con su rol
            return redirect('login')
    else:
        form = RegistroForm()

    return render(request, 'login/registro.html', {'form': form})


def _crear_persona_con_rol(user, datos):
    """Crea el perfil Persona y asigna el rol al usuario recién registrado."""
    try:
        from pulse_sas.internal.pulse_sas.personas.models import Persona, Rol, RolPersona

        persona, _ = Persona.objects.get_or_create(
            usuario=user,
            defaults={
                'nombre':   datos.get('nombre', user.first_name),
                'apellido': datos.get('apellido', user.last_name),
                'cedula':   datos.get('cedula', ''),
                'correo':   datos.get('email', user.email),
                'edad':     0,
            }
        )

        categoria = datos.get('rol', '')
        if categoria:
            # Buscar o crear un Rol con esa categoría
            rol_obj, _ = Rol.objects.get_or_create(
                categoria=categoria,
                defaults={'nombre': dict([
                    ('admin', 'Administrador'),
                    ('administrativo', 'Administrativo'),
                    ('medico', 'Médico'),
                    ('enfermera', 'Enfermera'),
                    ('guardia', 'Guardia de Seguridad'),
                    ('cliente_paciente', 'Paciente'),
                    ('empresa', 'Empresa / EPS'),
                ]).get(categoria, categoria)}
            )
            RolPersona.objects.get_or_create(persona=persona, rol=rol_obj)
    except Exception:
        pass  # No bloquear el registro si falla la asignación de rol


@login_required
def dashboard(request):
    user = request.user

    # 1. Superusuario siempre es admin
    if user.is_superuser:
        return render(request, ROLE_TEMPLATE_MAP['admin'])

    # 2. Rol guardado en sesión (login con selector de rol)
    rol_sesion = request.session.get('rol_activo')
    if rol_sesion and rol_sesion in ROLE_TEMPLATE_MAP:
        if rol_sesion == 'cliente_paciente':
            return vista_cliente(request)
        return render(request, ROLE_TEMPLATE_MAP[rol_sesion])

    # 3. Rol guardado en DB (persona -> roles)
    try:
        categorias = user.persona.roles.values_list('categoria', flat=True)
        for cat in categorias:
            if cat in ROLE_TEMPLATE_MAP:
                if cat == 'cliente_paciente':
                    return vista_cliente(request)
                return render(request, ROLE_TEMPLATE_MAP[cat])
    except Exception:
        pass

    # 4. Sin rol: mostrar selector
    return render(request, 'login/selector.html')


# ── Vistas directas por rol (acceso rápido) ──────────────────────────────────
@login_required
def vista_admin(request):
    return render(request, ROLE_TEMPLATE_MAP['admin'])

@login_required
def vista_administrativo(request):
    return render(request, ROLE_TEMPLATE_MAP['administrativo'])

@login_required
def vista_medico(request):
    return render(request, ROLE_TEMPLATE_MAP['medico'])

@login_required
def vista_enfermera(request):
    return render(request, ROLE_TEMPLATE_MAP['enfermera'])

@login_required
def vista_guardia(request):
    return render(request, ROLE_TEMPLATE_MAP['guardia'])

@login_required
def vista_cliente(request):
    from pulse_sas.internal.pulse_sas.personas.models import ContactoEmergencia
    from pulse_sas.internal.pulse_sas.personas.forms import PerfilEditableForm, ContactoEmergenciaForm
    from pulse_sas.internal.pulse_sas.citas.forms import SolicitarCitaForm
    from pulse_sas.internal.pulse_sas.citas.models import Cita

    try:
        persona = request.user.persona
    except Exception:
        persona = None

    contacto_emergencia = None
    citas = []
    if persona:
        contacto_emergencia = ContactoEmergencia.objects.filter(paciente=persona).first()
        citas = Cita.objects.filter(persona=persona).order_by('-fecha_hora')[:20]

    perfil_form = PerfilEditableForm(instance=persona) if persona else PerfilEditableForm()
    contacto_form = ContactoEmergenciaForm(instance=contacto_emergencia)
    cita_form = SolicitarCitaForm()

    # Citas para el calendario (JSON)
    import json
    citas_calendario = [
        {
            'fecha': str(c.fecha_hora.date()),
            'hora': c.fecha_hora.strftime('%H:%M'),
            'tipo': c.get_tipo_cita_display() if c.tipo_cita else c.motivo,
            'estado': c.estado,
        }
        for c in citas
    ]

    ctx = {
        'persona': persona,
        'perfil_form': perfil_form,
        'contacto_form': contacto_form,
        'cita_form': cita_form,
        'citas': citas,
        'citas_calendario_json': json.dumps(citas_calendario),
        'contacto_emergencia': contacto_emergencia,
        'seccion_activa': request.GET.get('seccion', 'perfil'),
    }
    return render(request, ROLE_TEMPLATE_MAP['cliente_paciente'], ctx)

@login_required
def vista_empresa(request):
    return render(request, ROLE_TEMPLATE_MAP['empresa'])
