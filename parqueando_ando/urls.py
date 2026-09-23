"""
URL configuration for parqueando_ando project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.auth_views import UserLoginView, UserLogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    # FR2 – Login/logout para TODOS los usuarios (no solo staff). Van antes
    # del include de abajo para reemplazar las vistas de Django por las
    # nuestras (ver core/auth_views.py); el resto de rutas de
    # django.contrib.auth.urls (cambio/recuperación de contraseña) siguen
    # disponibles igual.
    path('accounts/login/', UserLoginView.as_view(), name='login'),
    path('accounts/logout/', UserLogoutView.as_view(), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('core.urls')),
    path('reports/', include('reports.urls')),
    # Dashboard + mapeador visual de espacios (toda la funcionalidad de
    # administrador agrupada en la app `administration`).
    path('dashboard/', include('administration.urls')),
]

if settings.DEBUG:
    # Sirve las imágenes de los planos (layout_image) en desarrollo.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
