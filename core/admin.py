from django.contrib import admin

from .models import ParkingLot


@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = ("name", "total_capacity", "occupied_spaces", "last_updated")
    list_editable = ("occupied_spaces",)
    prepopulated_fields = {"slug": ("name",)}

