"""
FR19 – Importar la disponibilidad de los parqueaderos desde una API REST externa.

La idea: en vez de depender solo de lo que reportan los usuarios, el
sistema puede traer la ocupación desde otro sistema (por ejemplo, los
sensores o las barreras de entrada de EAFIT) que la publique como JSON
por HTTP. Este archivo es el único que sabe hablar con esa API; la vista
del dashboard y el comando `python manage.py import_availability` solo
lo llaman.

Formato que se espera de la API (GET, respuesta JSON):

    {
      "parkings": [
        {"slug": "parqueadero-norte",
         "occupied_cars": 120, "occupied_motorcycles": 30, "occupied_accessibility": 2},
        ...
      ]
    }

  - También se acepta la lista sola ([...]) o la clave "lots".
  - `slug` identifica el parqueadero (el mismo de /parking/<slug>/).
  - Los tres campos `occupied_*` son opcionales: el que no venga no se toca.

Reglas al aplicar los datos (nunca se confía ciegamente en la API):
  - Un parqueadero que no existe aquí se ignora y se reporta.
  - Un valor que no es entero o es negativo se rechaza (todo ese parqueadero).
  - Un valor mayor que la capacidad se ajusta a la capacidad y se avisa.
  - Todo se guarda en una sola transacción: o se aplica todo lo válido, o nada.

Si no hay una API real disponible (como en desarrollo), el proyecto trae
un simulador en /api/simulador/disponibilidad/ que responde con este mismo
formato — ver core.views.external_api_simulator.
"""

from dataclasses import dataclass, field

import requests
from django.db import transaction
from django.utils import timezone

from .models import ParkingLot

REQUEST_TIMEOUT = 8  # segundos
USER_AGENT = "ParqueandoAndo/1.0 (+FR19 importador)"

# Campo que llega en el JSON -> (campo de ocupación, campo de capacidad)
OCCUPANCY_FIELDS = {
    "occupied_cars": "capacity_cars",
    "occupied_motorcycles": "capacity_motorcycles",
    "occupied_accessibility": "capacity_accessibility",
}


class ExternalAPIError(Exception):
    """Error al consultar o entender la API externa (mensaje listo para mostrar)."""


@dataclass
class ImportResult:
    source: str = ""
    updated: list = field(default_factory=list)   # nombres de parqueaderos actualizados
    skipped: list = field(default_factory=list)   # (slug, motivo)
    adjusted: list = field(default_factory=list)  # (nombre, campo, recibido, aplicado)

    @property
    def summary(self):
        parts = [f"{len(self.updated)} parqueadero(s) actualizado(s)"]
        if self.adjusted:
            parts.append(f"{len(self.adjusted)} valor(es) ajustado(s) a la capacidad")
        if self.skipped:
            parts.append(f"{len(self.skipped)} registro(s) ignorado(s)")
        return ", ".join(parts) + "."


def fetch_payload(url, timeout=REQUEST_TIMEOUT):
    """Hace el GET a la API y devuelve el JSON ya convertido a Python."""
    try:
        response = requests.get(
            url,
            headers={"Accept": "application/json", "User-Agent": USER_AGENT},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.Timeout:
        raise ExternalAPIError(f"La API externa no respondió a tiempo (más de {timeout}s).")
    except requests.ConnectionError:
        raise ExternalAPIError("No se pudo conectar con la API externa. Revisa la URL o la conexión.")
    except requests.HTTPError as exc:
        raise ExternalAPIError(f"La API externa respondió con error HTTP {exc.response.status_code}.")
    except requests.RequestException as exc:
        raise ExternalAPIError(f"No se pudo consultar la API externa: {exc}")

    try:
        return response.json()
    except ValueError:
        raise ExternalAPIError("La API externa no respondió con JSON válido.")


def extract_entries(payload):
    """Saca la lista de parqueaderos del JSON, venga como venga envuelta."""
    if isinstance(payload, dict):
        payload = payload.get("parkings", payload.get("lots"))
    if not isinstance(payload, list):
        raise ExternalAPIError(
            'El JSON no tiene el formato esperado: debe ser una lista o tener la clave "parkings".'
        )
    return payload


def _as_count(value):
    """Entero >= 0, o None si el valor no sirve (texto, decimal, negativo, booleano)."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


@transaction.atomic
def apply_entries(entries, source=""):
    """Aplica la ocupación recibida a los ParkingLot. Devuelve un ImportResult."""
    result = ImportResult(source=source)
    lots_by_slug = {lot.slug: lot for lot in ParkingLot.objects.select_for_update()}

    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("slug"):
            result.skipped.append(("?", "registro sin 'slug'"))
            continue

        slug = str(entry["slug"])
        lot = lots_by_slug.get(slug)
        if lot is None:
            result.skipped.append((slug, "no existe ese parqueadero"))
            continue

        changes = {}
        invalid_field = None
        for occupied_field, capacity_field in OCCUPANCY_FIELDS.items():
            if occupied_field not in entry:
                continue
            value = _as_count(entry[occupied_field])
            if value is None:
                invalid_field = occupied_field
                break
            capacity = getattr(lot, capacity_field)
            if value > capacity:
                result.adjusted.append((lot.name, occupied_field, value, capacity))
                value = capacity
            changes[occupied_field] = value

        if invalid_field:
            result.skipped.append((slug, f"'{invalid_field}' no es un entero >= 0"))
            continue
        if not changes:
            result.skipped.append((slug, "no trae datos de ocupación"))
            continue

        # update() en vez de save(): escribe solo estos campos, sin pisar
        # otros cambios que estén ocurriendo al mismo tiempo.
        ParkingLot.objects.filter(pk=lot.pk).update(last_updated=timezone.now(), **changes)
        result.updated.append(lot.name)

    return result


def import_from_url(url, timeout=REQUEST_TIMEOUT):
    """Todo el flujo: consultar la API, validar el JSON y guardar la ocupación."""
    payload = fetch_payload(url, timeout=timeout)
    return apply_entries(extract_entries(payload), source=url)
