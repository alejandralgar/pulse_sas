from django.db import models

from .persona import Persona


class HistoriaClinica(models.Model):
    class Autorizacion(models.TextChoices):
        MEDICO = 'medico', 'Médico'
        PACIENTE = 'paciente', 'Paciente'
        ACOMPANANTE = 'acompanante', 'Acompañante / familiar'

    tratamiento = models.TextField()
    fecha_ingreso_paciente = models.DateTimeField()
    fecha_salida_paciente = models.DateTimeField(null=True, blank=True)
    tipo_autorizacion_salida = models.CharField(
        max_length=20, choices=Autorizacion.choices, blank=True
    )
    autorizado_por = models.ForeignKey(
        Persona,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='autorizaciones_realizadas',
    )
    persona_contacto = models.ForeignKey(
        Persona,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contacto_de_historias',
        verbose_name='persona de contacto / acompañante',
    )
    ocupacion = models.CharField(max_length=100, blank=True)
    personas = models.ManyToManyField(
        Persona, through='HistoriaClinicaPersona', related_name='historias_clinicas'
    )

    class Meta:
        verbose_name = 'historia clínica'
        verbose_name_plural = 'historias clínicas'
        ordering = ['-fecha_ingreso_paciente']

    def __str__(self):
        return f'Historia clínica #{self.pk}'


class HistoriaClinicaPersona(models.Model):
    class RolEnHistoria(models.TextChoices):
        PACIENTE = 'paciente', 'Paciente'
        MEDICO_TRATANTE = 'medico_tratante', 'Médico tratante'
        ACOMPANANTE = 'acompanante', 'Acompañante / familiar'

    historia_clinica = models.ForeignKey(HistoriaClinica, on_delete=models.CASCADE)
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    rol_en_historia = models.CharField(max_length=20, choices=RolEnHistoria.choices)

    class Meta:
        verbose_name = 'persona en historia clínica'
        verbose_name_plural = 'personas en historia clínica'
        unique_together = ('historia_clinica', 'persona', 'rol_en_historia')

    def __str__(self):
        return f'{self.persona} - {self.historia_clinica} ({self.rol_en_historia})'


class Antecedente(models.Model):
    historia_clinica = models.OneToOneField(
        HistoriaClinica, on_delete=models.CASCADE, related_name='antecedente'
    )
    personales_patologicos = models.TextField(
        'antecedentes personales patológicos', blank=True,
        help_text='Enfermedades previas, cirugías, hospitalizaciones'
    )
    familiares = models.TextField(
        'antecedentes familiares', blank=True,
        help_text='Enfermedades hereditarias o frecuentes en la familia'
    )
    no_patologicos = models.TextField(
        'antecedentes no patológicos', blank=True,
        help_text='Hábitos: alimentación, ejercicio, consumo de sustancias, vacunas'
    )

    class Meta:
        verbose_name = 'antecedente'
        verbose_name_plural = 'antecedentes'

    def __str__(self):
        return f'Antecedentes - {self.historia_clinica}'


class MotivoConsulta(models.Model):
    historia_clinica = models.OneToOneField(
        HistoriaClinica, on_delete=models.CASCADE, related_name='motivo_consulta'
    )
    descripcion = models.TextField(
        help_text='Razón principal por la que el paciente acude (dolor, control, chequeo, etc.)'
    )

    class Meta:
        verbose_name = 'motivo de consulta'
        verbose_name_plural = 'motivos de consulta'

    def __str__(self):
        return f'Motivo consulta - {self.historia_clinica}'


class HistoriaEnfermedadActual(models.Model):
    historia_clinica = models.OneToOneField(
        HistoriaClinica, on_delete=models.CASCADE, related_name='enfermedad_actual'
    )
    descripcion_cronologica = models.TextField(blank=True, help_text='Descripción cronológica de los síntomas')
    factores_desencadenantes = models.TextField(blank=True, help_text='Factores desencadenantes o agravantes')
    tratamientos_previos = models.TextField(blank=True)

    class Meta:
        verbose_name = 'historia de la enfermedad actual'
        verbose_name_plural = 'historias de la enfermedad actual'

    def __str__(self):
        return f'Enfermedad actual - {self.historia_clinica}'


