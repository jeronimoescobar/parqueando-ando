# Sprint 2 — siembra los 4 parqueaderos fijos del campus.
#
# Como el admin ya no permite crear ParkingLot (son fijos, ver
# core.admin.ParkingLotAdmin.has_add_permission), necesitamos una forma de
# que existan en una base de datos nueva/limpia. Esta migración los crea
# automáticamente al correr `python manage.py migrate`.
#
# Usa get_or_create por `slug`, así que es segura de correr aunque ya
# tengas estos 4 parqueaderos creados manualmente desde antes (no duplica).
#
# Los slugs coinciden con los que ya usa core/templates/core/home.html en
# los enlaces de los popups del mapa Leaflet — si cambias el slug de un
# parqueadero aquí, actualiza también esos enlaces en home.html.

from django.db import migrations

LOTS = [
    {
        "name": "Parqueadero Norte",
        "slug": "parqueadero-norte",
        "total_capacity": 60,
        "capacity_cars": 45,
        "capacity_motorcycles": 10,
        "capacity_accessibility": 5,
    },
    {
        "name": "Parqueadero Sur",
        "slug": "parqueadero-sur",
        "total_capacity": 50,
        "capacity_cars": 35,
        "capacity_motorcycles": 10,
        "capacity_accessibility": 5,
    },
    {
        "name": "Parqueadero Parque de los Guayabos",
        "slug": "parque-los-guayabos",
        "total_capacity": 40,
        "capacity_cars": 30,
        "capacity_motorcycles": 8,
        "capacity_accessibility": 2,
    },
    {
        "name": "Parqueadero de Empleados",
        "slug": "parqueadero-de-empleados",
        "total_capacity": 70,
        "capacity_cars": 55,
        "capacity_motorcycles": 10,
        "capacity_accessibility": 5,
    },
]


def create_fixed_lots(apps, schema_editor):
    ParkingLot = apps.get_model("core", "ParkingLot")
    for data in LOTS:
        ParkingLot.objects.get_or_create(slug=data["slug"], defaults=data)


def remove_fixed_lots(apps, schema_editor):
    ParkingLot = apps.get_model("core", "ParkingLot")
    slugs = [data["slug"] for data in LOTS]
    ParkingLot.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_parkingspot_and_layout_image'),
    ]

    operations = [
        migrations.RunPython(create_fixed_lots, remove_fixed_lots),
    ]
