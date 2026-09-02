"""
Vistas del panel de administrador (FR16, FR17) y del mapeador visual de
espacios. Todo protegido con @staff_member_required: redirige a
/accounts/login/ si no hay sesión, y devuelve 403 si el usuario logueado
no es staff — el mismo login que usa /admin/ (mismo modelo de usuario,
misma sesión de Django).
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from core.models import ParkingLot, ParkingSpot


@staff_member_required
def dashboard(request):
    """
    FR16 – Administrator dashboard:
           Resumen en vivo de los 4 parqueaderos: ocupación, capacidad y
           estado de los espacios reportados por los usuarios en el plano.

    FR17 – Parking data management:
           Enlaza a /admin/ (editar capacidad, subir el plano) y al
           mapeador visual (spot_mapper) para ubicar cada ParkingSpot
           haciendo clic sobre la imagen — los 4 parqueaderos son fijos,
           la gestión es siempre sobre los existentes.
    """
    lots = ParkingLot.objects.all()
    return render(request, "adminpanel/dashboard.html", {"lots": lots})


# ── Mapeador visual de espacios (clic para ubicar, arrastrar, girar) ───────────


@staff_member_required
def spot_mapper(request, slug):
    """
    Pantalla para "montar" el plano sin calcular porcentajes a mano:
    el administrador ve la imagen (`lot.layout_image`) y hace clic sobre
    cada celda para crear un ParkingSpot ahí mismo; puede arrastrar uno
    existente para reubicarlo, girarlo 90° o cambiar su tamaño, o
    borrarlo. Todo vía fetch, sin recargar.
    """
    lot = get_object_or_404(ParkingLot, slug=slug)
    return render(request, "adminpanel/spot_mapper.html", {"lot": lot, "spots": lot.spots.all()})


@staff_member_required
@require_POST
def mapper_create_spot(request, slug):
    """Crea un ParkingSpot en la posición (%) donde el admin hizo clic."""
    lot = get_object_or_404(ParkingLot, slug=slug)
    label = (request.POST.get("label") or "").strip()
    vehicle_type = request.POST.get("vehicle_type", "car")
    pos_x = request.POST.get("pos_x")
    pos_y = request.POST.get("pos_y")

    if not label or pos_x is None or pos_y is None:
        return JsonResponse({"ok": False, "error": "Faltan datos (etiqueta o posición)."}, status=400)

    if vehicle_type not in dict(ParkingSpot.VEHICLE_TYPES):
        vehicle_type = "car"

    if ParkingSpot.objects.filter(lot=lot, label=label).exists():
        return JsonResponse(
            {"ok": False, "error": f"Ya existe un espacio con la etiqueta '{label}' en {lot.name}."},
            status=400,
        )

    try:
        spot = ParkingSpot.objects.create(
            lot=lot, label=label, vehicle_type=vehicle_type, pos_x=pos_x, pos_y=pos_y,
        )
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Posición inválida."}, status=400)

    return JsonResponse({
        "ok": True,
        "id": spot.id,
        "label": spot.label,
        "vehicle_type": spot.vehicle_type,
        "pos_x": float(spot.pos_x),
        "pos_y": float(spot.pos_y),
        "rotation": spot.rotation,
        "width": spot.width,
        "height": spot.height,
    })


@staff_member_required
@require_POST
def mapper_update_spot(request, slug, spot_id):
    """
    Actualiza uno o varios atributos de un espacio desde el mapeador:
    posición (arrastrar), rotación (botón "Girar 90°") o tamaño (ancho/alto).
    Solo actualiza los campos que vienen en el POST — así el arrastre no
    toca la rotación, y viceversa.
    """
    spot = get_object_or_404(ParkingSpot, id=spot_id, lot__slug=slug)
    pos_x = request.POST.get("pos_x")
    pos_y = request.POST.get("pos_y")
    rotation = request.POST.get("rotation")
    width = request.POST.get("width")
    height = request.POST.get("height")

    fields_to_update = []
    try:
        if pos_x is not None:
            spot.pos_x = pos_x
            fields_to_update.append("pos_x")
        if pos_y is not None:
            spot.pos_y = pos_y
            fields_to_update.append("pos_y")
        if rotation is not None:
            spot.rotation = int(rotation) % 360
            fields_to_update.append("rotation")
        if width is not None:
            spot.width = max(10, min(300, int(width)))
            fields_to_update.append("width")
        if height is not None:
            spot.height = max(10, min(300, int(height)))
            fields_to_update.append("height")
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Datos inválidos."}, status=400)

    if fields_to_update:
        spot.save(update_fields=fields_to_update)

    return JsonResponse({
        "ok": True,
        "pos_x": float(spot.pos_x),
        "pos_y": float(spot.pos_y),
        "rotation": spot.rotation,
        "width": spot.width,
        "height": spot.height,
    })


@staff_member_required
@require_POST
def mapper_delete_spot(request, slug, spot_id):
    """Elimina un espacio desde el mapeador visual."""
    spot = get_object_or_404(ParkingSpot, id=spot_id, lot__slug=slug)
    spot.delete()
    return JsonResponse({"ok": True})
