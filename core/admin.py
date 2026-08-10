from django.contrib import admin

from .models import ParkingLot


@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = ("name", "total_capacity", "occupied_spaces", "last_updated")
    list_editable = ("occupied_spaces",)
    prepopulated_fields = {"slug": ("name",)}

    fieldsets = (
        ("Información general", {
            "fields": ("name", "slug", "total_capacity", "occupied_spaces"),
        }),
        ("Desglose por tipo de vehículo", {
            "description": (
                "Ingresa la cantidad de celdas por tipo de vehículo. "
                "La suma debe coincidir con la Capacidad total."
            ),
            "fields": (
                "capacity_cars",
                "capacity_motorcycles",
                "capacity_accessibility",
            ),
            "classes": ("collapse",),
        }),
    )
