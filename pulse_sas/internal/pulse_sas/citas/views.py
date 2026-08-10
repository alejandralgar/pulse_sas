import json
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from .forms import SolicitarCitaForm
from .models import Cita


from django.utils import timezone


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
