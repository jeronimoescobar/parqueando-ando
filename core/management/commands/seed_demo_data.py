"""
Comando de gestión para cargar datos de demostración.

Uso:
    python manage.py seed_demo_data

Crea los 4 parqueaderos que ya aparecen marcados en el mapa del home
(Norte, Sur, Parque de los Guayabos y Empleados) con capacidades y
ocupación variadas —para que en la demo se vea al menos un parqueadero
"Disponible", uno "Limitado" y uno "Lleno"— y un par de reportes en
estado "Pendiente de revisión" para poder mostrar FR34 (validar
reportes) sin tener que generarlos a mano desde el home primero.

Es seguro correrlo varias veces: usa get_or_create, así que no duplica
los parqueaderos si ya existen (solo actualiza sus datos).
"""

from django.core.management.base import BaseCommand

from core.models import ParkingLot
from reports.models import ParkingReport


class Command(BaseCommand):
    help = "Carga parqueaderos y reportes de ejemplo para la demo/exposición."

    def handle(self, *args, **options):
        lots_data = [
            dict(
                slug="norte",
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
                slug="sur",
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
                slug="guayabos",
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
                slug="empleados",
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
            dict(lot=created_lots["norte"], report_type="available", vehicle_type="car"),
            dict(lot=created_lots["sur"], report_type="occupied", vehicle_type="motorcycle"),
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
