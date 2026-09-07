"""
Personalización del admin de Django (/admin/) para los modelos de `core`.

Vive aquí (y no en core/admin.py) porque el objetivo de esta app es
agrupar TODA la funcionalidad de administrador en un solo lugar. Django
descubre admin.py automáticamente en cualquier app instalada, así que
esto sigue registrándose en /admin/ sin ningún cambio adicional — solo
cambia en qué archivo vive el código.
"""

from django.contrib import admin

from core.models import ParkingLot, ParkingLotNotice, ParkingSpot


class ParkingSpotInline(admin.TabularInline):
    """
    FR17 – Parking data management (parte 1: espacios del plano).
    Permite "montar" el plano de cada parqueadero: por cada ParkingSpot se
    define su etiqueta, posición (%), rotación y tamaño sobre
    `layout_image`, sin tocar código. Para una edición más visual (clic
    sobre la imagen, arrastrar, girar 90°), usa el mapeador en
    /dashboard/mapper/<slug>/ (ver adminpanel/views.py: spot_mapper).
    """
    model = ParkingSpot
    extra = 1
    fields = (
        "label", "vehicle_type", "pos_x", "pos_y",
        "rotation", "width", "height",
        "status", "status_updated_at",
    )
    readonly_fields = ("status_updated_at",)


class ParkingLotNoticeInline(admin.TabularInline):
    """
    FR17 – Parking data management (parte 3: avisos administrativos).
    Aquí el administrador escribe avisos puntuales que aclaran algo del
    parqueadero (ej. "Entrada Norte cerrada por obras") — se muestran en
    la tarjeta de cada parqueadero en el home mientras `active` esté
    marcado. No es un reporte de usuario (eso vive en la app `reports`);
    es texto que el admin escribe directamente.
    """
    model = ParkingLotNotice
    extra = 1
    fields = ("message", "active", "created_at")
    readonly_fields = ("created_at",)


@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    """
    FR17 – Parking data management (parte 2: datos generales).
    Esta clase es la que permite al administrador editar nombre,
    capacidad total, desglose por tipo de vehículo, el plano y los
    avisos de cada parqueadero — junto con los inlines de arriba, esto es
    "gestionar la información del parqueadero" en la práctica.

    Los 4 parqueaderos son fijos (ver has_add_permission/
    has_delete_permission abajo): la gestión es SIEMPRE sobre los
    existentes, nunca de crear uno nuevo o borrar uno de los 4.
    """
    list_display = ('name', 'total_capacity', 'occupied_spaces', 'last_updated')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('last_updated',)
    inlines = [ParkingSpotInline, ParkingLotNoticeInline]

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


@admin.register(ParkingLotNotice)
class ParkingLotNoticeAdmin(admin.ModelAdmin):
    """
    Vista plana de todos los avisos (además del inline de arriba), útil
    para ver/desactivar avisos de varios parqueaderos sin entrar a cada
    uno por separado.
    """
    list_display = ('lot', 'message', 'active', 'created_at')
    list_filter = ('lot', 'active')
    list_editable = ('active',)
    search_fields = ('message', 'lot__name')
    readonly_fields = ('created_at',)
