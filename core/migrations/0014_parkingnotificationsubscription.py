from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0013_remove_parkingrule_title_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ParkingNotificationSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "lot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notification_subscriptions",
                        to="core.parkinglot",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="parking_notification_subscriptions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Suscripción de notificación de parqueadero",
                "verbose_name_plural": "Suscripciones de notificaciones de parqueadero",
            },
        ),
        migrations.AddConstraint(
            model_name="parkingnotificationsubscription",
            constraint=models.UniqueConstraint(
                fields=("user", "lot"), name="unique_notification_subscription"
            ),
        ),
    ]
