"""
Sprint 3:
  - Coordenadas por parqueadero (antes estaban escritas a mano en home.html,
    así que el mapa no podía reflejar la base de datos).
  - Alias de búsqueda, para que el buscador entienda como le dice la gente
    a cada parqueadero sin tener que escribir el nombre exacto.
  - Modelo de favoritos, ya preparado para usuarios/login.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


# Coordenadas que ya venían fijas en el template del home; ahora pasan a
# la base de datos. Los alias son un punto de partida razonable: el
# administrador puede ajustarlos desde /admin/ cuando quiera, sin tocar código.
LOT_SEED = {
    "parqueadero-norte": {
        "latitude": "6.2018070",
        "longitude": "-75.5777196",
        "search_aliases": "norte, el de arriba, parqueadero de ingenieria, ingenieria, el del norte",
    },
    "parqueadero-sur": {
        "latitude": "6.1977715",
        "longitude": "-75.5788944",
        "search_aliases": "sur, el de abajo, el del sur, parqueadero principal",
    },
    "parque-los-guayabos": {
        "latitude": "6.2016866",
        "longitude": "-75.5762165",
        "search_aliases": "guayabos, los guayabos, el parque, parque de los guayabos, el del parque",
    },
    "parqueadero-de-empleados": {
        "latitude": "6.1996218",
        "longitude": "-75.5779220",
        "search_aliases": "empleados, profesores, el de los profes, administrativos, el de empleados",
    },
}


def seed_locations_and_aliases(apps, schema_editor):
    """
    Rellena coordenadas y alias de los 4 parqueaderos fijos.

    Solo toca los que reconoce por slug y solo si el campo está vacío,
    así que es seguro si alguien ya los ajustó a mano antes de correr esto.
    """
    ParkingLot = apps.get_model("core", "ParkingLot")
    for slug, data in LOT_SEED.items():
        lot = ParkingLot.objects.filter(slug=slug).first()
        if lot is None:
            continue
        changed = []
        if lot.latitude is None:
            lot.latitude = data["latitude"]
            changed.append("latitude")
        if lot.longitude is None:
            lot.longitude = data["longitude"]
            changed.append("longitude")
        if not lot.search_aliases:
            lot.search_aliases = data["search_aliases"]
            changed.append("search_aliases")
        if changed:
            lot.save(update_fields=changed)


def unseed(apps, schema_editor):
    """Nada que deshacer: los campos se van con el RemoveField de abajo."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_parkinglotnotice"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="parkinglot",
            name="latitude",
            field=models.DecimalField(
                blank=True, decimal_places=7, max_digits=10, null=True,
                help_text="Ej: 6.2018070. Si se deja vacío, el parqueadero no sale en el mapa.",
                verbose_name="Latitud",
            ),
        ),
        migrations.AddField(
            model_name="parkinglot",
            name="longitude",
            field=models.DecimalField(
                blank=True, decimal_places=7, max_digits=10, null=True,
                help_text="Ej: -75.5777196. Si se deja vacío, el parqueadero no sale en el mapa.",
                verbose_name="Longitud",
            ),
        ),
        migrations.AddField(
            model_name="parkinglot",
            name="search_aliases",
            field=models.TextField(
                blank=True, default="",
                help_text=(
                    "Nombres alternativos separados por coma, para que la búsqueda "
                    "los reconozca. Ej: 'norte, el de ingeniería, parqueadero de ing, "
                    "el de arriba'. No hace falta repetir el nombre oficial."
                ),
                verbose_name="Otros nombres / como le dice la gente",
            ),
        ),
        migrations.CreateModel(
            name="FavoriteParkingLot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_key", models.CharField(
                    blank=True, db_index=True, default="", max_length=40,
                    help_text=(
                        "Sesión del navegador, para recordar favoritos de visitantes "
                        "sin cuenta. Se limpia cuando el favorito pasa a un usuario."
                    ),
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("lot", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="favorited_by", to="core.parkinglot",
                )),
                ("user", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="favorite_parking_lots",
                    to=settings.AUTH_USER_MODEL,
                    help_text="Queda vacío mientras la persona no haya iniciado sesión.",
                )),
            ],
            options={
                "verbose_name": "Parqueadero favorito",
                "verbose_name_plural": "Parqueaderos favoritos",
            },
        ),
        migrations.AddConstraint(
            model_name="favoriteparkinglot",
            constraint=models.UniqueConstraint(
                condition=models.Q(("user__isnull", False)),
                fields=("user", "lot"),
                name="unique_favorite_per_user",
            ),
        ),
        migrations.AddConstraint(
            model_name="favoriteparkinglot",
            constraint=models.UniqueConstraint(
                condition=models.Q(("user__isnull", True)),
                fields=("session_key", "lot"),
                name="unique_favorite_per_session",
            ),
        ),
        migrations.RunPython(seed_locations_and_aliases, unseed),
    ]
