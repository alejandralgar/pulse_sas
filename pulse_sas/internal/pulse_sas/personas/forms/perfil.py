from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from ..models import Ciudad, ContactoEmergencia, Pais, Persona


class PerfilEditableForm(forms.ModelForm):
    """Campos que el paciente puede editar en su perfil."""

    ciudad_residencia = forms.ModelChoiceField(
        queryset=Ciudad.objects.all().order_by('nombre'),
        required=False,
        label='Ciudad de residencia',
        empty_label='Seleccionar ciudad...',
    )

    class Meta:
        model = Persona
        fields = ['correo', 'telefono_personal', 'direccion', 'ciudad_residencia', 'eps_ips']
        labels = {
            'correo': 'Correo electrónico',
            'telefono_personal': 'Número de celular',
            'direccion': 'Dirección de residencia',
            'eps_ips': 'IPS / EPS',
        }
        widgets = {
            'correo': forms.EmailInput(attrs={'placeholder': 'correo@ejemplo.com'}),
            'telefono_personal': forms.TextInput(attrs={'placeholder': 'Ej: 3001234567'}),
            'direccion': forms.TextInput(attrs={'placeholder': 'Ej: Calle 10 #15-20'}),
            'eps_ips': forms.TextInput(attrs={'placeholder': 'Ej: Sanitas EPS'}),
        }


class ContactoEmergenciaForm(forms.ModelForm):
    """Formulario de persona de contacto / emergencia."""

    ciudad_residencia = forms.ModelChoiceField(
        queryset=Ciudad.objects.all().order_by('nombre'),
        required=False,
        label='Ciudad de residencia',
        empty_label='Seleccionar ciudad...',
    )

    class Meta:
        model = ContactoEmergencia
        fields = ['nombre_completo', 'cedula', 'correo', 'telefono', 'parentesco', 'ciudad_residencia']
        labels = {
            'nombre_completo': 'Nombre completo',
            'cedula': 'Cédula / Identificación',
            'correo': 'Correo electrónico',
            'telefono': 'Número de teléfono',
            'parentesco': 'Parentesco',
        }
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'placeholder': 'Nombre y apellidos'}),
            'cedula': forms.TextInput(attrs={'placeholder': 'Número de documento'}),
            'correo': forms.EmailInput(attrs={'placeholder': 'correo@ejemplo.com'}),
            'telefono': forms.TextInput(attrs={'placeholder': 'Ej: 3001234567'}),
            'parentesco': forms.TextInput(attrs={'placeholder': 'Ej: Madre, Esposo/a, Hermano/a'}),
        }


class MiPerfilForm(forms.ModelForm):
    """Formulario de 'Mi Perfil' -- edición de datos personales, igual
    para cualquier rol. El rol/cargo NO se edita acá (lo maneja Admin)."""

    username = forms.CharField(max_length=150, label='Usuario')

    pais_nacimiento = forms.ModelChoiceField(
        queryset=Pais.objects.all().order_by('nombre'), required=False,
        label='País de nacimiento', empty_label='Seleccionar país...',
    )
    ciudad_nacimiento = forms.ModelChoiceField(
        queryset=Ciudad.objects.all().order_by('nombre'), required=False,
        label='Ciudad de nacimiento', empty_label='Seleccionar ciudad...',
    )
    pais_residencia = forms.ModelChoiceField(
        queryset=Pais.objects.all().order_by('nombre'), required=False,
        label='País de residencia', empty_label='Seleccionar país...',
    )
    ciudad_residencia = forms.ModelChoiceField(
        queryset=Ciudad.objects.all().order_by('nombre'), required=False,
        label='Ciudad de residencia', empty_label='Seleccionar ciudad...',
    )
    telefono_personal_pais = forms.ModelChoiceField(
        queryset=Pais.objects.all().order_by('nombre'), required=False,
        label='País', empty_label='País...',
    )
    telefono_familiar1_pais = forms.ModelChoiceField(
        queryset=Pais.objects.all().order_by('nombre'), required=False,
        label='País', empty_label='País...',
    )
    telefono_familiar2_pais = forms.ModelChoiceField(
        queryset=Pais.objects.all().order_by('nombre'), required=False,
        label='País', empty_label='País...',
    )

    class Meta:
        model = Persona
        fields = [
            'nombre', 'apellido', 'cedula', 'fecha_nacimiento',
            'correo', 'correo_recuperacion',
            'telefono_personal', 'telefono_personal_pais',
            'telefono_familiar1', 'telefono_familiar1_pais',
            'telefono_familiar2', 'telefono_familiar2_pais',
            'direccion',
            'pais_nacimiento', 'ciudad_nacimiento',
            'pais_residencia', 'ciudad_residencia',
        ]
        labels = {
            'correo': 'Correo electrónico personal',
            'correo_recuperacion': 'Correo de recuperación',
            'telefono_personal': 'Teléfono personal',
            'telefono_familiar1': 'Teléfono familiar 1',
            'telefono_familiar2': 'Teléfono familiar 2',
            'direccion': 'Dirección de residencia',
        }
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.usuario:
            self.fields['username'].initial = self.instance.usuario.username

    def clean_username(self):
        username = self.cleaned_data['username']
        qs = User.objects.filter(username=username)
        if self.instance.usuario_id:
            qs = qs.exclude(pk=self.instance.usuario_id)
        if qs.exists():
            raise forms.ValidationError('Ya existe otro usuario con ese nombre de usuario.')
        return username

    def clean_cedula(self):
        cedula = self.cleaned_data['cedula']
        qs = Persona.objects.filter(cedula=cedula)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Ya existe otra persona registrada con esa cédula.')
        return cedula

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data['fecha_nacimiento']
        if fecha > timezone.localdate():
            raise forms.ValidationError('La fecha de nacimiento no puede ser futura.')
        return fecha

    def clean(self):
        cleaned = super().clean()
        numeros = {
            'telefono_personal': (cleaned.get('telefono_personal') or '').strip(),
            'telefono_familiar1': (cleaned.get('telefono_familiar1') or '').strip(),
            'telefono_familiar2': (cleaned.get('telefono_familiar2') or '').strip(),
        }
        vistos = {}
        for campo, numero in numeros.items():
            if not numero:
                continue
            if numero in vistos:
                msg = 'No puede repetir el mismo número en dos campos de teléfono distintos.'
                self.add_error(campo, msg)
                self.add_error(vistos[numero], msg)
            else:
                vistos[numero] = campo
        return cleaned

    def save(self, commit=True):
        persona = super().save(commit=commit)
        if commit and persona.usuario:
            persona.usuario.username = self.cleaned_data['username']
            persona.usuario.save(update_fields=['username'])
        return persona
