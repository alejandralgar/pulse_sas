from django import forms
from django.contrib.auth.forms import AuthenticationForm

# Roles disponibles para login (selector de rol activo)
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
