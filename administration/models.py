from django.db import models
from django.contrib.auth.models import User
from django.conf import settings


class AdminActionLog(models.Model):
    """Registro legible de cambios administrativos relevantes."""
    ACTION_CHOICES = [("parking_lot_update", "Actualización de parqueadero"), ("parking_lot_create", "Creación de parqueadero"), ("report_status", "Validación de reporte"), ("report_delete", "Eliminación de reporte"), ("report_bulk_delete", "Eliminación masiva de reportes inválidos")]
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="admin_action_logs")
    action = models.CharField(max_length=80, choices=ACTION_CHOICES)
    target = models.CharField(max_length=160)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Acción administrativa"
        verbose_name_plural = "Registro de acciones administrativas"

    def __str__(self):
        return f"{self.get_action_display() if hasattr(self, 'get_action_display') else self.action}: {self.target}"

class ContactMessage(models.Model):
    """
    Mensajes de contacto enviados por los usuarios a la administración (FR36).
    """
    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('resolved', 'Resuelto'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contact_messages')
    subject = models.CharField(max_length=200, verbose_name="Asunto")
    message = models.TextField(verbose_name="Mensaje")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Estado")

    def __str__(self):
        return f"{self.subject} - {self.user.username}"
