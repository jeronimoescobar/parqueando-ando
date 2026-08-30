from django.contrib import admin

from .models import ParkingLot


@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = ('name', 'total_capacity', 'occupied_spaces', 'last_updated')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('last_updated',)

    fieldsets = (
        ("Información general", {
            "fields": ("name", "slug", "total_capacity", "last_updated"),
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
