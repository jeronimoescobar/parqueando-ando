from django.db import migrations, models


PARKING_LOT_CAPACITIES = {
    "parqueadero-de-empleados": {
        "capacity_cars": 103,
        "capacity_motorcycles": 4,
        "capacity_accessibility": 3,
    },
    "parqueadero-norte": {
        "capacity_cars": 427,
        "capacity_motorcycles": 0,
        "capacity_accessibility": 8,
    },
    "parqueadero-sur": {
        "capacity_cars": 182,
        "capacity_motorcycles": 328,
        "capacity_accessibility": 4,
    },
    "parque-los-guayabos": {
        "capacity_cars": 252,
        "capacity_motorcycles": 120,
        "capacity_accessibility": 4,
    },
}


def populate_vehicle_capacities(apps, schema_editor):
    ParkingLot = apps.get_model("core", "ParkingLot")
    for slug, capacities in PARKING_LOT_CAPACITIES.items():
        ParkingLot.objects.filter(slug=slug).update(**capacities)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="parkinglot",
            name="capacity_cars",
            field=models.PositiveIntegerField(default=0, verbose_name="Celdas para carros"),
        ),
        migrations.AddField(
            model_name="parkinglot",
            name="capacity_motorcycles",
            field=models.PositiveIntegerField(default=0, verbose_name="Celdas para motos"),
        ),
        migrations.AddField(
            model_name="parkinglot",
            name="capacity_accessibility",
            field=models.PositiveIntegerField(
                default=0,
                verbose_name="Celdas para personas con movilidad reducida (PMR)",
            ),
        ),
        migrations.RunPython(populate_vehicle_capacities, migrations.RunPython.noop),
    ]
