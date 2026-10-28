"""
FR33 – Estadísticas de ocupación de los parqueaderos (para los usuarios).

Ojo, no es lo mismo que FR18: FR18 (administration/views.py,
reports_statistics) es para el ADMINISTRADOR y resume los REPORTES
(pendientes, validados, por tipo). FR33 es una página pública que le
muestra a cualquier persona cómo está la OCUPACIÓN:

  - la ocupación general del campus,
  - la de cada parqueadero (del más lleno al más libre),
  - la de cada tipo de celda (carros, motos, PMR) sumando el campus,
  - cuántos estados hay (disponibles / limitados / llenos),
  - y la actividad de las últimas 24 horas según los reportes de
    "llegué" y "me voy" (FR21/FR22), que muestra qué tanto movimiento hay.

Aquí solo se calculan los números; el template
core/templates/core/occupancy_stats.html los pinta.
"""

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from .filters import STATUS_OPTIONS

VEHICLE_TYPES = [
    # (clave, etiqueta, clase del ícono — los mismos del home —, campo capacidad, campo ocupados)
    ("car", "Carros", "bi bi-car-front", "capacity_cars", "occupied_cars"),
    ("motorcycle", "Motos", "pa-ico pa-ico-moto", "capacity_motorcycles", "occupied_motorcycles"),
    ("accessibility", "PMR", "bi bi-universal-access", "capacity_accessibility", "occupied_accessibility"),
]

ACTIVITY_WINDOW = timedelta(hours=24)


def _percentage(part, whole):
    """Porcentaje 0-100 con un decimal (0 si no hay capacidad)."""
    if not whole:
        return 0.0
    return round(min(part / whole, 1.0) * 100, 1)


def _css_percentage(value):
    """El mismo porcentaje con punto decimal, para usarlo en style="width: …%"."""
    return f"{value:.1f}"


def campus_totals(lots):
    capacity = sum(lot.total_capacity for lot in lots)
    occupied = sum(min(lot.occupied_spaces, lot.total_capacity) for lot in lots)
    percentage = _percentage(occupied, capacity)
    return {
        "capacity": capacity,
        "occupied": occupied,
        "available": max(capacity - occupied, 0),
        "percentage": percentage,
        "percentage_css": _css_percentage(percentage),
    }


def lots_ranking(lots):
    """Cada parqueadero con su ocupación, ordenados del más lleno al más libre."""
    rows = []
    for lot in lots:
        rows.append({
            "lot": lot,
            "percentage": lot.occupancy_percentage,
            "percentage_css": lot.occupancy_percentage_css,
        })
    rows.sort(key=lambda row: (-row["percentage"], row["lot"].name))
    return rows


def by_vehicle_type(lots):
    """Ocupación por tipo de celda, sumando todos los parqueaderos."""
    rows = []
    for key, label, icon, capacity_field, occupied_field in VEHICLE_TYPES:
        capacity = sum(getattr(lot, capacity_field) for lot in lots)
        occupied = sum(min(getattr(lot, occupied_field), getattr(lot, capacity_field)) for lot in lots)
        percentage = _percentage(occupied, capacity)
        rows.append({
            "key": key,
            "label": label,
            "icon": icon,
            "capacity": capacity,
            "occupied": occupied,
            "available": max(capacity - occupied, 0),
            "percentage": percentage,
            "percentage_css": _css_percentage(percentage),
        })
    return rows


def status_breakdown(lots):
    counts = {value: 0 for value, _ in STATUS_OPTIONS}
    for lot in lots:
        counts[lot.occupancy_status] += 1
    return [{"value": value, "label": label, "count": counts[value]} for value, label in STATUS_OPTIONS]


def recent_activity(lots, now=None):
    """
    Llegadas (reportes "ocupé un espacio") y salidas ("liberé un espacio")
    de las últimas 24 horas, por parqueadero. Los reportes marcados como
    inválidos por el administrador no se cuentan.
    """
    from reports.models import ParkingReport  # import local: reports depende de core

    since = (now or timezone.now()) - ACTIVITY_WINDOW
    per_lot = {
        row["lot"]: row
        for row in (
            ParkingReport.objects.filter(created_at__gte=since)
            .exclude(status="invalid")
            .values("lot")
            .annotate(
                arrivals=Count("id", filter=Q(report_type="occupied")),
                departures=Count("id", filter=Q(report_type="available")),
            )
        )
    }

    rows = []
    for lot in lots:
        data = per_lot.get(lot.id, {})
        arrivals = data.get("arrivals", 0)
        departures = data.get("departures", 0)
        rows.append({"lot": lot, "arrivals": arrivals, "departures": departures, "total": arrivals + departures})
    rows.sort(key=lambda row: (-row["total"], row["lot"].name))

    busiest_total = rows[0]["total"] if rows else 0
    for row in rows:
        share = _percentage(row["total"], busiest_total)
        row["bar_css"] = _css_percentage(share)

    return {
        "rows": rows,
        "arrivals": sum(row["arrivals"] for row in rows),
        "departures": sum(row["departures"] for row in rows),
        "total": sum(row["total"] for row in rows),
    }


def build_statistics(lots, now=None):
    """Todo lo que necesita la página de FR33, en un solo diccionario."""
    lots = list(lots)
    ranking = lots_ranking(lots)
    with_capacity = [row for row in ranking if row["lot"].total_capacity]
    return {
        "has_lots": bool(lots),
        "totals": campus_totals(lots),
        "ranking": ranking,
        "most_occupied": with_capacity[0]["lot"] if with_capacity else None,
        "least_occupied": with_capacity[-1]["lot"] if with_capacity else None,
        "vehicle_types": by_vehicle_type(lots),
        "statuses": status_breakdown(lots),
        "activity": recent_activity(lots, now=now),
        "generated_at": timezone.localtime(now or timezone.now()),
    }
