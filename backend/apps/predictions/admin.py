from django.contrib import admin

from apps.core.admin_site import admin_site
from apps.predictions.models import Prediction


class PredictionAdmin(admin.ModelAdmin):
    list_display = ("predicted_yield", "farm_area", "predicted_production", "model_version", "user", "created_at")
    list_filter = ("model_version", "created_at")
    search_fields = ("user__username", "model_version")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


admin_site.register(Prediction, PredictionAdmin)
