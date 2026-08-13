from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy

from .forms import LoginConRolForm

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


def _usuario_tiene_rol(user, categoria):
    """True si `user` es superuser o tiene `categoria` entre sus roles
    reales en BD (Persona.roles). Único punto de verdad para permisos por
    rol — no confiar en lo que el usuario eligió en un <select>."""
    if user.is_superuser:
        return True
    from pulse_sas.internal.pulse_sas.personas.models import Rol
    return Rol.objects.filter(categoria=categoria, personas__usuario=user).exists()


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


# ── Vistas directas por rol (acceso rápido) ──────────────────────────────────
@login_required
def vista_admin(request):
    from django.contrib.auth.forms import SetPasswordForm
    from django.db.models import Count
    from django.shortcuts import get_object_or_404
    from django.utils import timezone

    from pulse_sas.internal.pulse_sas.personas.forms import (
        AdminEditarUsuarioForm, AdminRegistroUsuarioForm, ConvenioForm, RolForm,
    )
    from pulse_sas.internal.pulse_sas.personas.models import Convenio, Jornada, Persona, Rol

    if not _usuario_tiene_rol(request.user, Rol.Categoria.ADMIN):
        messages.error(request, 'No tienes permisos de administrador.')
        return redirect('dashboard')

    rol_form = RolForm()
    usuario_form = AdminRegistroUsuarioForm()
    convenio_form = ConvenioForm()

    editar_id = request.GET.get('editar')
    persona_editar = get_object_or_404(Persona, pk=editar_id) if editar_id else None
    editar_form = AdminEditarUsuarioForm(instance=persona_editar) if persona_editar else None
    password_form = (
        SetPasswordForm(persona_editar.usuario)
        if persona_editar and persona_editar.usuario else None
    )

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'crear_rol':
            rol_form = RolForm(request.POST)
            if rol_form.is_valid():
                rol_form.save()
                messages.success(request, 'Rol creado correctamente.')
                return redirect(reverse('dashboard_admin') + '?seccion=roles')

        elif accion == 'crear_usuario':
            usuario_form = AdminRegistroUsuarioForm(request.POST)
            if usuario_form.is_valid():
                usuario_form.save()
                messages.success(request, 'Usuario registrado correctamente.')
                return redirect(reverse('dashboard_admin') + '?seccion=usuarios')

        elif accion == 'crear_convenio':
            convenio_form = ConvenioForm(request.POST)
            if convenio_form.is_valid():
                convenio_form.save()
                messages.success(request, 'Convenio registrado correctamente.')
                return redirect(reverse('dashboard_admin') + '?seccion=convenios')

        elif accion == 'editar_usuario':
            persona_editar = get_object_or_404(Persona, pk=request.POST.get('persona_id'))
            editar_form = AdminEditarUsuarioForm(request.POST, instance=persona_editar)
            if editar_form.is_valid():
                editar_form.save()
                messages.success(request, 'Usuario actualizado correctamente.')
                return redirect(reverse('dashboard_admin') + '?seccion=usuarios')

        elif accion == 'cambiar_password':
            persona_editar = get_object_or_404(Persona, pk=request.POST.get('persona_id'))
            if not persona_editar.usuario:
                messages.error(request, 'Este registro no tiene una cuenta de acceso asociada.')
            else:
                editar_form = AdminEditarUsuarioForm(instance=persona_editar)
                password_form = SetPasswordForm(persona_editar.usuario, request.POST)
                if password_form.is_valid():
                    password_form.save()
                    messages.success(request, 'Contraseña actualizada correctamente.')
                    return redirect(reverse('dashboard_admin') + '?seccion=usuarios')

        elif accion == 'eliminar_usuario':
            persona_eliminar = get_object_or_404(Persona, pk=request.POST.get('persona_id'))
            if persona_eliminar.usuario_id == request.user.id:
                messages.error(request, 'No puedes eliminar tu propio usuario.')
            else:
                nombre_completo = f'{persona_eliminar.nombre} {persona_eliminar.apellido}'
                if persona_eliminar.usuario:
                    persona_eliminar.usuario.is_active = False
                    persona_eliminar.usuario.save(update_fields=['is_active'])
                persona_eliminar.delete()
                messages.success(request, f'Usuario "{nombre_completo}" eliminado correctamente.')
            return redirect(reverse('dashboard_admin') + '?seccion=usuarios')

        elif accion == 'toggle_activo':
            persona_toggle = get_object_or_404(Persona, pk=request.POST.get('persona_id'))
            if persona_toggle.usuario_id == request.user.id:
                messages.error(request, 'No puedes desactivar tu propio usuario.')
            elif not persona_toggle.usuario:
                messages.error(request, 'Este registro no tiene una cuenta de acceso asociada.')
            else:
                persona_toggle.usuario.is_active = not persona_toggle.usuario.is_active
                persona_toggle.usuario.save(update_fields=['is_active'])
                estado = 'activado' if persona_toggle.usuario.is_active else 'desactivado'
                messages.success(request, f'Usuario "{persona_toggle.nombre} {persona_toggle.apellido}" {estado} correctamente.')
            return redirect(reverse('dashboard_admin') + '?seccion=usuarios')

    roles = Rol.objects.annotate(num_usuarios=Count('personas')).order_by('categoria', 'nombre')
    convenios = Convenio.objects.all().order_by('nombre')
    usuarios = Persona.objects.select_related('usuario').prefetch_related('roles').order_by('-fecha_creacion')

    ahora = timezone.localtime()
    personal_trabajando = Jornada.objects.filter(
        fecha=ahora.date(),
        hora_inicio__lte=ahora.time(),
        hora_fin__gte=ahora.time(),
        persona__roles__categoria__in=[
            Rol.Categoria.ADMINISTRATIVO,
            Rol.Categoria.MEDICO,
            Rol.Categoria.ENFERMERA,
            Rol.Categoria.GUARDIA,
        ],
    ).select_related('persona').distinct().order_by('hora_inicio')

    ctx = {
        'rol_form': rol_form,
        'usuario_form': usuario_form,
        'convenio_form': convenio_form,
        'persona_editar': persona_editar,
        'editar_form': editar_form,
        'password_form': password_form,
        'roles': roles,
        'convenios': convenios,
        'usuarios': usuarios,
        'personal_trabajando': personal_trabajando,
        'seccion_activa': request.GET.get('seccion', 'resumen'),
    }
    return render(request, ROLE_TEMPLATE_MAP['admin'], ctx)

