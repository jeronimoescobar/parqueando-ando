from django.apps import AppConfig


class AdminpanelConfig(AppConfig):
    """
    App que agrupa TODA la funcionalidad de administrador de Parqueando
    Ando en un solo lugar:
      - Las personalizaciones del admin de Django (ParkingLotAdmin,
        ParkingSpotInline, ParkingSpotAdmin) — ver admin.py.
      - El dashboard de administrador (FR16/FR17) — ver views.dashboard.
      - El mapeador visual de espacios (clic para ubicar, arrastrar,
        rotar, redimensionar) — ver views.spot_mapper y sus endpoints.

    Los modelos (ParkingLot, ParkingSpot) siguen viviendo en `core`
    porque también los usa el sitio público; esta app solo contiene
    las HERRAMIENTAS de administración sobre esos modelos.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'adminpanel'
    verbose_name = 'Panel de administración (Parqueando Ando)'
