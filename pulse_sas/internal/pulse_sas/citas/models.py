from django.db import models

from pulse_sas.internal.pulse_sas.personas.models import Persona


class Cita(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        CONFIRMADA = 'confirmada', 'Confirmada'
        CANCELADA = 'cancelada', 'Cancelada'
        REPROGRAMADA = 'reprogramada', 'Reprogramada'

    class TipoCita(models.TextChoices):
        CONSULTA_GENERAL = 'consulta_general', 'Consulta general'
        CONTROL = 'control', 'Control'
        URGENCIA = 'urgencia', 'Urgencia'
        ESPECIALISTA = 'especialista', 'Especialista'
        LABORATORIO = 'laboratorio', 'Laboratorio / Examen'

    persona = models.ForeignKey(
        Persona, on_delete=models.CASCADE, related_name='citas_como_paciente'
    )
    medico = models.ForeignKey(
        Persona, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='citas_como_medico',
    )
    fecha_hora = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    tipo_cita = models.CharField('tipo de cita', max_length=50, choices=TipoCita.choices, blank=True)
    motivo = models.CharField(max_length=200, help_text='Consulta general, control, examen, etc.')
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = 'cita'
        verbose_name_plural = 'citas'
        ordering = ['-fecha_hora']

    def __str__(self):
        return f'Cita #{self.pk} - {self.persona} ({self.fecha_hora:%Y-%m-%d %H:%M})'


class CitaHistorial(models.Model):
    class Accion(models.TextChoices):
        RESERVAR = 'reservar', 'Reservar'
        CANCELAR = 'cancelar', 'Cancelar'
        REPROGRAMAR = 'reprogramar', 'Reprogramar'

    cita = models.ForeignKey(Cita, on_delete=models.CASCADE, related_name='historial')
    accion = models.CharField(max_length=20, choices=Accion.choices)
    fecha_accion = models.DateTimeField(auto_now_add=True)
    usuario_responsable = models.ForeignKey(
        Persona, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='acciones_citas',
    )
    comentario = models.TextField(blank=True)

    class Meta:
        verbose_name = 'historial de cita'
        verbose_name_plural = 'historial de citas'
        ordering = ['-fecha_accion']

    def __str__(self):
        return f'{self.accion} - {self.cita} ({self.fecha_accion:%Y-%m-%d %H:%M})'
