"""Feature builder compatible with the serialized training pipeline.

The joblib file was created while `data-science/src` was on the path, so pickle
looks up ``models.training.FeatureBuilder``. The API registers that name before
loading the file. The formulas match ``features.engineering``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

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

MODEL_FEATURES = RAW_FEATURES + [
    "temperature_range_c",
    "degrees_above_33_c",
    "planting_delay_days",
]


class FeatureBuilder(BaseEstimator, TransformerMixin):
    """Build engineered columns from the raw prediction inputs."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        frame = X if isinstance(X, pd.DataFrame) else pd.DataFrame(X, columns=RAW_FEATURES)
        missing = [column for column in RAW_FEATURES if column not in frame.columns]
        if missing:
            raise ValueError(f"Missing model inputs: {missing}")
        for column in RAW_FEATURES:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame["temperature_range_c"] = frame["max_temperature_c"] - frame["min_temperature_c"]
        frame["degrees_above_33_c"] = (frame["max_temperature_c"] - 33.0).clip(lower=0)
        frame["planting_delay_days"] = (frame["planting_day"] - 40.0).clip(lower=0)
        return frame.loc[:, MODEL_FEATURES].to_numpy(dtype=float)

    def get_feature_names_out(self, input_features=None):
        return np.asarray(MODEL_FEATURES, dtype=object)
