from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from pulse_sas.internal.pulse_sas.citas.models import Cita

from .forms import (
    ConsultaForm, ContactoEmergenciaForm, ItemRecetaFormSet, MiPerfilForm,
    RecetaForm,
)
from .models import (
    ContactoEmergencia, HistoriaClinica, HistoriaClinicaPersona, Persona, Receta, Rol,
)


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


# ── Historia clínica / receta ("epicrisis") ──────────────────────────────────
# Regla: el médico solo edita historia clínica y receta el MISMO día de la
# consulta (ni antes ni después). El único que puede editar fuera de esa
# ventana es el rol Administrativo "gerente" (por Rol.nombre, no alcanza con
# la categoría -- ver 8_FALTO_RESOLVER.md).

def _es_gerente(user):
    if user.is_superuser:
        return True
    return Rol.objects.filter(nombre='gerente', personas__usuario=user).exists()


def _persona_con_rol_en_historia(historia, rol):
    rel = historia.historiaclinicapersona_set.filter(rol_en_historia=rol).select_related('persona').first()
    return rel.persona if rel else None


def _paciente_de(historia):
    return _persona_con_rol_en_historia(historia, HistoriaClinicaPersona.RolEnHistoria.PACIENTE)


def _medico_tratante_de(historia):
    return _persona_con_rol_en_historia(historia, HistoriaClinicaPersona.RolEnHistoria.MEDICO_TRATANTE)


def _medico_atendio_a(medico_persona, paciente_persona):
    """True si `medico_persona` fue el médico tratante de `paciente_persona`
    en alguna HistoriaClinica -- no importa cuál, define si puede ver TODO
    el historial de ese paciente (pedido explícito de la usuaria)."""
    return HistoriaClinica.objects.filter(
        historiaclinicapersona__persona=medico_persona,
        historiaclinicapersona__rol_en_historia=HistoriaClinicaPersona.RolEnHistoria.MEDICO_TRATANTE,
    ).filter(
        historiaclinicapersona__persona=paciente_persona,
        historiaclinicapersona__rol_en_historia=HistoriaClinicaPersona.RolEnHistoria.PACIENTE,
    ).exists()


def _puede_editar_historia(user, historia, medico_tratante):
    if _es_gerente(user):
        return True
    return (
        medico_tratante is not None
        and medico_tratante.usuario_id == user.id
        and timezone.localtime(historia.fecha_ingreso_paciente).date() == timezone.localdate()
    )


@login_required
def atender_cita(request, cita_id):
    if not (request.user.is_superuser or Rol.objects.filter(categoria=Rol.Categoria.MEDICO, personas__usuario=request.user).exists()):
        messages.error(request, 'No tienes permisos de médico.')
        return redirect('dashboard')

    try:
        medico = request.user.persona
    except Exception:
        medico = None
    if medico is None:
        messages.error(request, 'No se encontró tu perfil de médico.')
        return redirect('dashboard')

    cita = get_object_or_404(Cita, pk=cita_id, medico=medico)
    if timezone.localtime(cita.fecha_hora).date() != timezone.localdate():
        messages.error(request, 'Solo podés atender citas del día de hoy.')
        return redirect('dashboard_medico')
    if cita.estado != Cita.Estado.CONFIRMADA:
        messages.error(request, 'Esta cita ya fue atendida, o no está confirmada.')
        return redirect('dashboard_medico')

    if request.method == 'POST':
        form = ConsultaForm(request.POST)
        if form.is_valid():
            historia = form.guardar_nueva(cita=cita, medico=medico)
            messages.success(request, 'Consulta registrada correctamente.')
            return redirect('historia_detalle', historia_id=historia.id)
    else:
        form = ConsultaForm()

    ctx = {'form': form, 'cita': cita, 'es_edicion': False}
    return render(request, 'medico/atender_cita.html', ctx)


