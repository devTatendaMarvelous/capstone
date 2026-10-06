from rest_framework import serializers

from apps.models_registry.models import ModelVersion


class ModelVersionSerializer(serializers.ModelSerializer):
    r2 = serializers.SerializerMethodField()
    rmse = serializers.SerializerMethodField()
    mae = serializers.SerializerMethodField()

    class Meta:
        model = ModelVersion
        fields = [
            "id",
            "name",
            "version",
            "algorithm",
            "target_variable",
            "features",
            "metrics",
            "artifact_path",
            "dataset_version",
            "training_date",
            "is_active",
            "r2",
            "rmse",
            "mae",
        ]

    def _metric(self, obj, key):
        metrics = obj.metrics or {}
        value = metrics.get(key)
        if value is None:
            value = metrics.get(f"test_{key}")
        return value

    def get_r2(self, obj):
        return self._metric(obj, "r2")

    def get_rmse(self, obj):
        return self._metric(obj, "rmse")

    def get_mae(self, obj):
        return self._metric(obj, "mae")
