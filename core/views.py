"""
Vistas de la app core.

Cada vista indica explícitamente los Functional Requirements (FR) que satisface.

Sprint 1 (completado):
    home()           → FR5, FR6, FR7, FR28, FR8, FR9, FR10, FR37

Sprint 2 (pendiente):
    parking_detail() → FR26, FR27
"""

from django.shortcuts import get_object_or_404, render

from .models import ParkingLot
from .transport_links import TRANSPORT_LINKS
from .waiting_time import estimate_waiting_time


# ── Sprint 1 ───────────────────────────────────────────────────────────────────


def home(request):
    """
    Página principal del sistema.

    FR5  – Display university parking lots:
           Recupera y muestra todos los parqueaderos registrados.
    FR6  – Display available parking spaces:
           Cada tarjeta muestra el estado cualitativo de disponibilidad.
    FR7  – Display parking occupancy status:
           Muestra la insignia de estado (Disponible / Limitado / Lleno).
    FR28 – Parking full message:
           Muestra un aviso explícito cuando el parqueadero está lleno.
    FR8  – Display parking lot map:
           El template renderiza el mapa Leaflet con los marcadores.
    FR9  – Recommend parking lot:
           El tiempo de espera sirve de guía para recomendar el parqueadero
           más conveniente al usuario.
    FR10 – Display estimated waiting time:
           Incluye el tiempo estimado de espera por parqueadero usando
           la lógica de `waiting_time.py`.
    FR37 – External transportation links:
           Incluye los enlaces a Uber, DiDi e InDrive cuando el
           parqueadero está lleno.
    """
    parking_lots = []
    for lot in ParkingLot.objects.all():
        parking_lots.append({
            "lot": lot,
            "waiting_time": estimate_waiting_time(lot),
        })

    context = {
        "parking_lots": parking_lots,
        "transport_links": TRANSPORT_LINKS,
    }
    return render(request, "core/home.html", context)


# ── Sprint 2 ───────────────────────────────────────────────────────────────────


def parking_detail(request, slug):
    """
    Vista de detalle de un parqueadero individual.

    FR26 – Display parking capacity:
           Muestra el desglose de capacidad por tipo de vehículo
           (carros, motos, personas con movilidad reducida — PMR).
    FR27 – Parking lot details:
           Muestra toda la información del parqueadero: nombre, capacidad
           total, desglose por tipo, estado de ocupación y tiempo de espera.

    URL: /parking/<slug>/
    """
    lot = get_object_or_404(ParkingLot, slug=slug)
    context = {
        "lot": lot,
        "waiting_time": estimate_waiting_time(lot),
    }
    return render(request, "core/parking_detail.html", context)
