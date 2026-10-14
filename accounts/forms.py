from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(
        max_length=30,
        label="Nombre de usuario",
        help_text="Requerido. Máximo 30 caracteres. Letras, dígitos y @/./+/-/_ únicamente.",
        widget=forms.TextInput(attrs={"class": "form-control", "maxlength": "30", "autofocus": True}),
    )
    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        help_text="Requerido. Ingresa un correo electrónico válido.",
        widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and len(username) > 30:
            raise forms.ValidationError("El nombre de usuario no puede tener más de 30 caracteres.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("El correo electrónico es obligatorio.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email


class ProfileUpdateForm(forms.ModelForm):
    """FR3 – Permite al usuario actualizar los datos básicos de su perfil."""
    username = forms.CharField(
        max_length=30,
        label="Nombre de usuario",
        help_text="Máximo 30 caracteres.",
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "username", "maxlength": "30"}),
    )
    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")
        labels = {
            "username": "Nombre de usuario",
            "first_name": "Nombres",
            "last_name": "Apellidos",
            "email": "Correo electrónico",
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control", "autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "autocomplete": "family-name"}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and len(username) > 30:
            raise forms.ValidationError("El nombre de usuario no puede tener más de 30 caracteres.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            raise forms.ValidationError("El correo electrónico es obligatorio.")
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email
