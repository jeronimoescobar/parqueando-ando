"""
Vistas del panel de administrador (FR16, FR17) y del mapeador visual de
espacios. Todo protegido con @staff_member_required: redirige a
/accounts/login/ si no hay sesión, y devuelve 403 si el usuario logueado
no es staff — el mismo login que usa /admin/ (mismo modelo de usuario,
misma sesión de Django).
"""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.models import ParkingLot, ParkingSpot
from reports.models import ParkingReport


@staff_member_required
def dashboard(request):
    """
    FR16 – Administrator dashboard:
           Resumen en vivo de los 4 parqueaderos: ocupación, capacidad y
           estado de los espacios reportados por los usuarios en el plano.
           También muestra cuántos reportes (FR21/FR22/FR30) están
           pendientes de revisión, con acceso directo a gestionarlos
           (FR32, FR34 — ver reports_management más abajo).

    FR17 – Parking data management:
           Enlaza a /admin/ (editar capacidad, subir el plano) y al
           mapeador visual (spot_mapper) para ubicar cada ParkingSpot
           haciendo clic sobre la imagen — los 4 parqueaderos son fijos,
           la gestión es siempre sobre los existentes.
    """
    lots = ParkingLot.objects.all()
    pending_reports_count = ParkingReport.objects.filter(status="pending").count()
    return render(request, "adminpanel/dashboard.html", {
        "lots": lots,
        "pending_reports_count": pending_reports_count,
    })


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


# ── Gestión de reportes (FR32, FR34) ────────────────────────────────────────────
#
# Un compañero implementó esto originalmente SOLO en el admin de Django
# (/admin/ → reports/admin.py: ParkingReportAdmin, con sus acciones
# "Marcar como Validado/Inválido" y "Eliminar reportes inválidos"). Esa
# vista se queda intacta y sigue funcionando igual — lo que faltaba era
# exponer lo mismo desde ESTE dashboard (que es adonde ya mandamos al
# administrador para todo lo demás), para no obligarlo a saltar a
# /admin/ solo para esta tarea. Las vistas de abajo llaman a los MISMOS
# campos y estados del modelo (ParkingReport.status), así que un reporte
# validado/invalidado desde aquí se ve exactamente igual en /admin/, y
# viceversa — es una segunda puerta de entrada a los mismos datos, no un
# sistema paralelo.


@staff_member_required
def reports_management(request):
    """
    FR34 – Validate parking reports:
           Lista los reportes enviados por los usuarios (FR21/FR22/FR30),
           agrupados por estado en pestañas (Pendientes/Válidos/
           Inválidos), para que el administrador los revise sin salir
           del dashboard.
    FR32 – Remove invalid parking reports:
           Botón "Eliminar todos los inválidos" (borra en lote los que
           ya están marcados como 'invalid') además de eliminar uno por
           uno desde su fila.

    El filtro de la pestaña viene por query string (?status=pending, por
    ejemplo) para poder enlazarlo directo desde otras páginas (ej. el
    dashboard podría linkear directo a "?status=pending").
    """
    status_filter = request.GET.get("status", "pending")
    valid_statuses = dict(ParkingReport.STATUS_CHOICES)

    reports_qs = ParkingReport.objects.select_related("lot").order_by("-created_at")
    if status_filter in valid_statuses:
        reports_qs = reports_qs.filter(status=status_filter)
    else:
        status_filter = "all"

    # Se arma la lista de pestañas ya con su conteo aquí (en vez de un
    # dict que el template tendría que indexar por variable, algo que
    # el lenguaje de templates de Django no permite directamente).
    status_tabs = [
        {
            "value": value,
            "label": label,
            "count": ParkingReport.objects.filter(status=value).count(),
        }
        for value, label in ParkingReport.STATUS_CHOICES
    ]

    context = {
        "reports": reports_qs,
        "status_filter": status_filter,
        "status_tabs": status_tabs,
        "total_count": ParkingReport.objects.count(),
    }
    return render(request, "adminpanel/reports_management.html", context)


def _redirect_to_reports(request):
    """
    Vuelve a la lista de reportes preservando la pestaña (status) desde
    la que se disparó la acción — el formulario manda ese valor en un
    campo oculto `redirect_status`. Evitamos usar HTTP_REFERER a propósito
    (es un vector de open-redirect si no se valida el host).
    """
    status = request.POST.get("redirect_status", "pending")
    valid_values = set(dict(ParkingReport.STATUS_CHOICES)) | {"all"}
    if status not in valid_values:
        status = "pending"
    return redirect(f"{reverse('reports_management')}?status={status}")


@staff_member_required
@require_POST
def report_set_status(request, report_id):
    """
    Cambia el estado de un reporte individual (Validar / Invalidar) desde
    una fila de la tabla del dashboard. Mismo efecto que editar el campo
    `status` de un ParkingReport en /admin/.
    """
    report = get_object_or_404(ParkingReport, id=report_id)
    new_status = request.POST.get("status")

    if new_status not in dict(ParkingReport.STATUS_CHOICES):
        messages.error(request, "Estado inválido.")
        return _redirect_to_reports(request)

    report.status = new_status
    report.save(update_fields=["status"])
    messages.success(request, f"Reporte #{report.id} marcado como '{report.get_status_display()}'.")

    return _redirect_to_reports(request)


@staff_member_required
@require_POST
def report_delete(request, report_id):
    """Elimina un reporte individual (cualquier estado) desde su fila."""
    report = get_object_or_404(ParkingReport, id=report_id)
    report.delete()
    messages.success(request, f"Reporte #{report_id} eliminado.")
    return _redirect_to_reports(request)


@staff_member_required
@require_POST
def reports_delete_all_invalid(request):
    """
    FR32 – Remove invalid parking reports (acción en lote).
    Borra TODOS los reportes que ya estén marcados como 'invalid' — el
    mismo efecto que la acción "Eliminar reportes inválidos" del admin
    de Django, pero accesible desde el dashboard con un solo botón.
    """
    deleted_count, _ = ParkingReport.objects.filter(status="invalid").delete()
    if deleted_count:
        messages.success(request, f"Se eliminaron {deleted_count} reporte(s) inválido(s).")
    else:
        messages.info(request, "No había reportes inválidos para eliminar.")
    return redirect(f"{reverse('reports_management')}?status=invalid")
