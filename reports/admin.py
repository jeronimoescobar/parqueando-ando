from django.contrib import admin
from django.utils.translation import gettext, ngettext

from .models import ParkingReport
from administration.models import AdminActionLog


# ============================================================================
# FR34 – Validate parking reports
# Acciones en lote para que el administrador valide o invalide reportes
# pendientes sin tener que abrirlos uno por uno.
# ============================================================================
@admin.action(description="Marcar reportes seleccionados como Validados")
def marcar_como_validado(modeladmin, request, queryset):
    ids = list(queryset.values_list("id", flat=True))
    updated = queryset.update(status="valid")
    AdminActionLog.objects.create(actor=request.user, action="report_status", target="Reportes", details={"report_ids": ids, "status": "valid"})
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
    ids = list(queryset.values_list("id", flat=True))
    updated = queryset.update(status="invalid")
    AdminActionLog.objects.create(actor=request.user, action="report_status", target="Reportes", details={"report_ids": ids, "status": "invalid"})
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
    ids = list(invalid_reports.values_list("id", flat=True))
    deleted_count, _ = invalid_reports.delete()
    AdminActionLog.objects.create(actor=request.user, action="report_bulk_delete", target="Reportes inválidos", details={"report_ids": ids, "deleted_count": deleted_count})

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

    list_display = ("lot", "user", "report_type", "vehicle_type", "status", "created_at")
    list_display_links = ("lot",)
    list_editable = ("status",)
    list_filter = ("status", "report_type", "vehicle_type", "lot", "user")
    search_fields = ("lot__name", "description", "user__username", "user__email")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    actions = (marcar_como_validado, marcar_como_invalido, remove_invalid_reports)

    def save_model(self, request, obj, form, change):
        old_status = ParkingReport.objects.get(pk=obj.pk).status if change else None
        super().save_model(request, obj, form, change)
        if change and "status" in form.changed_data:
            AdminActionLog.objects.create(actor=request.user, action="report_status", target=f"Reporte #{obj.pk}", details={"from": old_status, "to": obj.status})

    def delete_model(self, request, obj):
        AdminActionLog.objects.create(actor=request.user, action="report_delete", target=f"Reporte #{obj.pk}", details={"previous_status": obj.status})
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        ids = list(queryset.values_list("id", flat=True))
        AdminActionLog.objects.create(actor=request.user, action="report_bulk_delete", target="Reportes", details={"report_ids": ids, "deleted_count": len(ids)})
        super().delete_queryset(request, queryset)
