from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

UserModel = get_user_model()


class UsernameEmailCedulaBackend(ModelBackend):
    """Permite iniciar sesión con username, correo o cédula en el mismo campo."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        user = UserModel.objects.filter(
            Q(username__iexact=username) | Q(email__iexact=username)
        ).first()

        if user is None:
            from pulse_sas.internal.pulse_sas.personas.models import Persona

            persona = Persona.objects.select_related('usuario').filter(cedula=username).first()
            user = persona.usuario if persona else None

        if user is None:
            # Ejecutar el hash igual que en el caso exitoso, para no filtrar
            # por tiempo de respuesta si el identificador existe o no.
            UserModel().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
