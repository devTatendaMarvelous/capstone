"""Load the saved maize model and score one farm. This module never fits a model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from django.conf import settings
from rest_framework.exceptions import ValidationError

RAW_FEATURES = [
    "rainfall_mm",
    "avg_temperature_c",
    "max_temperature_c",
    "min_temperature_c",
    "soil_ph",
    "soil_nitrogen",
    "soil_organic_carbon",
    "fertilizer_kg_ha",
    "planting_day",
]

BOUNDS = {
    "rainfall_mm": (0, 2500),
    "avg_temperature_c": (5, 45),
    "max_temperature_c": (5, 50),
    "min_temperature_c": (0, 40),
    "soil_ph": (3.5, 9),
    "soil_nitrogen": (0, 1),
    "soil_organic_carbon": (0, 10),
    "fertilizer_kg_ha": (0, 1000),
    "planting_day": (1, 150),
    "area_ha": (0.01, 100),
}


class MLModelService:
    _model = None
    _metadata = None

    @classmethod
    def load_model(cls):
        if cls._model is None:
            path = settings.ML_MODEL_PATH
            if not path.is_file():
                raise FileNotFoundError(f"Saved model not found at {path}.")
            import sys
            import types

            import joblib

            from apps.predictions.feature_builder import FeatureBuilder

            if "models" not in sys.modules:
                package = types.ModuleType("models")
                package.__path__ = []
                sys.modules["models"] = package
            training = types.ModuleType("models.training")
            training.FeatureBuilder = FeatureBuilder
            sys.modules["models.training"] = training
            sys.modules["models"].training = training
            cls._model = joblib.load(path)
            metadata_path = settings.ML_METADATA_PATH
            cls._metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
        return cls._model

    @classmethod
    def get_model_metadata(cls) -> dict:
        cls.load_model()
        return cls._metadata or {}

    @classmethod
    def validate_features(cls, payload: dict, allow_imputed_fertilizer: bool = True) -> dict[str, float]:
        errors: dict[str, list[str]] = {}
        cleaned: dict[str, float] = {}

        # Area is always strictly required for production calculations
        if "area_ha" not in payload or payload["area_ha"] in (None, ""):
            errors["area_ha"] = ["This field is required."]
        else:
            try:
                area_val = float(payload["area_ha"])
                low, high = BOUNDS["area_ha"]
                if not low <= area_val <= high:
                    errors["area_ha"] = [f"Value must be between {low} and {high}."]
                else:
                    cleaned["area_ha"] = area_val
            except (TypeError, ValueError):
                errors["area_ha"] = ["Enter a number."]

        for name in RAW_FEATURES:
            val = payload.get(name)

            # Documented missing fertilizer workflow:
            # If the farmer does not know their fertilizer rate, allow imputation only if supported
            if name == "fertilizer_kg_ha" and (val is None or val == ""):
                if allow_imputed_fertilizer:
                    cleaned[name] = np.nan
                    continue
                errors[name] = ["Fertilizer rate is required."]
                continue

            if val in (None, ""):
                errors[name] = ["This field is required."]
                continue

            try:
                numeric_val = float(val)
            except (TypeError, ValueError):
                errors[name] = ["Enter a number."]
                continue

            low, high = BOUNDS.get(name, (None, None))
            if low is not None and not low <= numeric_val <= high:
                errors[name] = [f"Value must be between {low} and {high}."]
                continue

            cleaned[name] = numeric_val

        # Consistency check for temperatures
        if (
            "min_temperature_c" in cleaned
            and "avg_temperature_c" in cleaned
            and "max_temperature_c" in cleaned
            and not (cleaned["min_temperature_c"] <= cleaned["avg_temperature_c"] <= cleaned["max_temperature_c"])
        ):
            errors["avg_temperature_c"] = ["Average temperature must sit between the minimum and the maximum."]

        if errors:
            raise ValidationError(errors)

        return cleaned

    @classmethod
    def predict(cls, payload: dict, allow_imputed_fertilizer: bool = True) -> dict[str, Any]:
        cleaned = cls.validate_features(payload, allow_imputed_fertilizer=allow_imputed_fertilizer)
        model = cls.load_model()
        frame = pd.DataFrame([{name: cleaned[name] for name in RAW_FEATURES}])
        yield_t_ha = float(model.predict(frame)[0])
        area = cleaned["area_ha"]
        version = cls.get_model_metadata().get("version", "1.0.0")
        rounded = round(yield_t_ha, 2)
        production = round(rounded * area, 2)

        return {
            "predicted_yield_t_ha": rounded,
            "predicted_production_tonnes": production,
            "estimated_production_tonnes": production,
            "model_version": version,
            "interpretation": (
                f"Estimated yield: {rounded:.2f} tonnes/ha. "
                "This is a model estimate, not a guaranteed harvest."
            ),
            "disclaimer": (
                "The estimate comes from a saved model and is not a guaranteed yield. "
                "Model 1.0.0 was trained on synthetic development data, not on a Macheke farm survey. "
                "The current model's evaluation results do not establish reliable performance on real farms."
            ),
        }
