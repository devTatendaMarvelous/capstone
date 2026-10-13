from django.conf import settings
from django.db import models


class FarmLocation(models.Model):
    SELECTION_METHODS = (
        ("browser_geolocation", "Browser Geolocation"),
        ("manual_map_selection", "Manual Map Selection"),
        ("manual_coordinates", "Manual Coordinates"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="farm_locations",
        null=True,
        blank=True,
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    location_selection_method = models.CharField(
        max_length=50,
        choices=SELECTION_METHODS,
        default="manual_coordinates",
    )
    is_confirmed = models.BooleanField(default=False)
    location_description = models.CharField(max_length=255, blank=True, default="")
    is_within_study_area = models.BooleanField(default=False)
    boundary_polygon = models.JSONField(
        null=True,
        blank=True,
        help_text="Optional GeoJSON polygon for future farm boundary support.",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"FarmLocation({self.latitude:.4f}, {self.longitude:.4f}) confirmed={self.is_confirmed}"


class EnvironmentalCache(models.Model):
    cache_key = models.CharField(max_length=255, unique=True, db_index=True)
    provider = models.CharField(max_length=50, db_index=True)
    grid_cell = models.CharField(max_length=50, db_index=True)
    date_range = models.CharField(max_length=80)
    parameters = models.JSONField(default=list)
    payload = models.JSONField()
    provenance = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["provider", "grid_cell"])]

    def __str__(self) -> str:
        return f"EnvironmentalCache({self.provider}:{self.grid_cell})"


class Prediction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="predictions")
    model_version = models.CharField(max_length=40, db_index=True)
    prediction_inputs = models.JSONField()
    predicted_yield = models.FloatField()
    predicted_production = models.FloatField()
    farm_area = models.FloatField()
    farm_location = models.ForeignKey(
        FarmLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="predictions",
    )
    environmental_data = models.JSONField(null=True, blank=True)
    data_sources = models.JSONField(default=list, blank=True)
    data_quality = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "created_at"])]

    def __str__(self) -> str:
        return f"{self.predicted_yield:.2f} t/ha by {self.user}"
