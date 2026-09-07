from django.urls import path
from . import views

urlpatterns = [
    # FR21 – Report available parking space
    path('available/<int:lot_id>/', views.report_available_space, name='report_available'),
    # FR22 – Report occupied parking space
    path('occupied/<int:lot_id>/', views.report_occupied_space, name='report_occupied'),
    # FR30 – Report incorrect parking information
    path('incorrect/<int:lot_id>/', views.report_incorrect_information, name='report_incorrect'),
]
