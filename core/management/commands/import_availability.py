"""
FR19 – Importa la ocupación de los parqueaderos desde una API REST externa.

Uso:
    python manage.py import_availability --url https://api.ejemplo.edu.co/parqueaderos
    python manage.py import_availability          # usa EXTERNAL_PARKING_API_URL

Con el servidor corriendo en desarrollo se puede probar contra el simulador:
    python manage.py import_availability --url http://127.0.0.1:8000/api/simulador/disponibilidad/

Sirve para programarlo (por ejemplo con cron cada 5 minutos) y mantener la
disponibilidad sincronizada sin que nadie tenga que entrar al dashboard.
La lógica está en core/external_api.py; este comando solo la llama.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.external_api import ExternalAPIError, import_from_url


class Command(BaseCommand):
    help = "Importa la disponibilidad de los parqueaderos desde una API REST externa (FR19)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            help="URL de la API. Si no se pasa, se usa la variable EXTERNAL_PARKING_API_URL.",
        )

    def handle(self, *args, **options):
        url = options.get("url") or settings.EXTERNAL_PARKING_API_URL
        if not url:
            raise CommandError(
                "No hay URL: pásala con --url o define la variable de entorno EXTERNAL_PARKING_API_URL."
            )

        self.stdout.write(f"Consultando {url} ...")
        try:
            result = import_from_url(url)
        except ExternalAPIError as exc:
            raise CommandError(str(exc))

        for name in result.updated:
            self.stdout.write(self.style.SUCCESS(f"  ✓ {name}"))
        for name, field, received, applied in result.adjusted:
            self.stdout.write(self.style.WARNING(
                f"  ! {name}: {field}={received} supera la capacidad, se guardó {applied}"
            ))
        for slug, reason in result.skipped:
            self.stdout.write(self.style.WARNING(f"  - Ignorado {slug}: {reason}"))

        self.stdout.write(self.style.SUCCESS(result.summary))