@login_required
def vista_administrativo(request):
    from pulse_sas.internal.pulse_sas.personas.forms import ConvenioForm, EmpleadoRegistroForm
    from pulse_sas.internal.pulse_sas.personas.models import Convenio, Persona, Rol

    if not _usuario_tiene_rol(request.user, Rol.Categoria.ADMINISTRATIVO):
        messages.error(request, 'No tienes permisos de administrativo.')
        return redirect('dashboard')

    convenio_form = ConvenioForm()
    empleado_form = EmpleadoRegistroForm()

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'crear_convenio':
            convenio_form = ConvenioForm(request.POST)
            if convenio_form.is_valid():
                convenio_form.save()
                messages.success(request, 'Convenio registrado correctamente.')
                return redirect(reverse('dashboard_administrativo') + '?seccion=convenios')

        elif accion == 'crear_empleado':
            empleado_form = EmpleadoRegistroForm(request.POST)
            if empleado_form.is_valid():
                empleado_form.save()
                messages.success(request, 'Empleado registrado correctamente.')
                return redirect(reverse('dashboard_administrativo') + '?seccion=empleados')

    categorias_empleado = [Rol.Categoria.ADMINISTRATIVO, Rol.Categoria.MEDICO, Rol.Categoria.ENFERMERA]
    empleados = Persona.objects.filter(
        roles__categoria__in=categorias_empleado
    ).prefetch_related('roles').distinct().order_by('-fecha_creacion')

    ctx = {
        'convenio_form': convenio_form,
        'convenios': Convenio.objects.all().order_by('nombre'),
        'empleado_form': empleado_form,
        'empleados': empleados,
        'seccion_activa': request.GET.get('seccion', 'resumen'),
    }
    return render(request, ROLE_TEMPLATE_MAP['administrativo'], ctx)

@login_required
def vista_medico(request):
    from pulse_sas.internal.pulse_sas.personas.models import Rol
    if not _usuario_tiene_rol(request.user, Rol.Categoria.MEDICO):
        messages.error(request, 'No tienes permisos de médico.')
        return redirect('dashboard')
    return render(request, ROLE_TEMPLATE_MAP['medico'])

@login_required
def vista_enfermera(request):
    from pulse_sas.internal.pulse_sas.personas.models import Rol
    if not _usuario_tiene_rol(request.user, Rol.Categoria.ENFERMERA):
        messages.error(request, 'No tienes permisos de enfermera.')
        return redirect('dashboard')
    return render(request, ROLE_TEMPLATE_MAP['enfermera'])

@login_required
def vista_guardia(request):
    from pulse_sas.internal.pulse_sas.personas.models import Rol
    if not _usuario_tiene_rol(request.user, Rol.Categoria.GUARDIA):
        messages.error(request, 'No tienes permisos de guardia.')
        return redirect('dashboard')
    return render(request, ROLE_TEMPLATE_MAP['guardia'])

@login_required
def vista_cliente(request):
    from pulse_sas.internal.pulse_sas.personas.models import ContactoEmergencia, Rol
    from pulse_sas.internal.pulse_sas.personas.forms import PerfilEditableForm, ContactoEmergenciaForm
    from pulse_sas.internal.pulse_sas.citas.forms import SolicitarCitaForm
    from pulse_sas.internal.pulse_sas.citas.models import Cita

    if not _usuario_tiene_rol(request.user, Rol.Categoria.CLIENTE_PACIENTE):
        messages.error(request, 'No tienes permisos de paciente.')
        return redirect('dashboard')

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
    from pulse_sas.internal.pulse_sas.personas.models import Rol
    if not _usuario_tiene_rol(request.user, Rol.Categoria.EMPRESA):
        messages.error(request, 'No tienes permisos de empresa.')
        return redirect('dashboard')
    return render(request, ROLE_TEMPLATE_MAP['empresa'])


# Despacho rol -> vista. Definido al final: referencia funciones ya
# declaradas arriba, se resuelve recién cuando dashboard() lo usa.
VISTA_POR_ROL = {
    'admin':            vista_admin,
    'administrativo':   vista_administrativo,
    'medico':           vista_medico,
    'enfermera':        vista_enfermera,
    'guardia':          vista_guardia,
    'cliente_paciente': vista_cliente,
    'empresa':          vista_empresa,
}
