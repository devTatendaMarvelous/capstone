from django.contrib import admin

from apps.core.admin_site import admin_site
from apps.core.models import AuditLog
from apps.reports.models import GeneratedReport


class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "user", "object_type", "object_id", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("action", "user__username", "object_type")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = ("report_type", "export_format", "created_by", "created_at", "row_count")
    list_filter = ("report_type", "export_format", "created_at")
    search_fields = ("created_by__username", "report_type")
    date_hierarchy = "created_at"


admin_site.register(AuditLog, AuditLogAdmin)
admin_site.register(GeneratedReport, GeneratedReportAdmin)
