from django.urls import path

from . import views

urlpatterns = [
    # FR5, FR6, FR7, FR28, FR8, FR9, FR10, FR37
    path("", views.home, name="home"),

    # Estado del Metro (scraping cacheado) — usado por home.html (polling cada 5 min)
    path("metro-status/", views.metro_status_api, name="metro_status_api"),

    # FR26, FR27 — detalle de parqueadero + plano interactivo (Sprint 2)
    path("parking/<slug:slug>/", views.parking_detail, name="parking_detail"),
    path(
        "parking/<slug:slug>/spots/<int:spot_id>/status/",
        views.update_spot_status,
        name="update_spot_status",
    ),
]

# La funcionalidad de administrador (dashboard, mapeador visual) vive en
# la app `adminpanel` (ver parqueando_ando/urls.py -> include('adminpanel.urls')).
