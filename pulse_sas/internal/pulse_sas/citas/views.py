import json
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from .forms import SolicitarCitaForm
from .models import Cita


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
            fecha_hora = datetime.strptime(
                f"{d['fecha']} {d['hora']}", '%Y-%m-%d %H:%M'
            )
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

    ocupados = [c.strftime('%H:%M') for c in citas_del_dia]
    return JsonResponse({'ocupados': ocupados})
