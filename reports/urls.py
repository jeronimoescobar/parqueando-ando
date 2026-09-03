from django.urls import path
from . import views

urlpatterns = [
    # Ruta para FR21: Reportar espacio disponible
    path('available/<int:lot_id>/', views.report_available_space, name='report_available'),
    # Ruta para FR22: Reportar espacio ocupado
    path('occupied/<int:lot_id>/', views.report_occupied_space, name='report_occupied'),
    # Ruta para FR30: Reportar información incorrecta
    path('incorrect/<int:lot_id>/', views.report_incorrect_information, name='report_incorrect'),
]
