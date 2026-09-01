from django.db import models
from core.models import ParkingLot

class ParkingReport(models.Model):
    """
    Modelo para gestionar los reportes de los usuarios (Componente REPORTS AND INFORMATION).
    Satisface: FR21, FR22, FR30, FR32, FR34.
    """
    REPORT_TYPES = [
        ('available', 'Espacio Disponible (FR21)'),
        ('occupied', 'Espacio Ocupado (FR22)'),
        ('incorrect', 'Información Incorrecta (FR30)'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pendiente de revisión'),
        ('valid', 'Validado (FR34)'),
        ('invalid', 'Inválido/Eliminado (FR32)'),
    ]

    VEHICLE_TYPES = [
        ('car', 'Carro'),
        ('motorcycle', 'Moto'),
        ('accessibility', 'PMR'),
        ('general', 'No especificado')
    ]

    lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name='reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES, default='general')
    description = models.TextField(blank=True, null=True, help_text="Detalle opcional (FR30)")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.get_report_type_display()} en {self.lot.name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
