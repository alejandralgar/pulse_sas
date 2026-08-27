from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from pulse_sas.internal.pulse_sas.accounts.permissions import _usuario_tiene_rol
from pulse_sas.internal.pulse_sas.citas.models import Cita
from pulse_sas.internal.pulse_sas.personas.models import HistoriaClinicaPersona, Persona, Rol

from .forms import SolicitudRegistroPacienteForm


@login_required
def vista_medico(request):
    if not _usuario_tiene_rol(request.user, Rol.Categoria.MEDICO):
        messages.error(request, 'No tienes permisos de médico.')
        return redirect('dashboard')

    try:
        persona_medico = request.user.persona
    except Exception:
        persona_medico = None

    solicitud_registro_form = SolicitudRegistroPacienteForm()

    if request.method == 'POST' and persona_medico:
        accion = request.POST.get('accion')

        if accion == 'solicitar_atencion_urgente':
            paciente = Persona.objects.filter(
                pk=request.POST.get('paciente_id'), roles__categoria=Rol.Categoria.CLIENTE_PACIENTE
            ).first()
            if not paciente:
                messages.error(request, 'Paciente no encontrado.')
            else:
                Cita.objects.create(
                    persona=paciente,
                    medico=None,
                    estado=Cita.Estado.PENDIENTE,
                    tipo_cita=Cita.TipoCita.URGENCIA,
                    fecha_hora=timezone.now(),
                    motivo=f'Urgencia solicitada por Dr(a). {persona_medico.nombre} {persona_medico.apellido}',
                )
                messages.success(
                    request,
                    f'Solicitud de atención urgente para {paciente.nombre} {paciente.apellido} '
                    'enviada -- queda pendiente de que Recepcionista asigne médico.'
                )
            return redirect(reverse('dashboard_medico') + '?tab=buscar')

        elif accion == 'solicitar_registro_paciente':
            solicitud_registro_form = SolicitudRegistroPacienteForm(request.POST)
            if solicitud_registro_form.is_valid():
                solicitud = solicitud_registro_form.save(commit=False)
                solicitud.solicitado_por = persona_medico
                solicitud.save()
                messages.success(request, 'Solicitud de registro enviada a Recepcionista.')
                return redirect(reverse('dashboard_medico') + '?tab=buscar')

    q_paciente = request.GET.get('q_paciente', '').strip()
    resultados_busqueda = []
    if q_paciente:
        resultados_busqueda = Persona.objects.filter(
            roles__categoria=Rol.Categoria.CLIENTE_PACIENTE
        ).filter(
            Q(nombre__icontains=q_paciente)
            | Q(apellido__icontains=q_paciente)
            | Q(cedula__icontains=q_paciente)
        ).distinct().order_by('nombre', 'apellido')

    agenda_hoy = []
    pacientes_atendidos = []
    if persona_medico:
        # Incluye citas de hoy en adelante -- una cita confirmada para una
        # fecha futura antes no aparecía en ningún lado del dashboard del
        # médico (ver 6_ERRORES_CONOCIDOS.md, entrada 2026-08-18).
        agenda_hoy = Cita.objects.filter(
            medico=persona_medico,
            fecha_hora__date__gte=timezone.localdate(),
            estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA, Cita.Estado.ATENDIDA],
        ).select_related('persona').order_by('fecha_hora')

        pacientes_atendidos = Persona.objects.filter(
            historiaclinicapersona__rol_en_historia=HistoriaClinicaPersona.RolEnHistoria.PACIENTE,
            historiaclinicapersona__historia_clinica__in=HistoriaClinicaPersona.objects.filter(
                persona=persona_medico,
                rol_en_historia=HistoriaClinicaPersona.RolEnHistoria.MEDICO_TRATANTE,
            ).values_list('historia_clinica_id', flat=True),
        ).distinct().order_by('nombre', 'apellido')

    ctx = {
        'agenda_hoy': agenda_hoy,
        'pacientes_atendidos': pacientes_atendidos,
        'q_paciente': q_paciente,
        'resultados_busqueda': resultados_busqueda,
        'solicitud_registro_form': solicitud_registro_form,
    }
    return render(request, 'medico/dashboard.html', ctx)
