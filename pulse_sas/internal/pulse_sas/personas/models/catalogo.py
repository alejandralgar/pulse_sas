from django.db import models


class Pais(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    codigo_iso = models.CharField(max_length=3, unique=True, blank=True, null=True)

    class Meta:
        verbose_name = 'país'
        verbose_name_plural = 'países'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Ciudad(models.Model):
    nombre = models.CharField(max_length=100)
    paises = models.ManyToManyField(Pais, through='PaisCiudad', related_name='ciudades')

    class Meta:
        verbose_name = 'ciudad'
        verbose_name_plural = 'ciudades'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class PaisCiudad(models.Model):
    pais = models.ForeignKey(Pais, on_delete=models.CASCADE)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'país-ciudad'
        verbose_name_plural = 'país-ciudad'
        unique_together = ('pais', 'ciudad')

    def __str__(self):
        return f'{self.ciudad} ({self.pais})'


class TipoSangre(models.Model):
    nombre = models.CharField(max_length=3, unique=True)

    class Meta:
        verbose_name = 'tipo de sangre'
        verbose_name_plural = 'tipos de sangre'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Rol(models.Model):
    class Categoria(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        CLIENTE_PACIENTE = 'cliente_paciente', 'Cliente / paciente'
        EMPRESA = 'empresa', 'Empresa'
        GERENTE = 'gerente', 'Gerente'
        RECEPCIONISTA = 'recepcionista', 'Recepcionista'
        MEDICO = 'medico', 'Médico'
        ENFERMERA = 'enfermera', 'Enfermera'
        GUARDIA = 'guardia', 'Guardia de seguridad'

    nombre = models.CharField(max_length=50, unique=True)
    categoria = models.CharField(max_length=20, choices=Categoria.choices)

    class Meta:
        verbose_name = 'rol'
        verbose_name_plural = 'roles'
        ordering = ['categoria', 'nombre']

    def __str__(self):
        return self.nombre
