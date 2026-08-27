import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from pulse_sas.internal.pulse_sas.accounts.permissions import _usuario_tiene_rol
from pulse_sas.internal.pulse_sas.citas.models import Cita
from pulse_sas.internal.pulse_sas.personas.models import (
    Convenio, HistoriaClinica, HistoriaClinicaPersona, PlanManejo, Receta, Rol,
)

from .forms import SolicitarCitaForm


@login_required
def vista_cliente(request):
    if not _usuario_tiene_rol(request.user, Rol.Categoria.CLIENTE_PACIENTE):
        messages.error(request, 'No tienes permisos de paciente.')
        return redirect('dashboard')

    try:
        persona = request.user.persona
    except Exception:
        persona = None

    citas = []
    historias_clinicas = []
    recetas = []
    droguerias_convenio = []
    proxima_cita_recomendada = None

    if persona:
        citas = Cita.objects.filter(persona=persona).order_by('-fecha_hora')[:20]

        # 1. Obtener IDs de historias clínicas como paciente
        historias_ids = list(HistoriaClinicaPersona.objects.filter(
            persona=persona, rol_en_historia=HistoriaClinicaPersona.RolEnHistoria.PACIENTE,
        ).values_list('historia_clinica_id', flat=True))

        if historias_ids:
            # Cargar historias clínicas del paciente
            historias_qs = HistoriaClinica.objects.filter(
                id__in=historias_ids
            ).select_related(
                'motivo_consulta', 'enfermedad_actual', 'antecedente',
                'examen_fisico', 'diagnostico', 'plan_de_manejo'
            ).order_by('-fecha_ingreso_paciente')
            historias_clinicas = list(historias_qs)

            # Cargar médico tratante por cada historia clínica
            rel_medicos = HistoriaClinicaPersona.objects.filter(
                historia_clinica_id__in=historias_ids,
                rol_en_historia=HistoriaClinicaPersona.RolEnHistoria.MEDICO_TRATANTE,
            ).select_related('persona')
            medico_map = {rel.historia_clinica_id: rel.persona for rel in rel_medicos}

            for h in historias_clinicas:
                h.medico_tratante = medico_map.get(h.id)

            # Cargar Recetas médicas del paciente
            recetas_qs = Receta.objects.filter(
                historia_clinica_id__in=historias_ids
            ).select_related(
                'historia_clinica'
            ).prefetch_related(
                'medicamentos'
            ).order_by('-fecha_emision')
            recetas = list(recetas_qs)

            for r in recetas:
                r.medico_tratante = medico_map.get(r.historia_clinica_id)

        # 2. Droguerías / Convenios
        droguerias_convenio = list(Convenio.objects.all())
        if not droguerias_convenio:
            droguerias_convenio = [
                {'nombre': 'Droguería Cruz Verde (Convenio IPS)', 'nit': '800.149.695-1', 'telefono': '601 486 5000 / Linea Nal. 018000 910545', 'especialidad': 'Dispensación de Medicamentos y Fórmulas Médicas'},
                {'nombre': 'Audifarma S.A. (Farmacia Aliada)', 'nit': '816.002.019-2', 'telefono': '601 594 8888', 'especialidad': 'Medicamentos POS y Especializados'},
                {'nombre': 'Farmatodo Colombia', 'nit': '900.204.385-4', 'telefono': '601 746 9000', 'especialidad': 'Farmacia General y Cuidado Personal'},
                {'nombre': 'Droguerías La Rebaja / Copservir', 'nit': '890.319.193-0', 'telefono': '01 8000 939 900', 'especialidad': 'Atención 24 Horas y Domicilios'},
            ]

        # Aviso de "debés agendar" -- el médico dejó una fecha sugerida en PlanManejo
        plan_pendiente = PlanManejo.objects.filter(
            historia_clinica_id__in=historias_ids,
            fecha_proxima_cita__gte=timezone.localdate(),
        ).order_by('fecha_proxima_cita').first()
        if plan_pendiente:
            ya_agendada = Cita.objects.filter(
                persona=persona,
                fecha_hora__date=plan_pendiente.fecha_proxima_cita,
                estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA],
            ).exists()
            if not ya_agendada:
                proxima_cita_recomendada = plan_pendiente.fecha_proxima_cita

    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'enviar_correo_contacto':
            asunto = request.POST.get('asunto', '').strip()
            mensaje = request.POST.get('mensaje', '').strip()
            if not asunto or not mensaje:
                messages.error(request, 'Por favor ingresa tanto el asunto como el mensaje.')
            else:
                from django.core.mail import send_mail
                from django.conf import settings

                remitente_nombre = f"{persona.nombre} {persona.apellido}" if persona else request.user.get_full_name() or request.user.username
                remitente_email = request.user.email or "No especificado"

                cuerpo = (
                    f"Mensaje de contacto recibido desde el Panel del Cliente:\n\n"
                    f"De: {remitente_nombre}\n"
                    f"Usuario: {request.user.username}\n"
                    f"Correo de contacto: {remitente_email}\n\n"
                    f"--------------------------------------------------\n"
                    f"Asunto: {asunto}\n\n"
                    f"Mensaje:\n{mensaje}\n"
                    f"--------------------------------------------------\n"
                )
                try:
                    send_mail(
                        subject=f"[Contacto Sistema] {asunto}",
                        message=cuerpo,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=['soporte@pulsesas.com', 'admin@pulsesas.com'],
                        fail_silently=True,
                    )
                except Exception:
                    pass
                messages.success(request, '¡Tu mensaje ha sido enviado exitosamente al equipo del sistema (nosotras)! Nos poneremos en contacto contigo pronto.')
            return redirect(reverse('dashboard_cliente') + '?seccion=contactanos')

    cita_form = SolicitarCitaForm()

    # Citas para el calendario (JSON)
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
        'cita_form': cita_form,
        'citas': citas,
        'historias_clinicas': historias_clinicas,
        'recetas': recetas,
        'droguerias_convenio': droguerias_convenio,
        'citas_calendario_json': json.dumps(citas_calendario),
        'proxima_cita_recomendada': proxima_cita_recomendada,
        'seccion_activa': request.GET.get('seccion', 'cita'),
    }
    return render(request, 'cliente/dasboard.html', ctx)
