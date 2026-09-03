from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from core.models import ParkingLot
from .models import ParkingReport


def _redirect_back(request):
    """
    Redirige a la página desde donde se envió el formulario (home o el
    detalle de un parqueadero), o a home si no hay referer disponible o
    si el referer no pertenece a este sitio (evita open redirects).
    """
    referer = request.META.get('HTTP_REFERER')
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(referer)
    return redirect('home')


def report_available_space(request, lot_id):
    """
    Vista para FR21: Report available parking space.
    """
    if request.method == 'POST':
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

        # 3. Mensaje de éxito
        tipos = {'car': 'de carro', 'motorcycle': 'de moto', 'accessibility': 'PMR'}
        tipo_texto = tipos.get(vehicle_type, '')
        messages.success(request, f'¡Gracias! Reportaste un espacio disponible {tipo_texto} en {lot.name}.')

    return _redirect_back(request)


def report_occupied_space(request, lot_id):
    """
    Vista para FR22: Report occupied parking space.
    """
    if request.method == 'POST':
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

        # 3. Mensaje de éxito
        tipos = {'car': 'de carro', 'motorcycle': 'de moto', 'accessibility': 'PMR'}
        tipo_texto = tipos.get(vehicle_type, '')
        messages.success(request, f'¡Gracias! Reportaste que ocupaste un espacio {tipo_texto} en {lot.name}.')

    return _redirect_back(request)

def report_incorrect_information(request, lot_id):
    """
    Vista para FR30: Reportar información incorrecta.
    """
    if request.method == 'POST':
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

        messages.success(
            request,
            f'¡Gracias! Reportaste información incorrecta en {lot.name}.'
        )

        return redirect('home')

    return redirect('home')