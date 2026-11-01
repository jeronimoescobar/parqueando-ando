"""
FR13 – Historial de disponibilidad de los parqueaderos.

Cada vez que cambia la ocupación de un parqueadero se guarda un
AvailabilitySnapshot (record_snapshot, que se dispara solo desde
core/signals.py). Aquí también se calculan los números que muestra la
página /historial/: resumen del periodo, promedio por hora del día y la
lista de registros.
"""

from datetime import timedelta

from django.utils import timezone

from .models import AvailabilitySnapshot

# clave en la URL -> (etiqueta, duración)
PERIODS = {
    "24h": ("Últimas 24 horas", timedelta(hours=24)),
    "7d": ("Últimos 7 días", timedelta(days=7)),
    "30d": ("Últimos 30 días", timedelta(days=30)),
}
DEFAULT_PERIOD = "24h"
MAX_ROWS = 200  # tope de filas en la tabla, para que la página no se ponga pesada


def record_snapshot(lot, force=False):
    """
    Guarda una foto de la ocupación actual de `lot`.

    Si la ocupación es idéntica a la del último registro no guarda nada
    (así no se llena la tabla con fotos repetidas), salvo force=True.
    Devuelve el snapshot creado o None.
    """
    last = lot.snapshots.order_by("-recorded_at", "-id").first()
    same = (
        last is not None
        and last.occupied_cars == lot.occupied_cars
        and last.occupied_motorcycles == lot.occupied_motorcycles
        and last.occupied_accessibility == lot.occupied_accessibility
        and last.total_capacity == lot.total_capacity
    )
    if same and not force:
        return None
    return AvailabilitySnapshot.objects.create(
        lot=lot,
        occupied_cars=lot.occupied_cars,
        occupied_motorcycles=lot.occupied_motorcycles,
        occupied_accessibility=lot.occupied_accessibility,
        total_capacity=lot.total_capacity,
    )


def resolve_period(key):
    """Devuelve (clave válida, etiqueta, duración); una clave rara cae al valor por defecto."""
    if key not in PERIODS:
        key = DEFAULT_PERIOD
    label, delta = PERIODS[key]
    return key, label, delta


def build_history(lot, period_key, now=None):
    """Todo lo que necesita la página: resumen, promedio por hora y registros del periodo."""
    key, label, delta = resolve_period(period_key)
    now = now or timezone.now()
    since = now - delta

    snapshots = list(
        AvailabilitySnapshot.objects.filter(lot=lot, recorded_at__gte=since).order_by("recorded_at", "id")
    )
    # Para el promedio/pico se usa el porcentaje de cada registro.
    percentages = [s.occupancy_percentage for s in snapshots]

    summary = None
    if snapshots:
        peak = max(snapshots, key=lambda s: (s.occupancy_percentage, s.recorded_at))
        low = min(snapshots, key=lambda s: (s.occupancy_percentage, -s.recorded_at.timestamp()))
        summary = {
            "count": len(snapshots),
            "average": round(sum(percentages) / len(percentages), 1),
            "peak": peak,
            "low": low,
        }

    # Promedio de ocupación por hora del día (hora local), para ver las horas pico.
    by_hour = {}
    for snap in snapshots:
        hour = timezone.localtime(snap.recorded_at).hour
        by_hour.setdefault(hour, []).append(snap.occupancy_percentage)
    hourly = [
        {
            "hour": hour,
            "label": f"{hour:02d}:00",
            "average": round(sum(values) / len(values), 1),
            "average_css": f"{sum(values) / len(values):.1f}",
        }
        for hour, values in sorted(by_hour.items())
    ]

    rows = list(reversed(snapshots))[:MAX_ROWS]  # más recientes primero
    return {
        "period": key,
        "period_label": label,
        "periods": [(k, v[0]) for k, v in PERIODS.items()],
        "since": timezone.localtime(since),
        "summary": summary,
        "hourly": hourly,
        "rows": rows,
        "truncated": len(snapshots) > MAX_ROWS,
        "total_rows": len(snapshots),
    }
