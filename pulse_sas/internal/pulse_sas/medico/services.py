import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _crear_cita_control_automatica(*, paciente, medico, fecha_proxima_cita, hora_referencia):
    """Auto-crea la cita de control ya CONFIRMADA con el mismo médico
    tratante -- decisión de la usuaria 2026-08-18 (ver 8_FALTO_RESOLVER.md,
    opción 3). Usa la misma hora del día que la cita original (
    `hora_referencia`) como horario por defecto.

    Si esa fecha/hora ya está ocupada (el médico tiene otra cita, o el
    paciente ya tiene una cita ese día) NO crea nada -- se deja el aviso
    del dashboard (`cliente/views_dashboard.py::vista_cliente`) como
    respaldo para que alguien la agende a mano en otro horario."""
    from pulse_sas.internal.pulse_sas.citas.models import Cita

    nueva_fecha_hora = hora_referencia.replace(
        year=fecha_proxima_cita.year, month=fecha_proxima_cita.month, day=fecha_proxima_cita.day,
    )

    medico_ocupado = Cita.objects.filter(
        medico=medico, fecha_hora=nueva_fecha_hora,
        estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA],
    ).exists()
    paciente_ocupado = Cita.objects.filter(
        persona=paciente, fecha_hora__date=fecha_proxima_cita,
        estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA],
    ).exists()
    if medico_ocupado or paciente_ocupado:
        return None

    return Cita.objects.create(
        persona=paciente,
        medico=medico,
        fecha_hora=nueva_fecha_hora,
        estado=Cita.Estado.CONFIRMADA,
        tipo_cita=Cita.TipoCita.CONTROL,
        motivo='Control indicado por el médico en la consulta anterior',
    )


def _validar_fecha_proxima_cita(*, medico, paciente, fecha, hora_referencia):
    """Valida la fecha de control ANTES de guardar la consulta.

    Devuelve `(bloqueante, motivo)`. `bloqueante=True` -> choque real de
    agenda (fecha pasada, médico u paciente ya ocupados esa fecha/hora):
    esto SÍ impide guardar el formulario, se raisea ValidationError en
    `ConsultaForm.clean_fecha_proxima_cita`. `bloqueante=False` con
    `motivo` no-`None` -> solo aviso (hoy: falta de `Jornada` registrada
    ese día/hora) -- la consulta se guarda igual, el médico solo recibe un
    mensaje informativo. No bloquear por Jornada vacía porque la tabla
    `Jornada` hoy está prácticamente sin poblar en producción: tratarlo
    como bloqueante rompía el guardado de CUALQUIER consulta con fecha de
    control, no solo las realmente conflictivas (bug real encontrado
    2026-08-19, ver 8_FALTO_RESOLVER.md).

    Reusado por `ConsultaForm.clean_fecha_proxima_cita` y por el endpoint
    AJAX `disponibilidad_proxima_cita` (aviso en el momento)."""
    from django.utils import timezone as tz

    from pulse_sas.internal.pulse_sas.citas.models import Cita
    from pulse_sas.internal.pulse_sas.personas.models import Jornada

    hoy = tz.localdate()
    if fecha < hoy:
        return True, 'La fecha de próxima cita no puede ser anterior a hoy.'

    hora_referencia_local = tz.localtime(hora_referencia) if tz.is_aware(hora_referencia) else hora_referencia
    nueva_fecha_hora = hora_referencia_local.replace(year=fecha.year, month=fecha.month, day=fecha.day)
    hora = nueva_fecha_hora.time()

    medico_ocupado = Cita.objects.filter(
        medico=medico, fecha_hora=nueva_fecha_hora,
        estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA],
    ).exists()
    if medico_ocupado:
        return True, f'Ya tenés otra cita agendada el {fecha:%d/%m/%Y} a las {hora:%H:%M}.'

    paciente_ocupado = Cita.objects.filter(
        persona=paciente, fecha_hora__date=fecha,
        estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA],
    ).exists()
    if paciente_ocupado:
        return True, f'El paciente ya tiene otra cita agendada el {fecha:%d/%m/%Y}.'

    tiene_jornada = Jornada.objects.filter(
        persona=medico, fecha=fecha, hora_inicio__lte=hora, hora_fin__gte=hora,
    ).exists()
    if not tiene_jornada:
        return False, (
            f'Aviso: no tenés jornada registrada el {fecha:%d/%m/%Y} a las '
            f'{hora:%H:%M} -- la consulta se guardó igual.'
        )

    return False, None


def _enviar_recordatorio_proxima_cita(paciente, fecha_proxima_cita, *, cita_ya_confirmada):
    """Best-effort: si falla el correo (SMTP caído, etc.) no debe tumbar
    el guardado de la consulta, que ya quedó en la base de datos."""
    if not paciente.correo:
        return
    if cita_ya_confirmada:
        cuerpo = (
            f'Hola {paciente.nombre},\n\n'
            f'Tu médico indicó que debes volver a consulta el '
            f'{fecha_proxima_cita:%d/%m/%Y}. Ya te agendamos y confirmamos esa '
            f'cita automáticamente -- podés verla en "Mis citas" dentro de '
            f'Pulse SAS.\n\n-- Pulse SAS'
        )
    else:
        cuerpo = (
            f'Hola {paciente.nombre},\n\n'
            f'Tu médico indicó que debes volver a consulta el '
            f'{fecha_proxima_cita:%d/%m/%Y}. Ese horario no se pudo agendar '
            f'automáticamente (puede estar ocupado) -- ingresa a Pulse SAS y '
            f'solicita tu cita para esa fecha desde "Solicitar Citas".\n\n'
            f'-- Pulse SAS'
        )
    try:
        send_mail(
            subject='Recordatorio: tu próxima cita -- Pulse SAS',
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[paciente.correo],
            fail_silently=False,
        )
    except Exception:
        logger.exception('No se pudo enviar recordatorio de próxima cita a %s', paciente.correo)
