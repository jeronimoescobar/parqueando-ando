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

urlpatterns = [
    path('admin/', admin.site.urls),
    # Login/logout para el administrador (usados por FR16 - dashboard)
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('core.urls')),
    path('reports/', include('reports.urls')),
    # Dashboard + mapeador visual de espacios (toda la funcionalidad de
    # administrador agrupada en la app `adminpanel`).
    path('dashboard/', include('adminpanel.urls')),
]

if settings.DEBUG:
    # Sirve las imágenes de los planos (layout_image) en desarrollo.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
