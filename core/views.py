"""
Vistas PÚBLICAS de la app core (sin login).

La funcionalidad de administrador (dashboard, mapeador visual de
espacios, personalización de /admin/) vive en la app `adminpanel` — ver
adminpanel/views.py y adminpanel/admin.py.

Sprint 1:
    home()               → FR5, FR6, FR7, FR28, FR8, FR9, FR10, FR37

Sprint 2:
    parking_detail()     → FR26, FR27 (+ mapa interactivo por espacio)
    update_spot_status() → mapa interactivo (reporte ocupado/vacío/no se sabe)
    metro_status_api()   → estado del Metro (scraping cacheado)
"""

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .metro_status import get_metro_status
from .models import ParkingLot, ParkingSpot
from .parking_recommendation import recommend_parking_lot
from .transport_links import TRANSPORT_LINKS
from .waiting_time import estimate_waiting_time


# ── Sprint 1 ───────────────────────────────────────────────────────────────────


def home(request):
    """
    Página principal del sistema.

    FR5  – Display university parking lots:
           Recupera y muestra todos los parqueaderos registrados.
    FR6  – Display available parking spaces:
           Cada contenedor muestra el estado cualitativo de disponibilidad.
    FR7  – Display parking occupancy status:
           Muestra la insignia de estado (Disponible / Limitado / Lleno).
    FR28 – Parking full message:
           Muestra un aviso explícito cuando el parqueadero está lleno.
    FR8  – Display parking lot map:
           El template renderiza el mapa Leaflet con los marcadores.
    FR9  – Recommend parking lot:
           El tiempo de espera y la ocupación sirven de guía para recomendar
           el parqueadero más conveniente al usuario.
    FR10 – Display estimated waiting time:
           Incluye el tiempo estimado de espera por parqueadero usando
           la lógica de `waiting_time.py`.
    FR37 – External transportation links:
           Incluye los enlaces a Uber, DiDi e InDrive, más el estado del
           Metro (noticias, horarios y semáforo de líneas).

    Cada parqueadero trae sus `spots` (ParkingSpot) para poder desplegar
    su plano interactivo dentro del mismo acordeón, sin salir a
    /parking/<slug>/ ni estorbar el mapa general (FR8).
    """
    lots = list(ParkingLot.objects.all())
    parking_lots = []

    for lot in lots:
        parking_lots.append({
            "lot": lot,
            "waiting_time": estimate_waiting_time(lot),
            "spots": lot.spots.all(),
        })

    context = {
        "parking_lots": parking_lots,
        "transport_links": TRANSPORT_LINKS,
        "recommended_lot": recommend_parking_lot(lots) if lots else None,
        "metro_status": get_metro_status(),
    }
    return render(request, "core/home.html", context)


def metro_status_api(request):
    """
    Endpoint JSON que home.html consulta cada 5 minutos (fetch) para
    refrescar el bloque de estado del Metro sin recargar la página. Usa
    la misma caché de 10 minutos que la carga inicial (get_metro_status),
    así que el scraping real a metrodemedellin.gov.co no ocurre en cada
    refresco del navegador, solo cuando el caché vence.
    """
    data = get_metro_status()
    return JsonResponse({
        "news": data["news"],
        "schedules": data["schedules"],
        "line_status": data["line_status"],
        "fetched_at": data["fetched_at"].isoformat(),
        "ok": data["ok"],
        "error": data["error"],
    })


# ── Sprint 2 ───────────────────────────────────────────────────────────────────


def parking_detail(request, slug):
    """
    Vista de detalle de un parqueadero individual (acceso directo, por si
    se comparte un link). El punto de entrada normal para los usuarios es
    el acordeón del home, no esta página.

    FR26 – Display parking capacity.
    FR27 – Parking lot details.

    Renderiza el plano interactivo: cada ParkingSpot se dibuja sobre
    `lot.layout_image` en la posición (pos_x, pos_y) y el usuario puede
    tocarlo para reportar si está ocupado, vacío, o si no sabe.
    """
    lot = get_object_or_404(ParkingLot, slug=slug)
    context = {
        "lot": lot,
        "waiting_time": estimate_waiting_time(lot),
        "spots": lot.spots.all(),
    }
    return render(request, "core/parking_detail.html", context)


@require_POST
def update_spot_status(request, slug, spot_id):
    """
    Reporte de estado de un espacio puntual del plano (ocupado / vacío / no
    se sabe). No requiere login: cualquier usuario que ve el plano puede
    reportar, igual que con FR21/FR22 a nivel de parqueadero completo.

    Responde JSON si la petición viene por fetch/AJAX (la usada por el
    plano interactivo); si no, hace un redirect normal como fallback.
    """
    spot = get_object_or_404(ParkingSpot, id=spot_id, lot__slug=slug)
    new_status = request.POST.get("status")

    if new_status not in dict(ParkingSpot.STATUS_CHOICES):
        return JsonResponse({"ok": False, "error": "Estado inválido."}, status=400)

    spot.report_status(new_status)

    wants_json = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or "application/json" in request.headers.get("accept", "")
    )
    if wants_json:
        return JsonResponse({
            "ok": True,
            "spot_id": spot.id,
            "status": spot.status,
            "status_display": spot.get_status_display(),
        })
    return redirect("parking_detail", slug=slug)
