from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView

# Import the core logic for favorites
from core.favorites import attach_session_favorites_to_user

def log_user_in(request, user):
    """
    Inicia sesión y migra los favoritos anónimos a la cuenta.
    """
    anonymous_session_key = request.session.session_key
    login(request, user)
    attach_session_favorites_to_user(request, user, session_key=anonymous_session_key)


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        log_user_in(self.request, user)

        nombre = user.get_short_name() or user.get_username()
        messages.success(self.request, f"¡Hola, {nombre}! Iniciaste sesión.")
        return HttpResponseRedirect(self.get_success_url())

    def get_default_redirect_url(self):
        if self.request.user.is_staff:
            return reverse("dashboard")
        return reverse("home")


class UserLogoutView(LogoutView):
    next_page = "home"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.info(request, "Cerraste sesión.")
        return response


class UserRegisterView(CreateView):
    form_class = UserCreationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        # Guardar el nuevo usuario en la base de datos
        user = form.save()
        # Iniciar sesión inmediatamente usando la función que migra favoritos
        log_user_in(self.request, user)
        
        messages.success(self.request, f"¡Bienvenido a Parqueando Ando, {user.username}! Tu cuenta ha sido creada.")
        return HttpResponseRedirect(self.get_success_url())
