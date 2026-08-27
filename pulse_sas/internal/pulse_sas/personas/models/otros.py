from django.db import models

from .catalogo import Ciudad
from .persona import Persona


class ContactoEmergencia(models.Model):
    paciente = models.ForeignKey(
        Persona, on_delete=models.CASCADE, related_name='contactos_emergencia',
        verbose_name='paciente',
    )
    nombre_completo = models.CharField('nombre completo', max_length=200)
    cedula = models.CharField('cédula / identificación', max_length=20, blank=True)
    correo = models.EmailField('correo electrónico', blank=True)
    telefono = models.CharField('teléfono', max_length=20)
    parentesco = models.CharField(max_length=80)
    ciudad_residencia = models.ForeignKey(
        Ciudad, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='contactos_emergencia', verbose_name='ciudad de residencia',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'contacto de emergencia'
        verbose_name_plural = 'contactos de emergencia'
        ordering = ['-creado_en']

    def __str__(self):
        return f'{self.nombre_completo} ({self.parentesco}) → {self.paciente}'


class Jornada(models.Model):
    class TipoJornada(models.TextChoices):
        MANANA = 'manana', 'Mañana'
        TARDE = 'tarde', 'Tarde'
        NOCHE = 'noche', 'Noche'

    persona = models.ForeignKey(
        Persona, on_delete=models.CASCADE, related_name='jornadas',
        verbose_name='persona',
    )
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    tipo_jornada = models.CharField(max_length=10, choices=TipoJornada.choices)

    class Meta:
        verbose_name = 'jornada'
        verbose_name_plural = 'jornadas'
        ordering = ['-fecha', 'hora_inicio']

    def __str__(self):
        return f'{self.persona} - {self.fecha} ({self.get_tipo_jornada_display()})'


class SolicitudRegistroPaciente(models.Model):
    """Un médico encontró a alguien no registrado buscando pacientes
    (caso de urgencia) y pide que Recepcionista lo registre."""

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    cedula = models.CharField(max_length=20, blank=True)
    motivo = models.TextField(blank=True)
    solicitado_por = models.ForeignKey(
        Persona, on_delete=models.SET_NULL, null=True,
        related_name='solicitudes_registro_hechas',
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    atendida = models.BooleanField(default=False)
    atendida_por = models.ForeignKey(
        Persona, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='solicitudes_registro_atendidas',
    )
    fecha_atendida = models.DateTimeField(null=True, blank=True)
    persona_creada = models.ForeignKey(
        Persona, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )

    class Meta:
        verbose_name = 'solicitud de registro de paciente'
        verbose_name_plural = 'solicitudes de registro de paciente'
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f'{self.nombre} {self.apellido} (pedido por {self.solicitado_por})'


class Convenio(models.Model):
    nombre = models.CharField(max_length=150, verbose_name="Nombre de la Empresa")
    nit = models.CharField(max_length=50, verbose_name="NIT")
    telefono = models.CharField(max_length=50, verbose_name="Teléfono")
    especialidad = models.CharField(max_length=150, verbose_name="Especialidad / Servicio")

    class Meta:
        db_table = 'convenio'
        verbose_name = 'Convenio'
        verbose_name_plural = 'Convenios'

    def __str__(self):
        return self.nombre
