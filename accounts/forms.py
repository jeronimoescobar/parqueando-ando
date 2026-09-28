from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Correo electrónico")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email


class ProfileUpdateForm(forms.ModelForm):
    """FR3 – Permite al usuario actualizar los datos básicos de su perfil."""

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
            "username": forms.TextInput(attrs={"class": "form-control", "autocomplete": "username"}),
            "first_name": forms.TextInput(attrs={"class": "form-control", "autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email
