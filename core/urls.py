from django.urls import path

from . import views

urlpatterns = [
    # FR5, FR6, FR7, FR28, FR8, FR9, FR10, FR37
    path("", views.home, name="home"),

    # FR26, FR27 — detalle de parqueadero (Sprint 2)
    path("parking/<slug:slug>/", views.parking_detail, name="parking_detail"),
]
