from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from core.models import ParkingLot
from .models import ParkingReport

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
        
    return redirect('home')
