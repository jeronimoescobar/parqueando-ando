from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.forms import CustomUserCreationForm, ProfileUpdateForm

class AccountsFormValidationTest(TestCase):
    def test_username_max_length_30_valid(self):
        form = CustomUserCreationForm(data={
            'username': 'user_exact_30_characters_1234',  # 30 chars
            'email': 'valid30@example.com',
            'password1': 'StrongP@ss12345!',
            'password2': 'StrongP@ss12345!',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_username_exceeding_30_chars_invalid(self):
        form = CustomUserCreationForm(data={
            'username': 'user_exceeding_31_characters_long',  # 33 chars
            'email': 'invalid31@example.com',
            'password1': 'StrongP@ss12345!',
            'password2': 'StrongP@ss12345!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_email_required_in_registration(self):
        form = CustomUserCreationForm(data={
            'username': 'validuser',
            'email': '',
            'password1': 'StrongP@ss12345!',
            'password2': 'StrongP@ss12345!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_duplicate_email_invalid(self):
        User.objects.create_user(username='existinguser', email='duplicate@example.com', password='password123')
        form = CustomUserCreationForm(data={
            'username': 'newuser',
            'email': 'duplicate@example.com',
            'password1': 'StrongP@ss12345!',
            'password2': 'StrongP@ss12345!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_profile_update_username_limit_and_required_email(self):
        user = User.objects.create_user(username='testprofile', email='profile@example.com', password='password123')
        
        # Username too long
        form_long_user = ProfileUpdateForm(data={
            'username': 'a' * 31,
            'email': 'profile@example.com',
        }, instance=user)
        self.assertFalse(form_long_user.is_valid())
        self.assertIn('username', form_long_user.errors)

        # Empty email
        form_no_email = ProfileUpdateForm(data={
            'username': 'testprofile',
            'email': '',
        }, instance=user)
        self.assertFalse(form_no_email.is_valid())
        self.assertIn('email', form_no_email.errors)
