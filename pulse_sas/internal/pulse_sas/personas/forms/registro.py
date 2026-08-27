from django import forms
from django.contrib.auth.models import User
from django.db import transaction

from ..models import Convenio, Persona, Rol


class _RegistroUsuarioBaseForm(forms.Form):
    """Campos comunes para crear un `User` + `Persona` con rol(es)
    asignados. Subclases fijan `roles_queryset` para acotar qué roles
    puede asignar cada actor (Admin: todos; Gerente: solo roles de
    empleado; Recepcionista: solo paciente)."""

    roles_queryset = Rol.objects.all()

    username = forms.CharField(max_length=150, label='Usuario')
    email = forms.EmailField(label='Correo')
    password1 = forms.CharField(widget=forms.PasswordInput, label='Contraseña')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirmar contraseña')
    nombre = forms.CharField(max_length=100)
    apellido = forms.CharField(max_length=100)
    tipo_documento = forms.ChoiceField(choices=Persona.TipoDocumento.choices, label='Tipo de documento')
    cedula = forms.CharField(max_length=20, label='Cédula / Documento')
    fecha_nacimiento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    especialidad = forms.CharField(
        max_length=150, required=False, label='Especialidad (solo médicos)',
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Cardiología, Pediatría...'}),
    )
    roles = forms.ModelMultipleChoiceField(
        queryset=Rol.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label='Rol(es)',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['roles'].queryset = self.roles_queryset

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Ya existe un usuario con ese nombre de usuario.')
        return username

    def clean_cedula(self):
        cedula = self.cleaned_data['cedula']
        if Persona.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError('Ya existe una persona registrada con esa cédula.')
        return cedula

    def clean_fecha_nacimiento(self):
        from django.utils import timezone
        fecha = self.cleaned_data['fecha_nacimiento']
        if fecha > timezone.localdate():
            raise forms.ValidationError('La fecha de nacimiento no puede ser futura.')
        return fecha

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get('password1')
        password2 = cleaned.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned

    @transaction.atomic
    def save(self, registrado_por=None):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password1'],
        )
        persona = Persona.objects.create(
            usuario=user,
            nombre=self.cleaned_data['nombre'],
            apellido=self.cleaned_data['apellido'],
            tipo_documento=self.cleaned_data['tipo_documento'],
            cedula=self.cleaned_data['cedula'],
            fecha_nacimiento=self.cleaned_data['fecha_nacimiento'],
            correo=self.cleaned_data['email'],
            registrado_por=registrado_por,
            especialidad=self.cleaned_data['especialidad'],
        )
        persona.roles.set(self.cleaned_data['roles'])
        return persona


class _EditarPersonaBaseForm(forms.ModelForm):
    """Base para editar datos + roles de una `Persona` ya existente.
    Subclases fijan `roles_queryset` (qué roles puede dejar asignados
    quien edita)."""

    roles_queryset = Rol.objects.all()

    roles = forms.ModelMultipleChoiceField(
        queryset=Rol.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label='Rol(es)',
    )

    class Meta:
        model = Persona
        fields = ['nombre', 'apellido', 'tipo_documento', 'cedula', 'fecha_nacimiento', 'correo', 'especialidad']
        widgets = {'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'})}
        labels = {'especialidad': 'Especialidad (solo médicos)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['roles'].queryset = self.roles_queryset
        if self.instance.pk:
            self.fields['roles'].initial = self.instance.roles.all()

    def save(self, commit=True):
        persona = super().save(commit=commit)
        if commit:
            persona.roles.set(self.cleaned_data['roles'])
        return persona


class ConvenioForm(forms.ModelForm):
    """Form del modelo `Convenio` -- compartido: lo usan Admin y Gerente."""

    class Meta:
        model = Convenio
        fields = ['nombre', 'nit', 'telefono', 'especialidad']
