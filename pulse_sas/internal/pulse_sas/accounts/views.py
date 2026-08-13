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


def _tiene_rol_nombre(user, nombre_rol):
    """Distingue sub-roles dentro de una misma categoría (ej. Recepcionista
    vs. Gerente vs. Contadora, todos categoria=administrativo) por el
    `Rol.nombre` exacto asignado en BD."""
    if user.is_superuser:
        return True
    from pulse_sas.internal.pulse_sas.personas.models import Rol
    return Rol.objects.filter(nombre=nombre_rol, personas__usuario=user).exists()


def _sugerir_medico(cita):
    """Para una `Cita` pendiente sin médico: arma la lista de médicos
    candidatos (con si está ocupado a esa hora exacta y si tiene Jornada
    cubriendo ese horario) y devuelve cuál conviene sugerir primero.

    'Ocupado' es el único bloqueo duro (no se puede doble-agendar un
    médico a la misma fecha_hora). 'En turno' (tiene Jornada) y
    'coincide especialidad' son señales para elegir el sugerido, no
    bloqueos -- si nadie tiene Jornada registrada esa hora, igual se
    sugiere alguien libre en vez de dejar a la recepcionista sin opción."""
    from pulse_sas.internal.pulse_sas.citas.models import Cita
    from pulse_sas.internal.pulse_sas.personas.models import Jornada, Persona, Rol

    medicos = Persona.objects.filter(roles__categoria=Rol.Categoria.MEDICO).distinct().order_by('nombre', 'apellido')
    fecha_hora = cita.fecha_hora

    ocupados_ids = set(
        Cita.objects.filter(
            medico__in=medicos, fecha_hora=fecha_hora,
            estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA],
        ).values_list('medico_id', flat=True)
    )
    en_turno_ids = set(
        Jornada.objects.filter(
            persona__in=medicos, fecha=fecha_hora.date(),
            hora_inicio__lte=fecha_hora.time(), hora_fin__gte=fecha_hora.time(),
        ).values_list('persona_id', flat=True)
    )

    candidatos = []
    for medico in medicos:
        candidatos.append({
            'persona': medico,
            'ocupado': medico.id in ocupados_ids,
            'en_turno': medico.id in en_turno_ids,
            'coincide_especialidad': (
                cita.tipo_cita != Cita.TipoCita.ESPECIALISTA or bool(medico.especialidad)
            ),
        })

    disponibles = [c for c in candidatos if not c['ocupado']]
    sugerido = None
    for c in disponibles:
        if c['en_turno'] and c['coincide_especialidad']:
            sugerido = c['persona']
            break
    if sugerido is None:
        for c in disponibles:
            if c['coincide_especialidad']:
                sugerido = c['persona']
                break
    if sugerido is None and disponibles:
        sugerido = disponibles[0]['persona']

    return candidatos, sugerido


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
    from django.shortcuts import get_object_or_404

    from pulse_sas.internal.pulse_sas.citas.models import Cita
    from pulse_sas.internal.pulse_sas.personas.forms import ConvenioForm, EmpleadoRegistroForm
    from pulse_sas.internal.pulse_sas.personas.models import Convenio, Persona, Rol

    if not _usuario_tiene_rol(request.user, Rol.Categoria.ADMINISTRATIVO):
        messages.error(request, 'No tienes permisos de administrativo.')
        return redirect('dashboard')

    es_recepcionista = _tiene_rol_nombre(request.user, 'recepcionista')

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

        elif accion == 'asignar_medico' and es_recepcionista:
            cita = get_object_or_404(Cita, pk=request.POST.get('cita_id'), medico__isnull=True)
            medico = Persona.objects.filter(
                pk=request.POST.get('medico_id'), roles__categoria=Rol.Categoria.MEDICO
            ).first()
            if not medico:
                messages.error(request, 'Selecciona un médico válido.')
            elif Cita.objects.filter(
                medico=medico, fecha_hora=cita.fecha_hora,
                estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA],
            ).exists():
                messages.error(
                    request,
                    f'{medico.nombre} {medico.apellido} ya tiene otra cita a esa hora exacta. '
                    'Elige otro médico.'
                )
            else:
                cita.medico = medico
                cita.estado = Cita.Estado.CONFIRMADA
                cita.save(update_fields=['medico', 'estado'])
                messages.success(request, 'Cita asignada y confirmada correctamente.')
                return redirect(reverse('dashboard_administrativo') + '?seccion=citas')

    categorias_empleado = [Rol.Categoria.ADMINISTRATIVO, Rol.Categoria.MEDICO, Rol.Categoria.ENFERMERA]
    empleados = Persona.objects.filter(
        roles__categoria__in=categorias_empleado
    ).prefetch_related('roles').distinct().order_by('-fecha_creacion')

    citas_pendientes = []
    if es_recepcionista:
        pendientes = Cita.objects.filter(
            estado=Cita.Estado.PENDIENTE, medico__isnull=True
        ).select_related('persona').order_by('fecha_hora')
        for c in pendientes:
            candidatos, sugerido = _sugerir_medico(c)
            citas_pendientes.append({'cita': c, 'candidatos': candidatos, 'sugerido': sugerido})

    ctx = {
        'convenio_form': convenio_form,
        'convenios': Convenio.objects.all().order_by('nombre'),
        'empleado_form': empleado_form,
        'empleados': empleados,
        'es_recepcionista': es_recepcionista,
        'citas_pendientes': citas_pendientes,
        'seccion_activa': request.GET.get('seccion', 'resumen'),
    }
    return render(request, ROLE_TEMPLATE_MAP['administrativo'], ctx)

@login_required
def vista_medico(request):
    from django.utils import timezone

    from pulse_sas.internal.pulse_sas.citas.models import Cita
    from pulse_sas.internal.pulse_sas.personas.models import Rol

    if not _usuario_tiene_rol(request.user, Rol.Categoria.MEDICO):
        messages.error(request, 'No tienes permisos de médico.')
        return redirect('dashboard')

    try:
        persona_medico = request.user.persona
    except Exception:
        persona_medico = None

    agenda_hoy = []
    if persona_medico:
        agenda_hoy = Cita.objects.filter(
            medico=persona_medico,
            fecha_hora__date=timezone.localdate(),
            estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA],
        ).select_related('persona').order_by('fecha_hora')

    ctx = {'agenda_hoy': agenda_hoy}
    return render(request, ROLE_TEMPLATE_MAP['medico'], ctx)

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
