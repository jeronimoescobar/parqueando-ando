from django.db import models
from django.contrib.auth.models import User

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
