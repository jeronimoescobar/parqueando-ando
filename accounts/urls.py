from django.urls import path, include
from .views import UserLoginView, UserLogoutView, UserRegisterView, profile, change_password

app_name = 'accounts'

urlpatterns = [
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('register/', UserRegisterView.as_view(), name='register'),
    path('profile/', profile, name='profile'),
    path('profile/password/', change_password, name='change_password'),
    path('', include('django.contrib.auth.urls')),
]
