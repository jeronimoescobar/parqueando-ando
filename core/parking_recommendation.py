"""
Recomendación del mejor parqueadero disponible (FR9).

Este archivo está separado de views.py siguiendo el mismo patrón usado en
waiting_time.py y transport_links.py: si en el futuro cambia el criterio de
recomendación (por ejemplo, usar cercanía al usuario en vez de solo
ocupación), solo hay que tocar esta función.

Criterio actual: se recomienda el parqueadero con menor porcentaje de
ocupación entre los que no están llenos ("full"). Si todos están llenos,
no hay recomendación.
"""


def recommend_parking_lot(parking_lots):
    """
    Recibe una lista de instancias de ParkingLot y devuelve la que se
    recomienda (la que tiene más celdas disponibles proporcionalmente),
    o None si la lista está vacía o todos los parqueaderos están llenos.
    """
    candidates = [lot for lot in parking_lots if lot.occupancy_status != "full"]

    if not candidates:
        return None

    return min(candidates, key=lambda lot: lot.occupancy_ratio)
