"""
Vistas PÚBLICAS de la app core (sin login).

La funcionalidad de administrador (dashboard, mapeador visual de
espacios, personalización de /admin/) vive en la app `administration` —
ver administration/views.py y administration/admin.py.

Sprint 1:
    home()                → FR5, FR6, FR7, FR28, FR8, FR9, FR10, FR37

Sprint 2:
    parking_detail()      → FR26, FR27 (+ mapa interactivo por espacio)
    update_spot_status()  → mapa interactivo (ocupado/vacío/no se sabe)
    metro_status_api()    → estado del Metro (scraping cacheado)

Sprint 3 — actualización en vivo, búsqueda y favoritos:
    lots_state_api()      → estado actual de TODOS los parqueaderos en JSON.
                            El home lo consulta cada 30s y repinta solo los
                            números, sin recargar la página (así la persona
                            no pierde el scroll ni lo que tenía abierto).
    search_api()          → búsqueda inteligente por nombre, apodo o intención.
    toggle_favorite_api() → marcar/desmarcar un parqueadero como favorito.
"""

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .favorites import favorite_lot_ids, toggle_favorite
from .metro_status import get_metro_status, serialize_metro_status
from .models import ParkingLot, ParkingSpot
from .parking_recommendation import recommend_parking_lot
from .search import search_parking_lots
from .transport_links import TRANSPORT_LINKS
from .waiting_time import estimate_waiting_time


# ── Serialización compartida ──────────────────────────────────────────────────


def serialize_lot(lot, favorite_ids=frozenset()):
    """
    Estado de un parqueadero en formato JSON.

    Lo usan tanto el polling en vivo del home (lots_state_api) como la
    búsqueda, para que la interfaz reciba siempre la misma forma de datos
    y no haya dos maneras distintas de pintar lo mismo.
    """
    waiting = estimate_waiting_time(lot)
    counts = lot.spot_status_counts

    return {
        "id": lot.id,
        "slug": lot.slug,
        "name": lot.name,
        "is_favorite": lot.id in favorite_ids,

        # Ocupación general (FR6, FR7, FR28)
        "total_capacity": lot.total_capacity,
        "occupied_spaces": lot.occupied_spaces,
        "available_spaces": lot.available_spaces,
        "occupancy_percentage": lot.occupancy_percentage,
        "occupancy_percentage_css": lot.occupancy_percentage_css,
        "occupancy_status": lot.occupancy_status,
        "occupancy_status_display": lot.occupancy_status_display,

        # Desglose por tipo de vehículo (FR26)
        "capacity_cars": lot.capacity_cars,
        "capacity_motorcycles": lot.capacity_motorcycles,
        "capacity_accessibility": lot.capacity_accessibility,
        "occupied_cars": lot.occupied_cars,
        "occupied_motorcycles": lot.occupied_motorcycles,
        "occupied_accessibility": lot.occupied_accessibility,
        "available_cars": lot.available_cars,
        "available_motorcycles": lot.available_motorcycles,
        "available_accessibility": lot.available_accessibility,

        # Espera estimada (FR10)
        "waiting_label": waiting["label"],
        "waiting_level": waiting["level"],

        # Ubicación, para el mapa (Sprint 3: ya no está escrita a mano en el HTML)
        "latitude": float(lot.latitude) if lot.latitude is not None else None,
        "longitude": float(lot.longitude) if lot.longitude is not None else None,

        # Avisos del administrador
        "notices": [n.message for n in lot.active_notices],

        # Estado del plano interactivo
        "spot_counts": counts,
        "has_layout": bool(lot.layout_image),

        "last_updated": lot.last_updated.isoformat() if lot.last_updated else None,
    }


# ── Sprint 1 ──────────────────────────────────────────────────────────────────


def home(request):
    """
    Página principal del sistema.

    FR5  – Display university parking lots.
    FR6  – Display available parking spaces.
    FR7  – Display parking occupancy status.
    FR28 – Parking full message.
    FR8  – Display parking lot map (ahora dibujado desde la base de datos).
    FR9  – Recommend parking lot.
    FR10 – Display estimated waiting time.
    FR37 – External transportation links + estado del Metro.

    Sprint 3: esta vista ya NO espera al scraping del Metro. `get_metro_status()`
    lee de caché y, si hace falta, dispara el refresco en segundo plano —
    así el home carga siempre rápido aunque el sitio del Metro esté lento
    o no haya internet (antes podía quedarse 30 segundos cargando).
    """
    lots = list(ParkingLot.objects.prefetch_related("spots", "notices"))
    favorite_ids = favorite_lot_ids(request)

    parking_lots = []
    for lot in lots:
        parking_lots.append({
            "lot": lot,
            "waiting_time": estimate_waiting_time(lot),
            "spots": lot.spots.all(),
            "is_favorite": lot.id in favorite_ids,
        })

    # Los favoritos van primero: si alguien marcó "mi parqueadero de
    # siempre", lo lógico es que lo vea sin tener que bajar a buscarlo.
    parking_lots.sort(key=lambda item: (not item["is_favorite"], item["lot"].name))

    metro_state = get_metro_status()

    context = {
        "parking_lots": parking_lots,
        "transport_links": TRANSPORT_LINKS,
        "recommended_lot": recommend_parking_lot(lots) if lots else None,
        "metro_status": serialize_metro_status(metro_state),
        "map_lots": [serialize_lot(lot, favorite_ids) for lot in lots if lot.has_coordinates],
        "has_favorites": bool(favorite_ids),
    }
    return render(request, "core/home.html", context)


