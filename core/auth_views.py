"""
Inicio y cierre de sesión (FR2 – User login).

Se usa el sistema de autenticación que ya trae Django (modelo User,
contraseñas con hash, sesiones), con dos ajustes propios:

1. A dónde te manda después de entrar:
     - si venías de una página protegida (?next=...), vuelves a ella;
     - si eres staff, al dashboard de administrador;
     - si eres usuario normal, al home.
   Antes `LOGIN_REDIRECT_URL = 'dashboard'` mandaba a TODO el mundo al
   dashboard, y un estudiante (no staff) se topaba con una página que no
   puede ver.

2. Los favoritos que marcaste ANTES de iniciar sesión (guardados por
   sesión del navegador) pasan a tu cuenta — ver core/favorites.py.

Este login NO depende del registro (FR1): funciona con cualquier usuario
que exista en la base de datos, venga de donde venga (formulario de
registro, /admin/, createsuperuser...).

PARA QUIEN IMPLEMENTE EL REGISTRO: si quieres que la persona quede ya
logueada al terminar de registrarse, usa `log_user_in(request, user)` en
vez de `login(request, user)` — así también se le pasan los favoritos.
"""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseRedirect
from django.urls import reverse

from .favorites import attach_session_favorites_to_user


def log_user_in(request, user):
    """
    Inicia sesión y migra los favoritos anónimos a la cuenta.

    Ojo con el orden: al iniciar sesión Django CAMBIA la clave de la
    sesión (por seguridad, contra "session fixation"). Por eso leemos la
    clave vieja ANTES de login() y se la pasamos a la migración; si la
    leyéramos después, ya sería la nueva y no encontraría los favoritos.
    """
    anonymous_session_key = request.session.session_key
    login(request, user)
    attach_session_favorites_to_user(request, user, session_key=anonymous_session_key)


class UserLoginView(LoginView):
    template_name = "registration/login.html"
    # Si ya iniciaste sesión y vuelves a /accounts/login/, te redirige en
    # vez de mostrarte el formulario otra vez.
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        log_user_in(self.request, user)

        nombre = user.get_short_name() or user.get_username()
        messages.success(self.request, f"¡Hola, {nombre}! Iniciaste sesión.")
        return HttpResponseRedirect(self.get_success_url())

    def get_default_redirect_url(self):
        """Solo se usa cuando no vino un ?next= válido."""
        if self.request.user.is_staff:
            return reverse("dashboard")
        return reverse("home")


class UserLogoutView(LogoutView):
    """Cierra sesión (solo por POST, como exige Django) y vuelve al home."""

    next_page = "home"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.info(request, "Cerraste sesión.")
        return response
