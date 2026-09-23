"""
Filtro de parqueaderos por disponibilidad (FR12).

Dos filtros que se combinan:
    - estado:   available | limited | full   (el mismo de FR6)
    - vehiculo: car | motorcycle | accessibility
                → "que tenga al menos un cupo libre para ese tipo"

Vive en su propio archivo (como search.py o waiting_time.py) porque lo
usan dos lugares y deben dar SIEMPRE el mismo resultado:

  * el home, que lo aplica al renderizar (así el filtro funciona aunque
    el navegador no tenga JavaScript, y un link con ?estado=available
    llega ya filtrado);
  * la API /api/lots/?estado=...&vehiculo=..., por si otro cliente la usa.

En el navegador el filtro se aplica al instante con JavaScript (sin
recargar), usando exactamente las mismas reglas que `lot_matches`.
"""

STATUS_OPTIONS = [
    ("available", "Disponible"),
    ("limited", "Limitado"),
    ("full", "Lleno"),
]

VEHICLE_OPTIONS = [
    ("car", "Carro", "🚗"),
    ("motorcycle", "Moto", "🏍️"),
    ("accessibility", "PMR", "♿"),
]

_VALID_STATUSES = {value for value, _ in STATUS_OPTIONS}
_VALID_VEHICLES = {value for value, _, _ in VEHICLE_OPTIONS}

_AVAILABLE_BY_VEHICLE = {
    "car": lambda lot: lot.available_cars,
    "motorcycle": lambda lot: lot.available_motorcycles,
    "accessibility": lambda lot: lot.available_accessibility,
}


def parse_filters(params):
    """
    Lee ?estado= y ?vehiculo= de un QueryDict (request.GET). Cualquier
    valor desconocido se ignora (queda en None = "sin filtro"), así un
    link viejo o mal escrito nunca rompe la página.
    """
    status = params.get("estado") or None
    vehicle = params.get("vehiculo") or None
    return {
        "status": status if status in _VALID_STATUSES else None,
        "vehicle": vehicle if vehicle in _VALID_VEHICLES else None,
    }


def lot_matches(lot, status=None, vehicle=None):
    """¿Este parqueadero pasa los filtros? Sin filtros, todos pasan."""
    if status and lot.occupancy_status != status:
        return False
    if vehicle and _AVAILABLE_BY_VEHICLE[vehicle](lot) <= 0:
        return False
    return True


def filter_parking_lots(lots, status=None, vehicle=None):
    """Lista de los parqueaderos que pasan los filtros, en el mismo orden."""
    return [lot for lot in lots if lot_matches(lot, status, vehicle)]


def status_counts(lots):
    """Cuántos parqueaderos hay en cada estado (para los números de los botones)."""
    counts = {value: 0 for value, _ in STATUS_OPTIONS}
    for lot in lots:
        counts[lot.occupancy_status] += 1
    return counts
