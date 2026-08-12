from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .forms import ContactoEmergenciaForm, PerfilEditableForm
from .models import ContactoEmergencia


def _errores_form(form):
    partes = []
    for campo, errores in form.errors.items():
        etiqueta = form.fields[campo].label if campo in form.fields else None
        for error in errores:
            partes.append(f'{etiqueta}: {error}' if etiqueta else error)
    return ' '.join(partes)


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
        else:
            messages.error(request, f'No se pudo actualizar tu perfil: {_errores_form(form)}')

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
        else:
            messages.error(request, f'No se pudo guardar la persona de contacto: {_errores_form(form)}')

    return redirect('dashboard_cliente')
