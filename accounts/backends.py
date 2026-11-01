from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Autentica con usuario o con correo electrónico (FR2/FR20).

    - El correo se compara sin importar mayúsculas/minúsculas.
    - Si por datos viejos hay dos cuentas con el mismo correo, no se adivina
      cuál es: el login por correo falla (se puede entrar con el usuario).
    - Siempre se ejecuta un hash de contraseña, exista o no la cuenta, para
      que el tiempo de respuesta no delate qué usuarios existen.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None

        try:
            if "@" in username:
                user = User.objects.get(email__iexact=username)
            else:
                user = User.objects.get(**{User.USERNAME_FIELD: username})
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            User().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
