from rest_framework import serializers

from apps.predictions.ml_service import BOUNDS, RAW_FEATURES
from apps.predictions.models import Prediction


class PredictionRequestSerializer(serializers.Serializer):
    rainfall_mm = serializers.FloatField(min_value=BOUNDS["rainfall_mm"][0], max_value=BOUNDS["rainfall_mm"][1], help_text="Seasonal rainfall, millimetres.")
    avg_temperature_c = serializers.FloatField(help_text="Average growing-season temperature, °C.")
    max_temperature_c = serializers.FloatField(help_text="Mean daily maximum temperature, °C.")
    min_temperature_c = serializers.FloatField(help_text="Mean daily minimum temperature, °C.")
    soil_ph = serializers.FloatField(help_text="Topsoil pH.")
    soil_nitrogen = serializers.FloatField(help_text="Total soil nitrogen, percent.")
    soil_organic_carbon = serializers.FloatField(help_text="Soil organic carbon, percent.")
    fertilizer_kg_ha = serializers.FloatField(help_text="Fertilizer product, kg/ha.")
    planting_day = serializers.FloatField(help_text="Planting day index. 1 is 1 November.")
    area_ha = serializers.FloatField(help_text="Cultivated maize area, hectares. Used only to convert yield into production.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in RAW_FEATURES:
            if name in self.fields and name in BOUNDS:
                self.fields[name].min_value = BOUNDS[name][0]
                self.fields[name].max_value = BOUNDS[name][1]


class PredictionResponseSerializer(serializers.Serializer):
    predicted_yield_t_ha = serializers.FloatField()
    predicted_production_tonnes = serializers.FloatField()
    model_version = serializers.CharField()
    interpretation = serializers.CharField()
    disclaimer = serializers.CharField()


class PredictionRecordSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

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
            "created_at",
        ]
