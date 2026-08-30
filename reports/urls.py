from django.urls import path
from . import views

urlpatterns = [
    # Ruta para FR21: Reportar espacio disponible
    path('available/<int:lot_id>/', views.report_available_space, name='report_available'),
]
