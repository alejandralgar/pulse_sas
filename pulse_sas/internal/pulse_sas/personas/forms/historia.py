from django import forms
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
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    def __init__(self, *args, historia=None, **kwargs):
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
    extra=3, can_delete=True,
    widgets={
        'medicamento': forms.TextInput(attrs={'placeholder': 'Ej: Acetaminofén'}),
        'dosis': forms.TextInput(attrs={'placeholder': 'Ej: 500mg'}),
        'frecuencia': forms.TextInput(attrs={'placeholder': 'Ej: cada 8 horas'}),
        'duracion': forms.TextInput(attrs={'placeholder': 'Ej: 5 días'}),
        'indicaciones': forms.TextInput(attrs={'placeholder': 'Ej: Con alimentos'}),
    },
)