@login_required
def historia_paciente(request, persona_id):
    paciente = get_object_or_404(Persona, pk=persona_id)
    es_gerente = _es_gerente(request.user)

    if not es_gerente:
        try:
            medico = request.user.persona
        except Exception:
            medico = None
        if medico is None or not _medico_atendio_a(medico, paciente):
            messages.error(request, 'No tienes acceso a la historia clínica de este paciente.')
            return redirect('dashboard')

    historias = HistoriaClinica.objects.filter(
        historiaclinicapersona__persona=paciente,
        historiaclinicapersona__rol_en_historia=HistoriaClinicaPersona.RolEnHistoria.PACIENTE,
    ).distinct().order_by('-fecha_ingreso_paciente')

    ctx = {'paciente': paciente, 'historias': historias}
    return render(request, 'medico/historia_paciente.html', ctx)


@login_required
def historia_detalle(request, historia_id):
    historia = get_object_or_404(HistoriaClinica, pk=historia_id)
    paciente = _paciente_de(historia)
    medico_tratante = _medico_tratante_de(historia)
    es_gerente = _es_gerente(request.user)

    if not es_gerente:
        try:
            medico = request.user.persona
        except Exception:
            medico = None
        if medico is None or paciente is None or not _medico_atendio_a(medico, paciente):
            messages.error(request, 'No tienes acceso a esta historia clínica.')
            return redirect('dashboard')

    ctx = {
        'historia': historia,
        'paciente': paciente,
        'medico_tratante': medico_tratante,
        'puede_editar': _puede_editar_historia(request.user, historia, medico_tratante),
        'tiene_receta': hasattr(historia, 'receta'),
    }
    return render(request, 'medico/historia_detalle.html', ctx)


@login_required
def editar_historia(request, historia_id):
    historia = get_object_or_404(HistoriaClinica, pk=historia_id)
    medico_tratante = _medico_tratante_de(historia)

    if not _puede_editar_historia(request.user, historia, medico_tratante):
        messages.error(
            request,
            'Esta historia clínica ya no se puede editar (solo el mismo día '
            'de la consulta, o rol Gerente).'
        )
        return redirect('historia_detalle', historia_id=historia.id)

    if request.method == 'POST':
        form = ConsultaForm(request.POST, historia=historia)
        if form.is_valid():
            form.guardar_edicion(historia=historia)
            messages.success(request, 'Historia clínica actualizada correctamente.')
            return redirect('historia_detalle', historia_id=historia.id)
    else:
        form = ConsultaForm(historia=historia)

    ctx = {'form': form, 'historia': historia, 'paciente': _paciente_de(historia), 'es_edicion': True}
    return render(request, 'medico/atender_cita.html', ctx)


@login_required
def receta_view(request, historia_id):
    historia = get_object_or_404(HistoriaClinica, pk=historia_id)
    paciente = _paciente_de(historia)
    medico_tratante = _medico_tratante_de(historia)
    es_gerente = _es_gerente(request.user)

    if not es_gerente:
        try:
            medico = request.user.persona
        except Exception:
            medico = None
        if medico is None or paciente is None or not _medico_atendio_a(medico, paciente):
            messages.error(request, 'No tienes acceso a esta receta.')
            return redirect('dashboard')

    puede_editar = _puede_editar_historia(request.user, historia, medico_tratante)
    receta = Receta.objects.filter(historia_clinica=historia).first()
    receta_form = None
    formset = None

    if puede_editar:
        if request.method == 'POST':
            if receta is None:
                receta = Receta.objects.create(historia_clinica=historia)
            receta_form = RecetaForm(request.POST, instance=receta)
            formset = ItemRecetaFormSet(request.POST, instance=receta)
            if receta_form.is_valid() and formset.is_valid():
                receta_form.save()
                formset.save()
                messages.success(request, 'Receta guardada correctamente.')
                return redirect('ver_receta', historia_id=historia.id)
        else:
            instancia = receta or Receta(historia_clinica=historia)
            receta_form = RecetaForm(instance=instancia)
            formset = ItemRecetaFormSet(instance=instancia)

    ctx = {
        'historia': historia,
        'paciente': paciente,
        'receta': receta,
        'receta_form': receta_form,
        'formset': formset,
        'puede_editar': puede_editar,
    }
    return render(request, 'medico/receta.html', ctx)