class ExamenFisico(models.Model):
    historia_clinica = models.OneToOneField(
        HistoriaClinica, on_delete=models.CASCADE, related_name='examen_fisico'
    )
    presion_arterial = models.CharField(max_length=20, blank=True)
    frecuencia_cardiaca = models.PositiveSmallIntegerField(null=True, blank=True)
    temperatura = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    frecuencia_respiratoria = models.PositiveSmallIntegerField(null=True, blank=True)
    evaluacion_por_sistemas = models.TextField(
        blank=True, help_text='Respiratorio, cardiovascular, digestivo, neurológico, etc.'
    )

    class Meta:
        verbose_name = 'examen físico'
        verbose_name_plural = 'exámenes físicos'

    def __str__(self):
        return f'Examen físico - {self.historia_clinica}'


class ExamenComplementario(models.Model):
    historia_clinica = models.ForeignKey(
        HistoriaClinica, on_delete=models.CASCADE, related_name='examenes_complementarios'
    )
    tipo = models.CharField(max_length=100, help_text='Laboratorio, imagen diagnóstica, prueba especial')
    resultado = models.TextField(blank=True)
    fecha = models.DateField()

    class Meta:
        verbose_name = 'examen complementario'
        verbose_name_plural = 'exámenes complementarios'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.tipo} - {self.historia_clinica}'


class Diagnostico(models.Model):
    historia_clinica = models.OneToOneField(
        HistoriaClinica, on_delete=models.CASCADE, related_name='diagnostico'
    )
    impresion_diagnostica = models.TextField(blank=True, help_text='Hipótesis inicial')
    diagnostico_confirmado = models.TextField(blank=True)

    class Meta:
        verbose_name = 'diagnóstico'
        verbose_name_plural = 'diagnósticos'

    def __str__(self):
        return f'Diagnóstico - {self.historia_clinica}'


class PlanManejo(models.Model):
    historia_clinica = models.OneToOneField(
        HistoriaClinica, on_delete=models.CASCADE, related_name='plan_de_manejo'
    )
    tratamiento_indicado = models.TextField(
        blank=True, help_text='Medicamentos, terapias, procedimientos'
    )
    recomendaciones = models.TextField(blank=True)
    fecha_proxima_cita = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'plan de manejo'
        verbose_name_plural = 'planes de manejo'

    def __str__(self):
        return f'Plan de manejo - {self.historia_clinica}'


class Receta(models.Model):
    """Receta médica -- junto con `HistoriaClinica` forma lo que la
    usuaria llama 'epicrisis'. Mismo médico, misma ventana de edición
    (día de la consulta) que la historia clínica asociada."""

    historia_clinica = models.OneToOneField(
        HistoriaClinica, on_delete=models.CASCADE, related_name='receta'
    )
    indicaciones_generales = models.TextField(blank=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'receta médica'
        verbose_name_plural = 'recetas médicas'

    def __str__(self):
        return f'Receta - {self.historia_clinica}'


class ItemReceta(models.Model):
    receta = models.ForeignKey(Receta, on_delete=models.CASCADE, related_name='medicamentos')
    medicamento = models.CharField(max_length=150)
    dosis = models.CharField(max_length=100, blank=True)
    frecuencia = models.CharField(max_length=100, blank=True)
    duracion = models.CharField(max_length=100, blank=True)
    indicaciones = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'medicamento recetado'
        verbose_name_plural = 'medicamentos recetados'

    def __str__(self):
        return f'{self.medicamento} - {self.receta}'


class DatosAdministrativos(models.Model):
    historia_clinica = models.OneToOneField(
        HistoriaClinica, on_delete=models.CASCADE, related_name='datos_administrativos'
    )
    profesional = models.ForeignKey(
        Persona, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='atenciones_realizadas',
        verbose_name='profesional de la salud',
    )
    fecha_hora_atencion = models.DateTimeField()

    class Meta:
        verbose_name = 'datos administrativos'
        verbose_name_plural = 'datos administrativos'

    def __str__(self):
        return f'Datos administrativos - {self.historia_clinica}'