def metro_status_api(request):
    """
    Endpoint JSON que el home consulta periódicamente para refrescar el
    bloque del Metro sin recargar la página.

    Responde de inmediato con lo que haya en caché. El scraping real
    ocurre en segundo plano (ver core/metro_status.py), así que esta
    petición nunca se queda colgada esperando al sitio del Metro.
    """
    return JsonResponse(serialize_metro_status(get_metro_status()))


# ── Sprint 3: actualización en vivo, búsqueda y favoritos ─────────────────────


def lots_state_api(request):
    """
    Estado actual de todos los parqueaderos, en JSON.

    El home llama a esto cada 30 segundos y también justo después de que
    alguien reporta algo. Con la respuesta repinta SOLO los números
    (barra de ocupación, cupos, badges), sin recargar la página: así la
    persona no pierde el scroll, ni el plano que tenía abierto, ni lo que
    estaba escribiendo. Esto es lo que resuelve el "me devuelve al
    comienzo de la página cada vez que reporto algo".
    """
    favorite_ids = favorite_lot_ids(request)
    lots = ParkingLot.objects.prefetch_related("spots", "notices")

    return JsonResponse({
        "ok": True,
        "lots": [serialize_lot(lot, favorite_ids) for lot in lots],
    })


def search_api(request):
    """
    Búsqueda inteligente de parqueaderos (Sprint 3).

    No exige escribir el nombre exacto: entiende apodos ("el de
    ingeniería"), errores de dedo ("parqeadero nrte") e intenciones sin
    nombre ("el más desocupado", "uno para moto"). La lógica vive en
    core/search.py; los apodos se editan desde /admin/ en el campo
    "Otros nombres" de cada parqueadero, sin tocar código.
    """
    query = request.GET.get("q", "")
    favorite_ids = favorite_lot_ids(request)

    lots = list(ParkingLot.objects.prefetch_related("spots", "notices"))
    matches = search_parking_lots(query, lots)

    return JsonResponse({
        "ok": True,
        "query": query,
        "results": [
            {
                "reason": match["reason"],
                "score": match["score"],
                **serialize_lot(match["lot"], favorite_ids),
            }
            for match in matches
        ],
    })


@require_POST
def toggle_favorite_api(request, lot_id):
    """
    Marca o desmarca un parqueadero como favorito (Sprint 3).

    Funciona con o sin login: mientras no haya usuarios, el favorito
    queda asociado a la sesión del navegador. Cuando el login exista,
    basta con que llame a `core.favorites.attach_session_favorites_to_user`
    y los favoritos anónimos pasan solos a la cuenta — ver core/favorites.py.
    """
    lot = get_object_or_404(ParkingLot, id=lot_id)
    is_favorite = toggle_favorite(request, lot)

    return JsonResponse({
        "ok": True,
        "lot_id": lot.id,
        "is_favorite": is_favorite,
        "message": (
            f"{lot.name} quedó en tus favoritos."
            if is_favorite
            else f"{lot.name} ya no está en tus favoritos."
        ),
    })


# ── Sprint 2 ──────────────────────────────────────────────────────────────────


def parking_detail(request, slug):
    """
    Vista de detalle de un parqueadero (acceso directo, por si se comparte
    un link). El punto de entrada normal es el home, no esta página.

    FR26 – Display parking capacity.
    FR27 – Parking lot details.
    """
    lot = get_object_or_404(ParkingLot, slug=slug)
    context = {
        "lot": lot,
        "waiting_time": estimate_waiting_time(lot),
        "spots": lot.spots.all(),
        "is_favorite": lot.id in favorite_lot_ids(request),
    }
    return render(request, "core/parking_detail.html", context)


@require_POST
def update_spot_status(request, slug, spot_id):
    """
    Reporte de estado de un espacio puntual del plano (ocupado / vacío /
    no se sabe). No requiere login, igual que FR21/FR22.

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
