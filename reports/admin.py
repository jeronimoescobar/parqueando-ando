from django.contrib import admin
from django.utils.translation import ngettext

from .models import ParkingReport


@admin.action(description="Marcar reportes seleccionados como Validados")
def marcar_como_validado(modeladmin, request, queryset):
    updated = queryset.update(status="valid")
    modeladmin.message_user(
        request,
        ngettext(
            "%d reporte fue marcado como validado.",
            "%d reportes fueron marcados como validados.",
            updated,
        )
        % updated,
    )


@admin.action(description="Marcar reportes seleccionados como Inválidos")
def marcar_como_invalido(modeladmin, request, queryset):
    updated = queryset.update(status="invalid")
    modeladmin.message_user(
        request,
        ngettext(
            "%d reporte fue marcado como inválido.",
            "%d reportes fueron marcados como inválidos.",
            updated,
        )
        % updated,
    )


@admin.action(description="Eliminar reportes inválidos")
def remove_invalid_reports(modeladmin, request, queryset):
    invalid_reports = queryset.filter(status="invalid")
    deleted_count, _ = invalid_reports.delete()

    modeladmin.message_user(
        request,
        gettext(
            "%d reporte inválido fue eliminado."
            if deleted_count == 1
            else "%d reportes inválidos fueron eliminados."
        ) % deleted_count,
    )


@admin.register(ParkingReport)
class ParkingReportAdmin(admin.ModelAdmin):
    """
    Panel de administración para revisar los reportes enviados por los
    usuarios y decidir si son válidos o no.

    Satisface FR34 (Validate parking reports): permite ver todos los
    reportes pendientes, filtrarlos por estado/tipo/parqueadero y
    cambiar su estado individualmente (columna editable) o en lote
    (acciones "Marcar como Validado/Inválido").
    """

    list_display = ("lot", "report_type", "vehicle_type", "status", "created_at")
    list_display_links = ("lot",)
    list_editable = ("status",)
    list_filter = ("status", "report_type", "vehicle_type", "lot")
    search_fields = ("lot__name", "description")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    actions = (marcar_como_validado, marcar_como_invalido, remove_invalid_reports)
