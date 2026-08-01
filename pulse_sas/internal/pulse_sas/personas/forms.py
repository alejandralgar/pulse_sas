from django import forms

from .models import Ciudad, ContactoEmergencia, Persona


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
