from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Authenticates against settings.AUTH_USER_MODEL.
    Allows login with either username or email.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get('username')
            
        try:
            # Check if it's an email
            if '@' in username:
                user = User.objects.get(email=username)
            else:
                user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user.
            User().set_password(password)
            return None
            
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
