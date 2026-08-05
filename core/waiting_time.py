"""
Cálculo del tiempo estimado de espera (Requerimiento 1).

Este archivo está separado de views.py a propósito: si en el futuro cambian
la fórmula (por ejemplo para usar reportes de usuarios en vez de solo
ocupación), solo hay que tocar este archivo. views.py y el template no
necesitan cambiar mientras `estimate_waiting_time()` siga devolviendo el
mismo diccionario.

Fórmula usada (ver justificación completa en el chat con Claude):
    1. Se calcula el % de ocupación del parqueadero (occupied / total).
    2. Ese % se traduce a un número estimado de vehículos "en cola".
    3. El tiempo estimado = vehículos_en_cola * minutos_por_vehiculo,
       usando 6 minutos como promedio del rango real (4 a 8 min) que
       reportó el equipo.

Estos umbrales son un punto de partida razonable para la demo del curso,
no un estudio de tráfico real. Se pueden ajustar libremente.
"""

# Minutos promedio que tarda un vehículo en ingresar (rango real: 4-8 min).
MINUTES_PER_VEHICLE = 6

# Umbrales de ocupación -> vehículos estimados en cola.
# Cada tupla es (umbral_de_ocupacion, vehiculos_en_cola).
# Se evalúan en orden; el primer umbral que la ocupación NO supere gana.
OCCUPANCY_THRESHOLDS = [
    (0.70, 0),   # menos del 70% ocupado -> prácticamente sin espera
    (0.90, 2),   # entre 70% y 90% -> ~2 vehículos esperando
    (1.01, 4),   # 90% o más -> ~4 vehículos esperando (parqueadero casi lleno)
]


def estimate_waiting_time(parking_lot):
    """
    Recibe una instancia de ParkingLot y devuelve un dict con:
        - minutes: minutos estimados de espera (int)
        - queue_estimate: vehículos estimados en cola (int)
        - level: "low" | "medium" | "high" (para colorear en el template)
        - label: texto ya listo para mostrar en pantalla

    Si el parqueadero no tiene capacidad configurada, se asume sin datos.
    """
    ratio = parking_lot.occupancy_ratio

    queue_estimate = OCCUPANCY_THRESHOLDS[-1][1]  # valor por defecto (el más alto)
    for threshold, vehicles in OCCUPANCY_THRESHOLDS:
        if ratio < threshold:
            queue_estimate = vehicles
            break

    minutes = queue_estimate * MINUTES_PER_VEHICLE

    if queue_estimate == 0:
        level = "low"
        label = "Disponible, sin espera"
    elif minutes <= 12:
        level = "medium"
        label = f"~{minutes} min de espera"
    else:
        level = "high"
        label = f"~{minutes} min de espera"

    return {
        "minutes": minutes,
        "queue_estimate": queue_estimate,
        "level": level,
        "label": label,
    }
