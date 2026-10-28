from django.db import models
from django.conf import settings
from core.models import ParkingLot

class ParkingReport(models.Model):
    """
    Modelo para gestionar los reportes de los usuarios (Componente REPORTS AND INFORMATION).
    Satisface: FR21, FR22, FR30, FR31, FR32, FR34.
    """
    REPORT_TYPES = [
        ('available', 'Espacio disponible'),
        ('occupied', 'Espacio ocupado'),
        ('incorrect', 'Información incorrecta'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pendiente de revisión'),
        ('valid', 'Validado'),
        ('invalid', 'Inválido / Rechazado'),
    ]

    VEHICLE_TYPES = [
        ('car', 'Carro'),
        ('motorcycle', 'Moto'),
        ('accessibility', 'PMR'),
        ('general', 'No especificado')
    ]

    lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name='reports')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parking_reports',
        verbose_name="Usuario"
    )
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES, default='general')
    description = models.TextField(blank=True, null=True, help_text="Detalle opcional del reporte")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        user_str = f" por {self.user.username}" if self.user else ""
        return f"{self.get_report_type_display()} en {self.lot.name}{user_str} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
