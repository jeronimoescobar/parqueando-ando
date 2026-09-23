"""
Vistas del componente REPORTS AND INFORMATION.

Aquí viven las 3 formas en que un usuario (sin necesidad de login)
reporta el estado de un parqueadero:

    FR21 – Report available parking space  → report_available_space()
    FR22 – Report occupied parking space   → report_occupied_space()
    FR30 – Report incorrect parking info   → report_incorrect_information()

Cada una crea un ParkingReport (status='pending') para que el
administrador lo revise después en /admin/ (FR34 — ver reports/admin.py),
y las dos primeras además ajustan al instante el contador de ocupación
del ParkingLot correspondiente, para que el home se vea actualizado de
inmediato sin esperar a que un admin valide el reporte.
"""

from django.shortcuts import get_object_or_404, redirect
from datetime import timedelta
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from core.favorites import favorite_lot_ids
from core.models import ParkingLot
from core.views import serialize_lot
from .models import ParkingReport



def check_report_allowed(request):
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
    return None

def _redirect_back(request):
    """
    Redirige a la página desde donde se envió el formulario (home o el
    detalle de un parqueadero), o a home si no hay referer disponible o
    si el referer no pertenece a este sitio (evita open redirects).

    Solo se usa como PLAN B: si el navegador tiene JavaScript activo, el
    home envía estos reportes por fetch y recibe JSON (ver `_respond`),
    así que nunca llega a recargar la página. Esto queda para quien
    navegue sin JavaScript.
    """
    referer = request.META.get('HTTP_REFERER')
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(referer)
    return redirect('home')


def _is_ajax(request):
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('accept', '')
    )


def _respond(request, lot, message, fallback=None):
    """
    Responde al reporte según cómo llegó (Sprint 3).

    ¿Por qué existe esto? Antes cada reporte hacía POST + redirect, o sea
    una recarga completa de la página: la persona reportaba un cupo y el
    navegador la devolvía al comienzo del home, perdiendo el scroll y el
    plano que tuviera abierto. Molesto y confuso.

    Ahora, si el reporte viene por fetch (que es lo normal desde el home),
    devolvemos JSON con el estado NUEVO de ese parqueadero. El navegador
    actualiza solo esa tarjeta, en el sitio, y muestra un aviso flotante.
    Cero recargas, cero saltos de scroll.

    Si llega sin JavaScript, cae al redirect de siempre y sigue
    funcionando igual que antes.
    """
    if _is_ajax(request):
        lot.refresh_from_db()
        # Se pasan los favoritos de quien reporta: si no, la respuesta diría
        # que el parqueadero no es favorito y la estrella de la tarjeta
        # parpadearía apagándose por un instante.
        return JsonResponse({
            'ok': True,
            'message': message,
            'lot': serialize_lot(lot, favorite_lot_ids(request)),
        })

    messages.success(request, message)
    return fallback if fallback is not None else _redirect_back(request)


# ============================================================================
# FR21 – Report available parking space
# El usuario indica "me voy" / liberé un espacio de cierto tipo de
# vehículo. Baja en 1 el contador de ocupados de ese tipo (sin bajar de 0)
# y deja registro del reporte para que un admin lo valide (FR34).
# ============================================================================
def report_available_space(request, lot_id):
    """
    Vista para FR21: Report available parking space.
    """
    if request.method == 'POST':
        error_response = check_report_allowed(request)
        if error_response:
            return error_response
        lot = get_object_or_404(ParkingLot, id=lot_id)
        vehicle_type = request.POST.get('vehicle_type', 'general')
        
        # 1. Crear el reporte en la BD
        ParkingReport.objects.create(
            lot=lot,
            report_type='available',
            vehicle_type=vehicle_type,
            status='pending'
        )
        
        # 2. Actualizar la ocupación del parqueadero
        if vehicle_type == 'car' and lot.occupied_cars > 0:
            lot.occupied_cars -= 1
        elif vehicle_type == 'motorcycle' and lot.occupied_motorcycles > 0:
            lot.occupied_motorcycles -= 1
        elif vehicle_type == 'accessibility' and lot.occupied_accessibility > 0:
            lot.occupied_accessibility -= 1
            
        lot.save()

        # 3. Confirmación (JSON si vino por fetch, mensaje + redirect si no)
        tipos = {'car': 'de carro', 'motorcycle': 'de moto', 'accessibility': 'PMR'}
        tipo_texto = tipos.get(vehicle_type, '')
        return _respond(
            request, lot,
            f'¡Gracias! Reportaste un espacio disponible {tipo_texto} en {lot.name}.'
        )

    return _redirect_back(request)


# ============================================================================
# FR22 – Report occupied parking space
# El usuario indica "acabo de llegar" / ocupé un espacio de cierto tipo de
# vehículo. Sube en 1 el contador de ocupados de ese tipo (sin pasar la
# capacidad) y deja registro del reporte para que un admin lo valide (FR34).
# ============================================================================
def report_occupied_space(request, lot_id):
    """
    Vista para FR22: Report occupied parking space.
    """
    if request.method == 'POST':
        error_response = check_report_allowed(request)
        if error_response:
            return error_response
        lot = get_object_or_404(ParkingLot, id=lot_id)
        vehicle_type = request.POST.get('vehicle_type', 'general')
        
        # 1. Crear el reporte
        ParkingReport.objects.create(
            lot=lot,
            report_type='occupied',
            vehicle_type=vehicle_type,
            status='pending'
        )
        
        # 2. Actualizar la ocupación del parqueadero (sumar 1)
        if vehicle_type == 'car' and lot.occupied_cars < lot.capacity_cars:
            lot.occupied_cars += 1
        elif vehicle_type == 'motorcycle' and lot.occupied_motorcycles < lot.capacity_motorcycles:
            lot.occupied_motorcycles += 1
        elif vehicle_type == 'accessibility' and lot.occupied_accessibility < lot.capacity_accessibility:
            lot.occupied_accessibility += 1
            
        lot.save()

        # 3. Confirmación (JSON si vino por fetch, mensaje + redirect si no)
        tipos = {'car': 'de carro', 'motorcycle': 'de moto', 'accessibility': 'PMR'}
        tipo_texto = tipos.get(vehicle_type, '')
        return _respond(
            request, lot,
            f'¡Gracias! Reportaste que ocupaste un espacio {tipo_texto} en {lot.name}.'
        )

    return _redirect_back(request)


# ============================================================================
# FR30 – Report incorrect parking information
# El usuario reporta que la info mostrada de un parqueadero está mal (sin
# que esto cambie los contadores de ocupación — a diferencia de FR21/FR22,
# esto NO se auto-aplica; solo queda pendiente para que un admin lo revise
# manualmente en /admin/, ver FR34).
# ============================================================================
def report_incorrect_information(request, lot_id):
    """
    Vista para FR30: Reportar información incorrecta.
    """
    if request.method == 'POST':
        error_response = check_report_allowed(request)
        if error_response:
            return error_response
        lot = get_object_or_404(ParkingLot, id=lot_id)

        vehicle_type = request.POST.get('vehicle_type', 'general')
        description = request.POST.get('description', '').strip()

        ParkingReport.objects.create(
            lot=lot,
            report_type='incorrect',
            vehicle_type=vehicle_type,
            description=description,
            status='pending'
        )

        return _respond(
            request, lot,
            f'¡Gracias! Reportaste información incorrecta en {lot.name}. '
            f'Un administrador lo revisará.',
            fallback=redirect('home'),
        )

    return redirect('home')