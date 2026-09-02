from django.contrib import admin
from .models import ParkingReport


@admin.register(ParkingReport)
class ParkingReportAdmin(admin.ModelAdmin):
    list_display = ('lot', 'report_type', 'vehicle_type', 'status', 'created_at')
    list_filter = ('report_type', 'status', 'vehicle_type')

    actions = ['remove_invalid_reports']

    @admin.action(description='Remove invalid parking reports')
    def remove_invalid_reports(self, request, queryset):
        invalid_reports = queryset.filter(status='invalid')
        count = invalid_reports.count()
        invalid_reports.delete()

        self.message_user(
            request,
            f'{count} invalid parking report(s) removed.'
        )