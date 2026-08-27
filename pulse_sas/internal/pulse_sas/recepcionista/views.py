from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from pulse_sas.internal.pulse_sas.accounts.permissions import _usuario_tiene_rol
from pulse_sas.internal.pulse_sas.citas.models import Cita, CitaHistorial
from pulse_sas.internal.pulse_sas.personas.forms import ContactoEmergenciaForm
from pulse_sas.internal.pulse_sas.personas.models import (
    Jornada, Persona, Rol, SolicitudRegistroPaciente,
)

from .forms import PacienteRegistroForm


def _sugerir_medico(cita):
    """Para una `Cita` pendiente sin médico: arma la lista de médicos
    candidatos (con si está ocupado a esa hora exacta y si tiene Jornada
    cubriendo ese horario) y devuelve cuál conviene sugerir primero.

    'Ocupado' es el único bloqueo duro (no se puede doble-agendar un
    médico a la misma fecha_hora). 'En turno' (tiene Jornada) y
    'coincide especialidad' son señales para elegir el sugerido, no
    bloqueos -- si nadie tiene Jornada registrada esa hora, igual se
    sugiere alguien libre en vez de dejar a la recepcionista sin opción."""
    medicos = Persona.objects.filter(roles__categoria=Rol.Categoria.MEDICO).distinct().order_by('nombre', 'apellido')
    fecha_hora = cita.fecha_hora
    fecha_hora_local = timezone.localtime(fecha_hora) if timezone.is_aware(fecha_hora) else fecha_hora

    ocupados_ids = set(
        Cita.objects.filter(
            medico__in=medicos, fecha_hora=fecha_hora,
            estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA],
        ).values_list('medico_id', flat=True)
    )
    en_turno_ids = set(
        Jornada.objects.filter(
            persona__in=medicos, fecha=fecha_hora_local.date(),
            hora_inicio__lte=fecha_hora_local.time(), hora_fin__gte=fecha_hora_local.time(),
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


@login_required
def vista_recepcionista(request):
    """Recepcionista: atención al paciente -- registrar pacientes,
    asignar médico a citas pendientes, y bandeja de solicitudes de
    registro que llegan desde Médico (caso de urgencia)."""
    if not _usuario_tiene_rol(request.user, Rol.Categoria.RECEPCIONISTA):
        messages.error(request, 'No tienes permisos de recepcionista.')
        return redirect('dashboard')

    try:
        persona_recepcionista = request.user.persona
    except Exception:
        persona_recepcionista = None

    solicitud_id = request.GET.get('solicitud_id')
    solicitud_previa = None
    if solicitud_id:
        solicitud_previa = SolicitudRegistroPaciente.objects.filter(
            pk=solicitud_id, atendida=False
        ).first()
    paciente_form = PacienteRegistroForm(
        initial={
            'nombre': solicitud_previa.nombre,
            'apellido': solicitud_previa.apellido,
            'cedula': solicitud_previa.cedula,
        } if solicitud_previa else None
    )
    contacto_form = ContactoEmergenciaForm()

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'crear_paciente':
            paciente_form = PacienteRegistroForm(request.POST)
            contacto_form = ContactoEmergenciaForm(request.POST)
            if paciente_form.is_valid() and contacto_form.is_valid():
                persona = paciente_form.save(registrado_por=persona_recepcionista)
                contacto = contacto_form.save(commit=False)
                contacto.paciente = persona
                contacto.save()
                solicitud_atendida_id = request.POST.get('solicitud_id')
                if solicitud_atendida_id:
                    SolicitudRegistroPaciente.objects.filter(
                        pk=solicitud_atendida_id, atendida=False
                    ).update(
                        atendida=True, persona_creada=persona,
                        atendida_por=persona_recepcionista, fecha_atendida=timezone.now(),
                    )
                messages.success(request, 'Paciente registrado correctamente.')
                return redirect(reverse('dashboard_recepcionista') + '?seccion=pacientes')

        elif accion == 'asignar_medico':
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
                CitaHistorial.objects.create(
                    cita=cita, accion=CitaHistorial.Accion.ASIGNAR,
                    usuario_responsable=persona_recepcionista,
                    comentario=f'Asignado a {medico.nombre} {medico.apellido}',
                )
                messages.success(request, 'Cita asignada y confirmada correctamente.')
                return redirect(reverse('dashboard_recepcionista') + '?seccion=citas')

    pendientes = Cita.objects.filter(
        estado=Cita.Estado.PENDIENTE, medico__isnull=True
    ).select_related('persona').order_by('fecha_hora')
    citas_pendientes = []
    for c in pendientes:
        candidatos, sugerido = _sugerir_medico(c)
        citas_pendientes.append({'cita': c, 'candidatos': candidatos, 'sugerido': sugerido})

    solicitudes_registro = SolicitudRegistroPaciente.objects.filter(
        atendida=False
    ).select_related('solicitado_por').order_by('fecha_solicitud')

    solicitudes_atendidas = SolicitudRegistroPaciente.objects.filter(
        atendida=True
    ).select_related('solicitado_por', 'atendida_por').order_by('-fecha_atendida')[:50]

    pacientes = Persona.objects.filter(
        roles__categoria=Rol.Categoria.CLIENTE_PACIENTE
    ).select_related('registrado_por', 'registrado_por__usuario').distinct().order_by('-fecha_creacion')

    citas_asignadas = CitaHistorial.objects.filter(
        accion=CitaHistorial.Accion.ASIGNAR
    ).select_related('cita', 'cita__persona', 'cita__medico', 'usuario_responsable').order_by('-fecha_accion')[:50]

    ctx = {
        'paciente_form': paciente_form,
        'contacto_form': contacto_form,
        'pacientes': pacientes,
        'solicitud_previa': solicitud_previa,
        'solicitudes_registro': solicitudes_registro,
        'solicitudes_atendidas': solicitudes_atendidas,
        'citas_pendientes': citas_pendientes,
        'citas_asignadas': citas_asignadas,
        'seccion_activa': request.GET.get('seccion', 'resumen'),
    }
    return render(request, 'recepcionista/dashboard.html', ctx)
