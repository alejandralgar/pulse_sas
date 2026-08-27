from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from pulse_sas.internal.pulse_sas.citas.models import Cita, CitaHistorial

from .forms import SolicitarCitaForm


@login_required
def solicitar_cita(request):
    try:
        persona = request.user.persona
    except Exception:
        messages.error(request, 'No se encontró tu perfil de paciente.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = SolicitarCitaForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            fecha_str = d['fecha'].strftime('%Y-%m-%d') if hasattr(d['fecha'], 'strftime') else str(d['fecha'])
            fecha_hora_naive = datetime.strptime(
                f"{fecha_str} {d['hora']}", '%Y-%m-%d %H:%M'
            )

            if timezone.is_aware(timezone.now()):
                fecha_hora = timezone.make_aware(fecha_hora_naive, timezone.get_current_timezone())
                ahora = timezone.localtime(timezone.now())
            else:
                fecha_hora = fecha_hora_naive
                ahora = datetime.now()

            # 1. Validar que la fecha/hora no sea del pasado ni una hora transcurrida del mismo día
            if fecha_hora < ahora:
                messages.error(request, 'No puedes agendar una cita para una fecha u hora pasadas.')
                return redirect('dashboard_cliente')

            # 2. Validar si otro paciente ya ocupó ese horario
            ocupada = Cita.objects.filter(
                fecha_hora=fecha_hora,
                estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA]
            ).exists()

            if ocupada:
                messages.error(
                    request,
                    'El horario seleccionado ya ha sido ocupado por otro paciente. '
                    'Por favor selecciona otro horario.'
                )
                return redirect('dashboard_cliente')

            Cita.objects.create(
                persona=persona,
                fecha_hora=fecha_hora,
                tipo_cita=d['tipo_cita'],
                motivo=d.get('motivo', '') or d['tipo_cita'],
                estado=Cita.Estado.PENDIENTE,
            )
            messages.success(
                request,
                'Tu cita ha sido registrada con estado PENDIENTE. '
                'Te confirmaremos pronto.'
            )
            return redirect('dashboard_cliente')
        else:
            messages.error(request, 'Por favor completa todos los campos requeridos.')

    return redirect('dashboard_cliente')


@login_required
@require_GET
def horarios_disponibles(request):
    """Devuelve los horarios ocupados para una fecha dada (JSON)."""
    fecha_str = request.GET.get('fecha', '')
    if not fecha_str:
        return JsonResponse({'ocupados': []})

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'ocupados': []})

    citas_del_dia = Cita.objects.filter(
        fecha_hora__date=fecha,
        estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA],
    ).values_list('fecha_hora', flat=True)

    ocupados = []
    for c in citas_del_dia:
        if timezone.is_aware(c):
            c_local = timezone.localtime(c)
        else:
            c_local = c
        ocupados.append(c_local.strftime('%H:%M'))

    return JsonResponse({'ocupados': ocupados})


@login_required
def modificar_cita(request, cita_id):
    """Permite al cliente modificar/reprogramar una cita pendiente o confirmada."""
    try:
        persona = request.user.persona
    except Exception:
        messages.error(request, 'No se encontró tu perfil de paciente.')
        return redirect('dashboard')

    cita = get_object_or_404(Cita, pk=cita_id, persona=persona)

    if cita.estado in [Cita.Estado.ATENDIDA, Cita.Estado.CANCELADA]:
        messages.error(request, 'No es posible modificar una cita que ya fue atendida o cancelada.')
        return redirect(reverse('dashboard_cliente') + '?seccion=miscitas')

    if request.method == 'POST':
        fecha_str = request.POST.get('fecha', '').strip()
        hora_str = request.POST.get('hora', '').strip()
        tipo_cita = request.POST.get('tipo_cita', '').strip()
        motivo = request.POST.get('motivo', '').strip()

        if not fecha_str or not hora_str:
            messages.error(request, 'Por favor especifica la nueva fecha y hora para la cita.')
            return redirect(reverse('dashboard_cliente') + '?seccion=miscitas')

        try:
            fecha_hora_naive = datetime.strptime(f"{fecha_str} {hora_str}", '%Y-%m-%d %H:%M')
        except ValueError:
            messages.error(request, 'Formato de fecha u hora no válido.')
            return redirect(reverse('dashboard_cliente') + '?seccion=miscitas')

        if timezone.is_aware(timezone.now()):
            fecha_hora = timezone.make_aware(fecha_hora_naive, timezone.get_current_timezone())
            ahora = timezone.localtime(timezone.now())
        else:
            fecha_hora = fecha_hora_naive
            ahora = datetime.now()

        if fecha_hora < ahora:
            messages.error(request, 'No puedes seleccionar una fecha u hora pasadas.')
            return redirect(reverse('dashboard_cliente') + '?seccion=miscitas')

        ocupada = Cita.objects.filter(
            fecha_hora=fecha_hora,
            estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA]
        ).exclude(pk=cita.pk).exists()

        if ocupada:
            messages.error(
                request,
                'El horario seleccionado ya ha sido ocupado por otro paciente. Por favor selecciona otro horario.'
            )
            return redirect(reverse('dashboard_cliente') + '?seccion=miscitas')

        cita.fecha_hora = fecha_hora
        if tipo_cita:
            cita.tipo_cita = tipo_cita
        if motivo:
            cita.motivo = motivo
        cita.estado = Cita.Estado.REPROGRAMADA
        cita.save()

        CitaHistorial.objects.create(
            cita=cita,
            accion=CitaHistorial.Accion.REPROGRAMAR,
            usuario_responsable=persona,
            comentario=f'Cita reprogramada por el cliente a {fecha_hora.strftime("%d/%m/%Y %H:%M")}',
        )

        messages.success(request, f'La cita #{cita.pk} ha sido reprogramada exitosamente.')

    return redirect(reverse('dashboard_cliente') + '?seccion=miscitas')


@login_required
def cancelar_cita(request, cita_id):
    """Permite al cliente cancelar una cita pendiente, confirmada o reprogramada."""
    try:
        persona = request.user.persona
    except Exception:
        messages.error(request, 'No se encontró tu perfil de paciente.')
        return redirect('dashboard')

    cita = get_object_or_404(Cita, pk=cita_id, persona=persona)

    if cita.estado == Cita.Estado.CANCELADA:
        messages.warning(request, 'La cita ya se encuentra cancelada.')
        return redirect(reverse('dashboard_cliente') + '?seccion=miscitas')

    if cita.estado == Cita.Estado.ATENDIDA:
        messages.error(request, 'No se puede cancelar una cita que ya ha sido atendida.')
        return redirect(reverse('dashboard_cliente') + '?seccion=miscitas')

    cita.estado = Cita.Estado.CANCELADA
    cita.save(update_fields=['estado'])

    CitaHistorial.objects.create(
        cita=cita,
        accion=CitaHistorial.Accion.CANCELAR,
        usuario_responsable=persona,
        comentario='Cita cancelada a solicitud del cliente desde la oficina virtual',
    )

    messages.success(request, f'La cita #{cita.pk} ha sido cancelada exitosamente.')
    return redirect(reverse('dashboard_cliente') + '?seccion=miscitas')
