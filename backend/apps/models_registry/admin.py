from django.contrib import admin

from apps.core.admin_site import admin_site
from apps.models_registry.models import ModelVersion


class ModelVersionAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "algorithm", "r2_display", "rmse_display", "mae_display", "is_active", "training_date")
    list_filter = ("algorithm", "is_active", "training_date")
    search_fields = ("name", "version", "algorithm")
    ordering = ("-is_active", "-created_at")

    @admin.display(description="R²")
    def r2_display(self, obj):
        return (obj.metrics or {}).get("r2")

    @admin.display(description="RMSE")
    def rmse_display(self, obj):
        return (obj.metrics or {}).get("rmse")

    @admin.display(description="MAE")
    def mae_display(self, obj):
        return (obj.metrics or {}).get("mae")


admin_site.register(ModelVersion, ModelVersionAdmin)
