from rest_framework import serializers

from apps.predictions.ml_service import BOUNDS, RAW_FEATURES
from apps.predictions.models import FarmLocation, Prediction


class LocationInputSerializer(serializers.Serializer):
    latitude = serializers.FloatField(help_text="Latitude in decimal degrees.")
    longitude = serializers.FloatField(help_text="Longitude in decimal degrees.")
    location_selection_method = serializers.ChoiceField(
        choices=[
            ("browser_geolocation", "Browser Geolocation"),
            ("manual_map_selection", "Manual Map Selection"),
            ("manual_coordinates", "Manual Coordinates"),
        ],
        required=False,
        default="manual_coordinates",
    )
    confirmed = serializers.BooleanField(required=False, default=False)
    description = serializers.CharField(required=False, allow_blank=True, default="")


class LocationValidationRequestSerializer(serializers.Serializer):
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    location_selection_method = serializers.CharField(required=False, default="manual_coordinates")
    is_confirmed = serializers.BooleanField(required=False, default=False)
    location_description = serializers.CharField(required=False, allow_blank=True, default="")


class EnvironmentalPreviewRequestSerializer(serializers.Serializer):
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    season_year = serializers.IntegerField(required=False, default=2023)
    planting_date = serializers.CharField(required=False, allow_blank=True, default="")
    force_refresh = serializers.BooleanField(required=False, default=False)


class PredictionRequestSerializer(serializers.Serializer):
    # Location selection
    location = LocationInputSerializer(required=False, help_text="Farmer confirmed location.")
    latitude = serializers.FloatField(required=False, help_text="Direct latitude fallback.")
    longitude = serializers.FloatField(required=False, help_text="Direct longitude fallback.")
    location_selection_method = serializers.CharField(required=False, default="manual_coordinates")
    location_confirmed = serializers.BooleanField(required=False, default=False)

    # Core farm management inputs
    area_ha = serializers.FloatField(
        min_value=BOUNDS["area_ha"][0],
        max_value=BOUNDS["area_ha"][1],
        help_text="Cultivated maize area, hectares. Used to convert yield into total production.",
    )
    planting_date = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Calendar planting date (e.g. '2023-11-15' or '11-15'). Converted to planting_day.",
    )
    planting_day = serializers.FloatField(
        required=False,
        min_value=BOUNDS["planting_day"][0],
        max_value=BOUNDS["planting_day"][1],
        help_text="Planting day index where 1 is 1 November.",
    )
    fertilizer_kg_ha = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=BOUNDS["fertilizer_kg_ha"][0],
        max_value=BOUNDS["fertilizer_kg_ha"][1],
        help_text="Fertilizer product rate in kg/ha. If unknown, training median is imputed.",
    )

    # Optional manual weather and soil overrides
    rainfall_mm = serializers.FloatField(
        required=False,
        min_value=BOUNDS["rainfall_mm"][0],
        max_value=BOUNDS["rainfall_mm"][1],
        help_text="Seasonal rainfall in mm (optional override).",
    )
    avg_temperature_c = serializers.FloatField(
        required=False,
        min_value=BOUNDS["avg_temperature_c"][0],
        max_value=BOUNDS["avg_temperature_c"][1],
        help_text="Average growing-season temperature in °C (optional override).",
    )
    max_temperature_c = serializers.FloatField(
        required=False,
        min_value=BOUNDS["max_temperature_c"][0],
        max_value=BOUNDS["max_temperature_c"][1],
        help_text="Mean daily maximum temperature in °C (optional override).",
    )
    min_temperature_c = serializers.FloatField(
        required=False,
        min_value=BOUNDS["min_temperature_c"][0],
        max_value=BOUNDS["min_temperature_c"][1],
        help_text="Mean daily minimum temperature in °C (optional override).",
    )
    soil_ph = serializers.FloatField(
        required=False,
        min_value=BOUNDS["soil_ph"][0],
        max_value=BOUNDS["soil_ph"][1],
        help_text="Topsoil pH (optional override).",
    )
    soil_nitrogen = serializers.FloatField(
        required=False,
        min_value=BOUNDS["soil_nitrogen"][0],
        max_value=BOUNDS["soil_nitrogen"][1],
        help_text="Total soil nitrogen in percent (optional override).",
    )
    soil_organic_carbon = serializers.FloatField(
        required=False,
        min_value=BOUNDS["soil_organic_carbon"][0],
        max_value=BOUNDS["soil_organic_carbon"][1],
        help_text="Soil organic carbon in percent (optional override).",
    )


class PredictionResponseSerializer(serializers.Serializer):
    predicted_yield_t_ha = serializers.FloatField()
    predicted_production_tonnes = serializers.FloatField()
    estimated_production_tonnes = serializers.FloatField()
    model_version = serializers.CharField()
    location = serializers.DictField(required=False)
    environmental_data = serializers.DictField(required=False)
    data_sources = serializers.ListField(child=serializers.DictField(), required=False)
    data_quality = serializers.DictField(required=False)
    interpretation = serializers.CharField()
    disclaimer = serializers.CharField()


class PredictionRecordSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    location = serializers.SerializerMethodField()

    class Meta:
        model = Prediction
        fields = [
            "id",
            "username",
            "model_version",
            "prediction_inputs",
            "predicted_yield",
            "predicted_production",
            "farm_area",
            "location",
            "data_sources",
            "data_quality",
            "created_at",
        ]

    def get_location(self, obj):
        if obj.farm_location:
            return {
                "latitude": obj.farm_location.latitude,
                "longitude": obj.farm_location.longitude,
                "selection_method": obj.farm_location.location_selection_method,
                "confirmed": obj.farm_location.is_confirmed,
                "description": obj.farm_location.location_description,
                "is_within_study_area": obj.farm_location.is_within_study_area,
            }
        return None
