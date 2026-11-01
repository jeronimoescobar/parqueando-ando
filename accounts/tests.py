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


from django.core.cache import cache
from django.test import override_settings
from accounts import throttle


class LoginSecurityTest(TestCase):
    """FR20 – bloqueo por intentos fallidos y backend de login."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='carlos', email='Carlos@Example.com', password='ClaveSegura#2026'
        )
        self.url = reverse('accounts:login')

    def _bad_login(self, username='carlos'):
        return self.client.post(self.url, {'username': username, 'password': 'incorrecta'})

    def test_login_ok_by_username_and_by_email_ignoring_case(self):
        self.assertTrue(self.client.login(username='carlos', password='ClaveSegura#2026'))
        self.client.logout()
        self.assertTrue(self.client.login(username='carlos@example.COM', password='ClaveSegura#2026'))

    def test_wrong_password_does_not_log_in(self):
        response = self._bad_login()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_account_locks_after_max_attempts_even_with_right_password(self):
        for _ in range(throttle.MAX_ATTEMPTS):
            self._bad_login()
        response = self.client.post(self.url, {'username': 'carlos', 'password': 'ClaveSegura#2026'})
        self.assertEqual(response.status_code, 429)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, 'Demasiados intentos', status_code=429)

    def test_lock_is_per_user_so_others_can_still_log_in(self):
        User.objects.create_user(username='ana', email='ana@example.com', password='OtraClave#2026')
        for _ in range(throttle.MAX_ATTEMPTS):
            self._bad_login()
        response = self.client.post(self.url, {'username': 'ana', 'password': 'OtraClave#2026'})
        self.assertEqual(response.status_code, 302)

    def test_successful_login_resets_the_counter(self):
        for _ in range(throttle.MAX_ATTEMPTS - 1):
            self._bad_login()
        response = self.client.post(self.url, {'username': 'carlos', 'password': 'ClaveSegura#2026'})
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        for _ in range(throttle.MAX_ATTEMPTS - 1):
            self._bad_login()
        response = self.client.post(self.url, {'username': 'carlos', 'password': 'ClaveSegura#2026'})
        self.assertEqual(response.status_code, 302)

    def test_login_does_not_redirect_to_external_site(self):
        response = self.client.post(
            self.url + '?next=https://evil.example/',
            {'username': 'carlos', 'password': 'ClaveSegura#2026', 'next': 'https://evil.example/'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response['Location'].startswith('http'))

    def test_duplicate_emails_do_not_crash_login(self):
        User.objects.create_user(username='otro', email='carlos@example.com', password='x' * 12)
        self.assertFalse(self.client.login(username='carlos@example.com', password='ClaveSegura#2026'))
        self.assertTrue(self.client.login(username='carlos', password='ClaveSegura#2026'))

    def test_password_needs_at_least_10_characters(self):
        form = CustomUserCreationForm(data={
            'username': 'nuevo', 'email': 'nuevo@example.com',
            'password1': 'Corta#12', 'password2': 'Corta#12',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_session_cookie_is_httponly(self):
        self.client.post(self.url, {'username': 'carlos', 'password': 'ClaveSegura#2026'})
        from django.conf import settings
        self.assertTrue(self.client.cookies[settings.SESSION_COOKIE_NAME]['httponly'])
