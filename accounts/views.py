from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import LoginView, LogoutView
from .forms import CustomUserCreationForm, ProfileUpdateForm
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView

from . import throttle

# Import the core logic for favorites
from core.favorites import attach_session_favorites_to_user

def log_user_in(request, user):
    """
    Inicia sesión y migra los favoritos anónimos a la cuenta.
    """
    anonymous_session_key = request.session.session_key
    backend = getattr(user, 'backend', None) or 'accounts.backends.EmailOrUsernameModelBackend'
    login(request, user, backend=backend)
    attach_session_favorites_to_user(request, user, session_key=anonymous_session_key)


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        # FR20 – Si esta combinación usuario+IP ya agotó sus intentos, ni
        # siquiera se revisa la contraseña (así no sirve para seguir adivinando).
        identifier = request.POST.get("username", "")
        if throttle.is_locked(request, identifier):
            form = self.get_form()
            messages.error(
                request,
                f"Demasiados intentos fallidos. Espera {throttle.lockout_minutes()} minutos "
                "e inténtalo de nuevo.",
            )
            return self.render_to_response(self.get_context_data(form=form), status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        identifier = self.request.POST.get("username", "")
        failures = throttle.register_failure(self.request, identifier)
        if failures >= throttle.MAX_ATTEMPTS:
            messages.error(
                self.request,
                f"Demasiados intentos fallidos. Espera {throttle.lockout_minutes()} minutos "
                "e inténtalo de nuevo.",
            )
        return super().form_invalid(form)

    def form_valid(self, form):
        user = form.get_user()
        throttle.reset(self.request, self.request.POST.get("username", ""))
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
    form_class = CustomUserCreationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        # Guardar el nuevo usuario en la base de datos
        self.object = form.save()
        # Iniciar sesión inmediatamente usando la función que migra favoritos
        log_user_in(self.request, self.object)
        
        messages.success(self.request, f"¡Bienvenido a Parqueando Ando, {self.object.username}! Tu cuenta ha sido creada.")
        return HttpResponseRedirect(self.get_success_url())


@login_required
def profile(request):
    """FR3 – Visualizar y actualizar el perfil del usuario."""
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Tu perfil se actualizó correctamente.")
            return HttpResponseRedirect(reverse("accounts:profile"))
    else:
        form = ProfileUpdateForm(instance=request.user)

    password_form = PasswordChangeForm(request.user)
    return render_profile(request, form, password_form)


@login_required
def change_password(request):
    """FR3 – Cambiar la contraseña sin cerrar la sesión actual."""
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Tu contraseña se cambió correctamente.")
            return HttpResponseRedirect(reverse("accounts:profile"))
    else:
        form = PasswordChangeForm(request.user)

    profile_form = ProfileUpdateForm(instance=request.user)
    return render_profile(request, profile_form, form)


def render_profile(request, form, password_form):
    from django.shortcuts import render
    return render(request, "accounts/profile.html", {
        "form": form,
        "password_form": password_form,
    })
