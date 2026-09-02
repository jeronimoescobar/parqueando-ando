from django.urls import path

from . import views

# Incluido desde parqueando_ando/urls.py como:
#     path("dashboard/", include("adminpanel.urls"))
# así que las rutas de aquí NO llevan el prefijo "dashboard/" — ya lo
# pone el include(). URLs finales resultantes:
#     /dashboard/
#     /dashboard/mapper/<slug>/
#     /dashboard/mapper/<slug>/create/
#     /dashboard/mapper/<slug>/spots/<id>/update/
#     /dashboard/mapper/<slug>/spots/<id>/delete/
urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("mapper/<slug:slug>/", views.spot_mapper, name="spot_mapper"),
    path("mapper/<slug:slug>/create/", views.mapper_create_spot, name="mapper_create_spot"),
    path(
        "mapper/<slug:slug>/spots/<int:spot_id>/update/",
        views.mapper_update_spot,
        name="mapper_update_spot",
    ),
    path(
        "mapper/<slug:slug>/spots/<int:spot_id>/delete/",
        views.mapper_delete_spot,
        name="mapper_delete_spot",
    ),
]
