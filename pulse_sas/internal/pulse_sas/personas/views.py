from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render

from .forms import ContactoEmergenciaForm, MiPerfilForm
from .models import ContactoEmergencia


@login_required
def mi_perfil(request):
    """Página 'Mi Perfil', accesible desde el menú del usuario en el
    topbar -- igual para cualquier rol. Cada quien edita solo su propia
    Persona; el rol/cargo no se toca acá (lo asigna Admin)."""
    try:
        persona = request.user.persona
    except Exception:
        persona = None

    if persona is None:
        messages.error(request, 'No se encontró tu perfil.')
        return redirect('dashboard')

    perfil_form = MiPerfilForm(instance=persona)
    password_form = PasswordChangeForm(request.user)
    contacto_emergencia = ContactoEmergencia.objects.filter(paciente=persona).first()
    contacto_form = ContactoEmergenciaForm(instance=contacto_emergencia)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'actualizar_perfil':
            perfil_form = MiPerfilForm(request.POST, instance=persona)
            if perfil_form.is_valid():
                perfil_form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
                return redirect('mi_perfil')

        elif accion == 'cambiar_password':
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, password_form.user)
                messages.success(request, 'Contraseña actualizada correctamente.')
                return redirect('mi_perfil')

        elif accion == 'guardar_contacto':
            contacto_form = ContactoEmergenciaForm(request.POST, instance=contacto_emergencia)
            if contacto_form.is_valid():
                contacto = contacto_form.save(commit=False)
                contacto.paciente = persona
                contacto.save()
                messages.success(request, 'Persona de contacto guardada correctamente.')
                return redirect('mi_perfil')

    ctx = {
        'perfil_form': perfil_form,
        'password_form': password_form,
        'persona': persona,
        'contacto_form': contacto_form,
        'contacto_emergencia': contacto_emergencia,
    }
    return render(request, 'cuenta/mi_perfil.html', ctx)
