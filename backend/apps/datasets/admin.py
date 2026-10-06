from django.contrib import admin

from apps.core.admin_site import admin_site
from apps.datasets.models import Dataset, DatasetVersion


class DatasetAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "created_at")
    search_fields = ("name",)
    date_hierarchy = "created_at"


class DatasetVersionAdmin(admin.ModelAdmin):
    list_display = ("dataset", "version", "source", "source_type", "record_count", "status", "uploaded_at")
    list_filter = ("source_type", "status", "uploaded_at")
    search_fields = ("dataset__name", "source", "version")
    date_hierarchy = "uploaded_at"
    ordering = ("-uploaded_at",)


admin_site.register(Dataset, DatasetAdmin)
admin_site.register(DatasetVersion, DatasetVersionAdmin)
