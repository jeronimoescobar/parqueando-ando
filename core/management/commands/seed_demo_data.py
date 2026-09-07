"""
Comando de gestión para cargar datos de demostración.

Uso:
    python manage.py seed_demo_data

IMPORTANTE — no crea parqueaderos nuevos: los 4 parqueaderos del campus
son fijos y ya se crean automáticamente al correr `migrate` (ver
core/migrations/0006_seed_fixed_parking_lots.py). Este comando SOLO
actualiza esos mismos 4 (por slug) con capacidades y ocupación variadas
—para que en la demo se vea al menos un parqueadero "Disponible", uno
"Limitado" y uno "Lleno"— y agrega un par de reportes en estado
"Pendiente de revisión" para poder mostrar FR34 (validar reportes) sin
tener que generarlos a mano desde el home primero.

Los slugs de abajo deben coincidir EXACTAMENTE con los de la migración
0006 (parqueadero-norte, parqueadero-sur, parque-los-guayabos,
parqueadero-de-empleados). Si no coinciden, `update_or_create` no
encuentra el parqueadero existente y crea uno nuevo con ese slug
distinto — quedarían 8 parqueaderos en vez de 4 en el home. (Así estaba
antes de este arreglo: usaba slugs cortos como "norte"/"sur" que no
existen en ningún otro lado del proyecto.)

Es seguro correrlo varias veces: usa update_or_create, así que no
duplica los parqueaderos si ya existen (solo actualiza sus datos).
"""

from django.core.management.base import BaseCommand

from core.models import ParkingLot
from reports.models import ParkingReport


class Command(BaseCommand):
    help = "Carga parqueaderos y reportes de ejemplo para la demo/exposición."

    def handle(self, *args, **options):
        lots_data = [
            dict(
                slug="parqueadero-norte",
                name="Parqueadero Norte",
                total_capacity=50,
                capacity_cars=40,
                capacity_motorcycles=8,
                capacity_accessibility=2,
                occupied_cars=10,
                occupied_motorcycles=2,
                occupied_accessibility=0,
            ),  # Disponible
            dict(
                slug="parqueadero-sur",
                name="Parqueadero Sur",
                total_capacity=40,
                capacity_cars=32,
                capacity_motorcycles=6,
                capacity_accessibility=2,
                occupied_cars=25,
                occupied_motorcycles=5,
                occupied_accessibility=1,
            ),  # Limitado (~78%)
            dict(
                slug="parque-los-guayabos",
                name="Parqueadero Parque de los Guayabos",
                total_capacity=30,
                capacity_cars=24,
                capacity_motorcycles=4,
                capacity_accessibility=2,
                occupied_cars=24,
                occupied_motorcycles=4,
                occupied_accessibility=2,
            ),  # Lleno
            dict(
                slug="parqueadero-de-empleados",
                name="Parqueadero de Empleados",
                total_capacity=25,
                capacity_cars=20,
                capacity_motorcycles=3,
                capacity_accessibility=2,
                occupied_cars=8,
                occupied_motorcycles=1,
                occupied_accessibility=0,
            ),  # Disponible
        ]

        created_lots = {}
        for data in lots_data:
            slug = data.pop("slug")
            lot, created = ParkingLot.objects.update_or_create(slug=slug, defaults=data)
            created_lots[slug] = lot
            estado = "creado" if created else "actualizado"
            self.stdout.write(self.style.SUCCESS(f"  OK {lot.name} ({estado})"))

        # Un par de reportes pendientes para poder demostrar FR34 de una.
        reportes_demo = [
            dict(lot=created_lots["parqueadero-norte"], report_type="available", vehicle_type="car"),
            dict(lot=created_lots["parqueadero-sur"], report_type="occupied", vehicle_type="motorcycle"),
        ]
        for data in reportes_demo:
            _, created = ParkingReport.objects.get_or_create(
                lot=data["lot"],
                report_type=data["report_type"],
                vehicle_type=data["vehicle_type"],
                status="pending",
                defaults={},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  OK Reporte pendiente creado en {data['lot'].name}"))

        self.stdout.write(self.style.SUCCESS("\nListo. Ya puedes correr 'python manage.py runserver' y ver datos en /"))
