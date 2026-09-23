from django.urls import path

from . import views

urlpatterns = [
    # FR5, FR6, FR7, FR28, FR8, FR9, FR10, FR37
    path("", views.home, name="home"),

    # FR35 — información general de los parqueaderos (horarios, tarifas, normas...)
    path("informacion/", views.parking_info_view, name="parking_info"),

    # ── APIs JSON que mantienen la página viva sin recargarla (Sprint 3) ──
    # El home consulta estas rutas con fetch cada cierto tiempo y repinta
    # solo lo que cambió, para que la persona no pierda el scroll.
    path("api/lots/", views.lots_state_api, name="lots_state_api"),
    path("api/search/", views.search_api, name="search_api"),
    path("api/favorites/<int:lot_id>/toggle/", views.toggle_favorite_api, name="toggle_favorite_api"),

    # Estado del Metro (caché + refresco en segundo plano)
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
# la app `administration` (ver parqueando_ando/urls.py -> include('administration.urls')).
