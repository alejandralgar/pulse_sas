from django.conf import settings
from django.db import models
from django.utils import timezone

from .catalogo import Ciudad, Pais, Rol, TipoSangre


class Persona(models.Model):
    class Sexo(models.TextChoices):
        MASCULINO = 'M', 'Masculino'
        FEMENINO = 'F', 'Femenino'
        OTRO = 'O', 'Otro'

    class TipoDocumento(models.TextChoices):
        CC = 'CC', 'Cédula de ciudadanía'
        TI = 'TI', 'Tarjeta de identidad'
        CE = 'CE', 'Cédula de extranjería'
        RC = 'RC', 'Registro civil'
        PA = 'PA', 'Pasaporte'

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='persona',
    )
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    tipo_documento = models.CharField(max_length=2, choices=TipoDocumento.choices, default=TipoDocumento.CC)
    cedula = models.CharField('cédula / documento', max_length=20, unique=True)
    fecha_nacimiento = models.DateField()
    sexo = models.CharField(max_length=1, choices=Sexo.choices, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    pais_nacimiento = models.ForeignKey(
        Pais, on_delete=models.SET_NULL, null=True, blank=True, related_name='personas_nacidas'
    )
    ciudad_nacimiento = models.ForeignKey(
        Ciudad, on_delete=models.SET_NULL, null=True, blank=True, related_name='personas_nacidas'
    )
    telefono_personal = models.CharField(max_length=20, blank=True)
    telefono_personal_pais = models.ForeignKey(
        Pais, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='telefonos_personales', verbose_name='país del teléfono personal',
    )
    telefono_familiar1 = models.CharField('teléfono familiar 1', max_length=20, blank=True)
    telefono_familiar1_pais = models.ForeignKey(
        Pais, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='telefonos_familiar1', verbose_name='país del teléfono familiar 1',
    )
    telefono_familiar2 = models.CharField('teléfono familiar 2', max_length=20, blank=True)
    telefono_familiar2_pais = models.ForeignKey(
        Pais, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='telefonos_familiar2', verbose_name='país del teléfono familiar 2',
    )
    correo = models.EmailField('correo electrónico personal')
    correo_recuperacion = models.EmailField('correo de recuperación', blank=True)
    eps_ips = models.CharField('EPS / IPS', max_length=150, blank=True)
    pais_residencia = models.ForeignKey(
        Pais, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='personas_residentes', verbose_name='país de residencia',
    )
    ciudad_residencia = models.ForeignKey(
        'Ciudad', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='residentes', verbose_name='ciudad de residencia',
    )
    roles = models.ManyToManyField(Rol, through='RolPersona', related_name='personas')
    tipos_sangre = models.ManyToManyField(TipoSangre, through='TipoSangrePersona', related_name='personas')
    especialidad = models.CharField(
        'especialidad médica', max_length=150, blank=True,
        help_text='Solo aplica a personas con rol médico.',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='registros_realizados', verbose_name='registrado por',
    )

    class Meta:
        verbose_name = 'persona'
        verbose_name_plural = 'personas'
        ordering = ['apellido', 'nombre']

    def __str__(self):
        return f'{self.nombre} {self.apellido}'

    @property
    def edad_actual(self):
        hoy = timezone.localdate()
        anios = hoy.year - self.fecha_nacimiento.year
        if (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day):
            anios -= 1
        return anios


class RolPersona(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'rol de persona'
        verbose_name_plural = 'roles de persona'
        unique_together = ('persona', 'rol')

    def __str__(self):
        return f'{self.persona} - {self.rol}'


class TipoSangrePersona(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    tipo_sangre = models.ForeignKey(TipoSangre, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'tipo de sangre de persona'
        verbose_name_plural = 'tipos de sangre de persona'
        unique_together = ('persona', 'tipo_sangre')

    def __str__(self):
        return f'{self.persona} - {self.tipo_sangre}'
