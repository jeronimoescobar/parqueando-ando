from django.contrib import admin
from django.utils.translation import gettext, ngettext

from .models import ParkingReport


# ============================================================================
# FR34 – Validate parking reports
# Acciones en lote para que el administrador valide o invalide reportes
# pendientes sin tener que abrirlos uno por uno.
# ============================================================================
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


# ============================================================================
# FR32 – Remove invalid parking reports
# Borra en lote los reportes que ya quedaron marcados como "invalid" (por
# la acción de arriba, o manualmente). Solo borra los que de verdad están
# inválidos dentro de lo seleccionado — si seleccionas reportes válidos o
# pendientes junto con inválidos, esos otros no se tocan.
# ============================================================================
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

    FR34 – Validate parking reports:
           Permite ver todos los reportes pendientes, filtrarlos por
           estado/tipo/parqueadero y cambiar su estado individualmente
           (columna editable `status`) o en lote (acciones "Marcar como
           Validado/Inválido" arriba).
    FR32 – Remove invalid parking reports:
           La acción "Eliminar reportes inválidos" (arriba) borra los que
           ya quedaron marcados como inválidos.
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
