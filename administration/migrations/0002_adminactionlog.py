from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ("administration", "0001_initial")]
    operations = [migrations.CreateModel(
        name="AdminActionLog",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("action", models.CharField(choices=[("parking_lot_update", "Actualización de parqueadero"), ("parking_lot_create", "Creación de parqueadero"), ("report_status", "Validación de reporte"), ("report_delete", "Eliminación de reporte"), ("report_bulk_delete", "Eliminación masiva de reportes inválidos")], max_length=80)),
            ("target", models.CharField(max_length=160)),
            ("details", models.JSONField(blank=True, default=dict)),
            ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="admin_action_logs", to=settings.AUTH_USER_MODEL)),
        ],
        options={"verbose_name": "Acción administrativa", "verbose_name_plural": "Registro de acciones administrativas", "ordering": ["-created_at"]},
    )]
