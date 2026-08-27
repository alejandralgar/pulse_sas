from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from pulse_sas.internal.pulse_sas.accounts.permissions import _usuario_tiene_rol
from pulse_sas.internal.pulse_sas.personas.forms import ConvenioForm
from pulse_sas.internal.pulse_sas.personas.models import Convenio, Jornada, Persona, Rol

from .forms import AdminEditarUsuarioForm, AdminRegistroUsuarioForm, RolForm


@login_required
def vista_admin(request):
    if not _usuario_tiene_rol(request.user, Rol.Categoria.ADMIN):
        messages.error(request, 'No tienes permisos de administrador.')
        return redirect('dashboard')

    try:
        persona_admin = request.user.persona
    except Exception:
        persona_admin = None

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
                usuario_form.save(registrado_por=persona_admin)
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
            Rol.Categoria.GERENTE,
            Rol.Categoria.RECEPCIONISTA,
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
    return render(request, 'admin_rol/dashboard.html', ctx)
