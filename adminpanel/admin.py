"""
Personalización del admin de Django (/admin/) para los modelos de `core`.

Vive aquí (y no en core/admin.py) porque el objetivo de esta app es
agrupar TODA la funcionalidad de administrador en un solo lugar. Django
descubre admin.py automáticamente en cualquier app instalada, así que
esto sigue registrándose en /admin/ sin ningún cambio adicional — solo
cambia en qué archivo vive el código.
"""

from django.contrib import admin

from core.models import ParkingLot, ParkingSpot


class ParkingSpotInline(admin.TabularInline):
    """
    Permite "montar" el plano de cada parqueadero: por cada ParkingSpot se
    define su etiqueta, posición (%), rotación y tamaño sobre
    `layout_image`, sin tocar código (FR17 — gestión de información de
    parqueaderos). Para una edición más visual (clic sobre la imagen,
    arrastrar, girar 90°), usa el mapeador en /dashboard/mapper/<slug>/.
    """
    model = ParkingSpot
    extra = 1
    fields = (
        "label", "vehicle_type", "pos_x", "pos_y",
        "rotation", "width", "height",
        "status", "status_updated_at",
    )
    readonly_fields = ("status_updated_at",)


@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = ('name', 'total_capacity', 'occupied_spaces', 'last_updated')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('last_updated',)
    inlines = [ParkingSpotInline]

    fieldsets = (
        ("Información general", {
            "fields": ("name", "slug", "total_capacity", "last_updated"),
        }),
        ("Plano del parqueadero (Sprint 2)", {
            "fields": ("layout_image",),
            "description": (
                "Sube aquí la imagen del croquis/plano. Luego, en la sección "
                "de espacios más abajo, ubica cada celda con su posición "
                "porcentual (X, Y) sobre esa imagen — o usa el mapeador "
                "visual desde el dashboard, que es más fácil."
            ),
        }),
        ("Desglose por tipo de vehículo (Capacidad)", {
            "fields": (
                "capacity_cars",
                "capacity_motorcycles",
                "capacity_accessibility",
            ),
            "classes": ("collapse",),
        }),
        ("Desglose por tipo de vehículo (Ocupación)", {
            "fields": (
                "occupied_cars",
                "occupied_motorcycles",
                "occupied_accessibility",
            ),
        }),
    )

    def has_add_permission(self, request):
        # Requerimiento del cliente: los 4 parqueaderos son fijos y no se
        # crean desde el panel de administración.
        return False

    def has_delete_permission(self, request, obj=None):
        # Por la misma razón, tampoco se pueden eliminar.
        return False


@admin.register(ParkingSpot)
class ParkingSpotAdmin(admin.ModelAdmin):
    """Vista plana de todos los espacios, útil para revisar/filtrar por estado."""
    list_display = ('label', 'lot', 'vehicle_type', 'rotation', 'width', 'height', 'status', 'status_updated_at')
    list_filter = ('lot', 'vehicle_type', 'status')
    search_fields = ('label',)
    readonly_fields = ('status_updated_at',)
