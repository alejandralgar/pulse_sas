from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ContactoEmergenciaForm, PerfilEditableForm
from .models import ContactoEmergencia


@login_required
def actualizar_perfil(request):
    try:
        persona = request.user.persona
    except Exception:
        messages.error(request, 'No se encontró tu perfil de paciente.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = PerfilEditableForm(request.POST, instance=persona)
        if form.is_valid():
            form.save()
            # Sincronizar email con el User de Django
            request.user.email = form.cleaned_data['correo']
            request.user.save(update_fields=['email'])
            messages.success(request, 'Datos personales actualizados correctamente.')
            return redirect('dashboard_cliente')
    else:
        form = PerfilEditableForm(instance=persona)

    return redirect('dashboard_cliente')


@login_required
def guardar_contacto_emergencia(request):
    try:
        persona = request.user.persona
    except Exception:
        messages.error(request, 'No se encontró tu perfil de paciente.')
        return redirect('dashboard')

    contacto_existente = ContactoEmergencia.objects.filter(paciente=persona).first()

    if request.method == 'POST':
        form = ContactoEmergenciaForm(request.POST, instance=contacto_existente)
        if form.is_valid():
            contacto = form.save(commit=False)
            contacto.paciente = persona
            contacto.save()
            messages.success(request, 'Persona de contacto guardada correctamente.')
            return redirect('dashboard_cliente')

    return redirect('dashboard_cliente')
