from django import forms

from .models import Cita


HORAS_DISPONIBLES = [
    ('', 'Seleccionar hora...'),
    ('07:00', '07:00 AM'),
    ('08:00', '08:00 AM'),
    ('09:00', '09:00 AM'),
    ('10:00', '10:00 AM'),
    ('11:00', '11:00 AM'),
    ('14:00', '02:00 PM'),
    ('15:00', '03:00 PM'),
    ('16:00', '04:00 PM'),
    ('17:00', '05:00 PM'),
]


class SolicitarCitaForm(forms.Form):
    tipo_cita = forms.ChoiceField(
        choices=[('', 'Seleccionar...')] + list(Cita.TipoCita.choices),
        label='Tipo de cita',
    )
    fecha = forms.DateField(
        label='Fecha',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    hora = forms.ChoiceField(
        choices=HORAS_DISPONIBLES,
        label='Hora disponible',
    )
    motivo = forms.CharField(
        label='Motivo / Síntomas',
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Describe brevemente el motivo de la cita...',
        }),
        max_length=200,
    )

    def clean_tipo_cita(self):
        val = self.cleaned_data.get('tipo_cita')
        if not val:
            raise forms.ValidationError('Selecciona un tipo de cita.')
        return val

    def clean_hora(self):
        val = self.cleaned_data.get('hora')
        if not val:
            raise forms.ValidationError('Selecciona una hora.')
        return val
