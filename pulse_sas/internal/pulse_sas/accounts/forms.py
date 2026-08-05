from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

# Roles disponibles para registro/login
ROL_CHOICES = [
    ('',                 'Selecciona tu rol...'),
    ('admin',            'Administrador'),
    ('administrativo',   'Administrativo (Secretaria / Recepcionista)'),
    ('medico',           'Médico'),
    ('enfermera',        'Enfermera'),
    ('guardia',          'Guardia de Seguridad'),
    ('cliente_paciente', 'Paciente'),
    ('empresa',          'Empresa / EPS'),
]


TIPO_SANGRE_CHOICES = [
    ('', 'Seleccionar tipo de sangre...'),
    ('A+', 'A+'),
    ('A-', 'A-'),
    ('B+', 'B+'),
    ('B-', 'B-'),
    ('AB+', 'AB+'),
    ('AB-', 'AB-'),
    ('O+', 'O+'),
    ('O-', 'O-'),
]


class RegistroForm(UserCreationForm):
    email       = forms.EmailField(required=True, label='Correo electrónico')
    nombre      = forms.CharField(max_length=100, label='Nombre')
    apellido    = forms.CharField(max_length=100, label='Apellido')
    cedula      = forms.CharField(max_length=20,  label='Cédula / Documento')
    rol         = forms.ChoiceField(choices=ROL_CHOICES, label='Rol')
    tipo_sangre = forms.ChoiceField(choices=TIPO_SANGRE_CHOICES, required=False, label='Tipo de sangre')
    eps_ips     = forms.CharField(max_length=150, required=False, label='EPS / IPS')

    class Meta:
        model  = User
        fields = ['username', 'email', 'nombre', 'apellido', 'cedula', 'rol', 'tipo_sangre', 'eps_ips', 'password1', 'password2']

    def clean_rol(self):
        rol = self.cleaned_data.get('rol')
        if not rol:
            raise forms.ValidationError('Debes seleccionar un rol.')
        return rol

    def clean(self):
        cleaned_data = super().clean()
        rol = cleaned_data.get('rol')
        if rol == 'cliente_paciente':
            tipo_sangre = cleaned_data.get('tipo_sangre')
            eps_ips = cleaned_data.get('eps_ips')
            if not tipo_sangre:
                self.add_error('tipo_sangre', 'Por favor selecciona tu tipo de sangre.')
            if not eps_ips:
                self.add_error('eps_ips', 'Por favor ingresa tu EPS / IPS.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email      = self.cleaned_data['email']
        user.first_name = self.cleaned_data['nombre']
        user.last_name  = self.cleaned_data['apellido']
        if commit:
            user.save()
        return user


class LoginConRolForm(AuthenticationForm):
    rol = forms.ChoiceField(choices=ROL_CHOICES, label='Rol')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Usuario, correo o cédula'

    def clean_rol(self):
        rol = self.cleaned_data.get('rol')
        if not rol:
            raise forms.ValidationError('Debes seleccionar un rol.')
        return rol
