"""
Vista principal (home).

NOTA PARA EL EQUIPO: esta vista empezó como un placeholder vacío. Se le
agregó el contexto de los Requerimientos 1 y 2 (tiempo estimado de espera
y enlaces de transporte). Si alguien más necesita agregar datos al home
(ej. login, listado con más detalle), agréguenlos al diccionario que ya
arma `_build_home_context()` en vez de crear una vista nueva, para no
duplicar la ruta "/".
"""

from django.shortcuts import render

from .models import ParkingLot
from .parking_recommendation import recommend_parking_lot
from .transport_links import TRANSPORT_LINKS
from .waiting_time import estimate_waiting_time


def _build_home_context():
    """Arma el contexto del home: parqueaderos con su tiempo estimado
    de espera (Requerimiento 1), los enlaces de transporte externo
    (Requerimiento 2), el porcentaje de ocupación (FR7) y el parqueadero
    recomendado según disponibilidad (FR9)."""
    lots = list(ParkingLot.objects.all())

    parking_lots = []
    for lot in lots:
        parking_lots.append({
            "lot": lot,
            "waiting_time": estimate_waiting_time(lot),
        })

    return {
        "parking_lots": parking_lots,
        "transport_links": TRANSPORT_LINKS,
        "recommended_lot": recommend_parking_lot(lots),
    }


def home(request):
    return render(request, "core/home.html", _build_home_context())
