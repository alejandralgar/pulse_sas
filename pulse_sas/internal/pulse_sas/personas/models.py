from django.conf import settings
from django.db import models
from django.utils import timezone


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
        ADMINISTRATIVO = 'administrativo', 'Administrativo'
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


class Persona(models.Model):
    class Sexo(models.TextChoices):
        MASCULINO = 'M', 'Masculino'
        FEMENINO = 'F', 'Femenino'
        OTRO = 'O', 'Otro'

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='persona',
    )
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    cedula = models.CharField(max_length=20, unique=True)
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

