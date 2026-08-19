import logging

from django import forms
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from ..models import (
    Antecedente,
    Diagnostico,
    DatosAdministrativos,
    ExamenFisico,
    HistoriaClinica,
    HistoriaClinicaPersona,
    HistoriaEnfermedadActual,
    ItemReceta,
    MotivoConsulta,
    PlanManejo,
    Receta,
)

logger = logging.getLogger(__name__)


def _crear_cita_control_automatica(*, paciente, medico, fecha_proxima_cita, hora_referencia):
    """Auto-crea la cita de control ya CONFIRMADA con el mismo médico
    tratante -- decisión de la usuaria 2026-08-18 (ver 8_FALTO_RESOLVER.md,
    opción 3). Usa la misma hora del día que la cita original (
    `hora_referencia`) como horario por defecto.

    Si esa fecha/hora ya está ocupada (el médico tiene otra cita, o el
    paciente ya tiene una cita ese día) NO crea nada -- se deja el aviso
    del dashboard (`accounts/views.py::vista_cliente`) como respaldo para
    que alguien la agende a mano en otro horario."""
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
    from ..models import Jornada

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


class ConsultaForm(forms.Form):
    """Cubre lo esencial de una consulta: motivo, examen físico básico,
    diagnóstico, tratamiento y plan de manejo -- reparte los campos entre
    `HistoriaClinica` y sus modelos relacionados 1:1. Se usa tanto para
    registrar una consulta nueva (`atender_cita`) como para editarla
    (`editar_historia`), pasando `historia=` para precargar."""

    motivo_consulta = forms.CharField(
        label='Motivo de consulta', widget=forms.Textarea(attrs={'rows': 2}),
    )
    padecimiento_actual = forms.CharField(
        label='Padecimiento actual (descripción cronológica)', required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
    )
    factores_desencadenantes = forms.CharField(
        label='Factores desencadenantes o agravantes', required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
    )
    tratamientos_previos = forms.CharField(
        label='Tratamientos previos para este padecimiento', required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
    )
    antecedentes_familiares = forms.CharField(
        label='Antecedentes heredo-familiares', required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
    )
    antecedentes_personales_patologicos = forms.CharField(
        label='Antecedentes personales patológicos', required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
    )
    antecedentes_no_patologicos = forms.CharField(
        label='Antecedentes personales no patológicos', required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
    )
    tratamiento = forms.CharField(
        label='Tratamiento (resumen)', widget=forms.Textarea(attrs={'rows': 2}),
    )
    presion_arterial = forms.CharField(
        label='Presión arterial', max_length=20, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Ej: 120/80 mmHg'}),
    )
    frecuencia_cardiaca = forms.IntegerField(
        label='Frecuencia cardíaca (lpm)', required=False, min_value=0,
    )
    impresion_diagnostica = forms.CharField(
        label='Impresión diagnóstica', required=False, widget=forms.Textarea(attrs={'rows': 2}),
    )
    diagnostico_confirmado = forms.CharField(
        label='Diagnóstico confirmado', required=False, widget=forms.Textarea(attrs={'rows': 2}),
    )
    tratamiento_indicado = forms.CharField(
        label='Tratamiento indicado (plan)', required=False, widget=forms.Textarea(attrs={'rows': 2}),
    )
    recomendaciones = forms.CharField(
        label='Recomendaciones', required=False, widget=forms.Textarea(attrs={'rows': 2}),
    )
    fecha_proxima_cita = forms.DateField(
        label='Fecha próxima cita (si aplica)', required=False,
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d'],
    )

    def __init__(self, *args, historia=None, medico=None, paciente=None, hora_referencia=None, **kwargs):
        self._medico = medico
        self._paciente = paciente
        self._hora_referencia = hora_referencia
        initial = kwargs.pop('initial', None) or {}
        if historia is not None:
            initial.setdefault('tratamiento', historia.tratamiento)
            if hasattr(historia, 'motivo_consulta'):
                initial.setdefault('motivo_consulta', historia.motivo_consulta.descripcion)
            if hasattr(historia, 'examen_fisico'):
                initial.setdefault('presion_arterial', historia.examen_fisico.presion_arterial)
                initial.setdefault('frecuencia_cardiaca', historia.examen_fisico.frecuencia_cardiaca)
            if hasattr(historia, 'diagnostico'):
                initial.setdefault('impresion_diagnostica', historia.diagnostico.impresion_diagnostica)
                initial.setdefault('diagnostico_confirmado', historia.diagnostico.diagnostico_confirmado)
            if hasattr(historia, 'plan_de_manejo'):
                initial.setdefault('tratamiento_indicado', historia.plan_de_manejo.tratamiento_indicado)
                initial.setdefault('recomendaciones', historia.plan_de_manejo.recomendaciones)
                initial.setdefault('fecha_proxima_cita', historia.plan_de_manejo.fecha_proxima_cita)
            if hasattr(historia, 'enfermedad_actual'):
                initial.setdefault('padecimiento_actual', historia.enfermedad_actual.descripcion_cronologica)
                initial.setdefault('factores_desencadenantes', historia.enfermedad_actual.factores_desencadenantes)
                initial.setdefault('tratamientos_previos', historia.enfermedad_actual.tratamientos_previos)
            if hasattr(historia, 'antecedente'):
                initial.setdefault('antecedentes_familiares', historia.antecedente.familiares)
                initial.setdefault('antecedentes_personales_patologicos', historia.antecedente.personales_patologicos)
                initial.setdefault('antecedentes_no_patologicos', historia.antecedente.no_patologicos)
        super().__init__(*args, initial=initial, **kwargs)

    advertencia_fecha_proxima_cita = None

    def clean_fecha_proxima_cita(self):
        fecha = self.cleaned_data.get('fecha_proxima_cita')
        if fecha and self._medico and self._paciente and self._hora_referencia:
            bloqueante, motivo = _validar_fecha_proxima_cita(
                medico=self._medico, paciente=self._paciente,
                fecha=fecha, hora_referencia=self._hora_referencia,
            )
            if bloqueante:
                raise forms.ValidationError(motivo)
            self.advertencia_fecha_proxima_cita = motivo
        return fecha

    @transaction.atomic
    def guardar_nueva(self, *, cita, medico):
        from django.utils import timezone
        from pulse_sas.internal.pulse_sas.citas.models import Cita

        d = self.cleaned_data
        ahora = timezone.now()

        historia = HistoriaClinica.objects.create(
            tratamiento=d['tratamiento'], fecha_ingreso_paciente=ahora,
        )
        HistoriaClinicaPersona.objects.create(
            historia_clinica=historia, persona=cita.persona,
            rol_en_historia=HistoriaClinicaPersona.RolEnHistoria.PACIENTE,
        )
        HistoriaClinicaPersona.objects.create(
            historia_clinica=historia, persona=medico,
            rol_en_historia=HistoriaClinicaPersona.RolEnHistoria.MEDICO_TRATANTE,
        )
        MotivoConsulta.objects.create(historia_clinica=historia, descripcion=d['motivo_consulta'])
        HistoriaEnfermedadActual.objects.create(
            historia_clinica=historia,
            descripcion_cronologica=d.get('padecimiento_actual', ''),
            factores_desencadenantes=d.get('factores_desencadenantes', ''),
            tratamientos_previos=d.get('tratamientos_previos', ''),
        )
        Antecedente.objects.create(
            historia_clinica=historia,
            familiares=d.get('antecedentes_familiares', ''),
            personales_patologicos=d.get('antecedentes_personales_patologicos', ''),
            no_patologicos=d.get('antecedentes_no_patologicos', ''),
        )
        ExamenFisico.objects.create(
            historia_clinica=historia,
            presion_arterial=d.get('presion_arterial', ''),
            frecuencia_cardiaca=d.get('frecuencia_cardiaca'),
        )
        Diagnostico.objects.create(
            historia_clinica=historia,
            impresion_diagnostica=d.get('impresion_diagnostica', ''),
            diagnostico_confirmado=d.get('diagnostico_confirmado', ''),
        )
        PlanManejo.objects.create(
            historia_clinica=historia,
            tratamiento_indicado=d.get('tratamiento_indicado', ''),
            recomendaciones=d.get('recomendaciones', ''),
            fecha_proxima_cita=d.get('fecha_proxima_cita'),
        )
        DatosAdministrativos.objects.create(
            historia_clinica=historia, profesional=medico, fecha_hora_atencion=ahora,
        )

        cita.historia_clinica = historia
        cita.estado = Cita.Estado.ATENDIDA
        cita.save(update_fields=['historia_clinica', 'estado'])

        if d.get('fecha_proxima_cita'):
            cita_control = _crear_cita_control_automatica(
                paciente=cita.persona, medico=medico,
                fecha_proxima_cita=d['fecha_proxima_cita'], hora_referencia=cita.fecha_hora,
            )
            _enviar_recordatorio_proxima_cita(
                cita.persona, d['fecha_proxima_cita'], cita_ya_confirmada=cita_control is not None,
            )

        return historia

    @transaction.atomic
    def guardar_edicion(self, *, historia):
        d = self.cleaned_data
        historia.tratamiento = d['tratamiento']
        historia.save(update_fields=['tratamiento'])

        MotivoConsulta.objects.update_or_create(
            historia_clinica=historia, defaults={'descripcion': d['motivo_consulta']},
        )
        HistoriaEnfermedadActual.objects.update_or_create(
            historia_clinica=historia,
            defaults={
                'descripcion_cronologica': d.get('padecimiento_actual', ''),
                'factores_desencadenantes': d.get('factores_desencadenantes', ''),
                'tratamientos_previos': d.get('tratamientos_previos', ''),
            },
        )
        Antecedente.objects.update_or_create(
            historia_clinica=historia,
            defaults={
                'familiares': d.get('antecedentes_familiares', ''),
                'personales_patologicos': d.get('antecedentes_personales_patologicos', ''),
                'no_patologicos': d.get('antecedentes_no_patologicos', ''),
            },
        )
        ExamenFisico.objects.update_or_create(
            historia_clinica=historia,
            defaults={
                'presion_arterial': d.get('presion_arterial', ''),
                'frecuencia_cardiaca': d.get('frecuencia_cardiaca'),
            },
        )
        Diagnostico.objects.update_or_create(
            historia_clinica=historia,
            defaults={
                'impresion_diagnostica': d.get('impresion_diagnostica', ''),
                'diagnostico_confirmado': d.get('diagnostico_confirmado', ''),
            },
        )
        PlanManejo.objects.update_or_create(
            historia_clinica=historia,
            defaults={
                'tratamiento_indicado': d.get('tratamiento_indicado', ''),
                'recomendaciones': d.get('recomendaciones', ''),
                'fecha_proxima_cita': d.get('fecha_proxima_cita'),
            },
        )
        return historia


class RecetaForm(forms.ModelForm):
    class Meta:
        model = Receta
        fields = ['indicaciones_generales']
        labels = {'indicaciones_generales': 'Indicaciones generales'}
        widgets = {'indicaciones_generales': forms.Textarea(attrs={'rows': 3})}


ItemRecetaFormSet = forms.inlineformset_factory(
    Receta, ItemReceta,
    fields=['medicamento', 'dosis', 'frecuencia', 'duracion', 'indicaciones'],
    extra=1, can_delete=True,
    widgets={
        'medicamento': forms.TextInput(attrs={'placeholder': 'Ej: Acetaminofén'}),
        'dosis': forms.TextInput(attrs={'placeholder': 'Ej: 500mg'}),
        'frecuencia': forms.TextInput(attrs={'placeholder': 'Ej: cada 8 horas'}),
        'duracion': forms.TextInput(attrs={'placeholder': 'Ej: 5 días'}),
        'indicaciones': forms.TextInput(attrs={'placeholder': 'Ej: Con alimentos'}),
    },
)
