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
    home() + lots_state_api() también filtran por estado y tipo de
                            vehículo (FR12, ver core/filters.py).
    parking_info_view()   → FR35, información general de los parqueaderos.

El login/logout (FR2) está en core/auth_views.py.
"""

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_POST

from . import parking_info
from .favorites import favorite_lot_ids, toggle_favorite
from .filters import (
    STATUS_OPTIONS,
    VEHICLE_OPTIONS,
    filter_parking_lots,
    lot_matches,
    parse_filters,
    status_counts,
)
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

    # FR12: filtros ?estado=...&vehiculo=... Se aplican también aquí (no
    # solo en JavaScript) para que un link filtrado llegue ya filtrado y
    # para que funcione sin JavaScript. Todas las tarjetas se renderizan
    # igual; las que no pasan el filtro quedan ocultas, así el JavaScript
    # puede volver a mostrarlas al instante al cambiar de filtro.
    filters = parse_filters(request.GET)

    parking_lots = []
    for lot in lots:
        parking_lots.append({
            "lot": lot,
            "waiting_time": estimate_waiting_time(lot),
            "spots": lot.spots.all(),
            "is_favorite": lot.id in favorite_ids,
            "matches_filter": lot_matches(lot, filters["status"], filters["vehicle"]),
        })

    # Los favoritos van primero: si alguien marcó "mi parqueadero de
    # siempre", lo lógico es que lo vea sin tener que bajar a buscarlo.
    parking_lots.sort(key=lambda item: (not item["is_favorite"], item["lot"].name))

    metro_state = get_metro_status()
    counts = status_counts(lots)

    context = {
        "parking_lots": parking_lots,
        "transport_links": TRANSPORT_LINKS,
        "recommended_lot": recommend_parking_lot(lots) if lots else None,
        "metro_status": serialize_metro_status(metro_state),
        "map_lots": [serialize_lot(lot, favorite_ids) for lot in lots if lot.has_coordinates],
        "has_favorites": bool(favorite_ids),
        # FR12
        "active_filters": filters,
        "status_filter_options": _status_filter_options(filters, counts, len(lots)),
        "vehicle_filter_options": _vehicle_filter_options(filters),
        "visible_lots_count": sum(1 for item in parking_lots if item["matches_filter"]),
    }
    return render(request, "core/home.html", context)


# ── FR12: botones de filtro del home ──────────────────────────────────────────


def _filter_href(status, vehicle):
    """Link del home con esos filtros (los vacíos no se ponen en la URL)."""
    params = {key: value for key, value in (("estado", status), ("vehiculo", vehicle)) if value}
    query = f"?{urlencode(params)}" if params else ""
    return f"{reverse('home')}{query}#disponibilidad"


def _status_filter_options(filters, counts, total):
    options = [{"value": "", "label": "Todos", "count": total}]
    options += [
        {"value": value, "label": label, "count": counts[value]}
        for value, label in STATUS_OPTIONS
    ]
    for opt in options:
        opt["active"] = (opt["value"] or None) == filters["status"]
        opt["href"] = _filter_href(opt["value"], filters["vehicle"])
    return options


def _vehicle_filter_options(filters):
    options = [{"value": "", "label": "Cualquiera", "icon": ""}]
    options += [
        {"value": value, "label": label, "icon": icon}
        for value, label, icon in VEHICLE_OPTIONS
    ]
    for opt in options:
        opt["active"] = (opt["value"] or None) == filters["vehicle"]
        opt["href"] = _filter_href(filters["status"], opt["value"])
    return options


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
    lots = list(ParkingLot.objects.prefetch_related("spots", "notices"))

    # FR12: la API acepta los mismos filtros que el home
    # (/api/lots/?estado=available&vehiculo=motorcycle). Sin parámetros
    # devuelve todos, que es lo que usa el refresco en vivo del home.
    filters = parse_filters(request.GET)
    lots = filter_parking_lots(lots, filters["status"], filters["vehicle"])

    return JsonResponse({
        "ok": True,
        "filters": filters,
        "lots": [serialize_lot(lot, favorite_ids) for lot in lots],
    })


# ── FR35: información general de los parqueaderos ────────────────────────────


def parking_info_view(request):
    """
    FR35 – University parking information.

    Página con la información general de los parqueaderos de EAFIT:
    horarios (con indicador de abierto/cerrado ahora), tarifas, dónde
    pagar, cómo entrar, normas y contacto. El contenido vive en
    core/parking_info.py para poder actualizarlo sin tocar el HTML.
    Al lado de cada horario se muestra la disponibilidad en vivo del
    parqueadero correspondiente.
    """
    lots_by_slug = {lot.slug: lot for lot in ParkingLot.objects.all()}

    context = {
        "lots_info": parking_info.lots_with_status(lots_by_slug),
        "rates": parking_info.RATES,
        "payment_points": parking_info.PAYMENT_POINTS,
        "online_payment_note": parking_info.ONLINE_PAYMENT_NOTE,
        "entry_options": parking_info.ENTRY_OPTIONS,
        "grace_period_note": parking_info.GRACE_PERIOD_NOTE,
        "rules": parking_info.RULES,
        "contacts": parking_info.CONTACTS,
        "source_url": parking_info.SOURCE_URL,
    }
    return render(request, "core/parking_info.html", context)


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

    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'Debes iniciar sesión para reportar.'}, status=403)
        
    last_report_time_iso = request.session.get('last_report_time')
    if last_report_time_iso:
        try:
            last_report_time = timezone.datetime.fromisoformat(last_report_time_iso)
            if timezone.now() < last_report_time + timedelta(minutes=3):
                return JsonResponse({'ok': False, 'error': 'Debes esperar 3 minutos entre reportes para evitar spam.'}, status=429)
        except ValueError:
            pass
            
    request.session['last_report_time'] = timezone.now().isoformat()
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


def general_rules(request):
    return render(request, 'core/general_rules.html')
