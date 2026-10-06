"""A short set of maize features that can be computed from a prediction request.

No feature is added unless the API can rebuild it from the raw inputs.
Seasonal rainfall is already `rainfall_mm`, so it is not copied into a second
column. Fertilizer is already stored per hectare.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

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

ENGINEERED_FEATURES = [
    "temperature_range_c",
    "degrees_above_33_c",
    "planting_delay_days",
]

MODEL_FEATURES = RAW_FEATURES + ENGINEERED_FEATURES

FEATURE_NOTES = [
    {
        "feature": "rainfall_mm",
        "kind": "source",
        "unit": "mm",
        "definition": "Seasonal rainfall total already stored on the observation. Not duplicated as rainfall_total.",
    },
    {
        "feature": "avg_temperature_c",
        "kind": "source",
        "unit": "°C",
        "definition": "Average temperature over the growing season. Used as growing_season_temperature without a rename.",
    },
    {
        "feature": "max_temperature_c",
        "kind": "source",
        "unit": "°C",
        "definition": "Mean daily maximum temperature over the growing season.",
    },
    {
        "feature": "min_temperature_c",
        "kind": "source",
        "unit": "°C",
        "definition": "Mean daily minimum temperature over the growing season.",
    },
    {
        "feature": "soil_ph",
        "kind": "source",
        "unit": "pH",
        "definition": "Topsoil pH.",
    },
    {
        "feature": "soil_nitrogen",
        "kind": "source",
        "unit": "%",
        "definition": "Total soil nitrogen, percent by mass.",
    },
    {
        "feature": "soil_organic_carbon",
        "kind": "source",
        "unit": "%",
        "definition": "Soil organic carbon, percent.",
    },
    {
        "feature": "fertilizer_kg_ha",
        "kind": "source",
        "unit": "kg/ha",
        "definition": "Fertilizer product already expressed per hectare. Not copied to a second rate column.",
    },
    {
        "feature": "planting_day",
        "kind": "source",
        "unit": "day index",
        "definition": "Planting day index where 1 is 1 November.",
    },
    {
        "feature": "temperature_range_c",
        "kind": "engineered",
        "unit": "°C",
        "definition": "max_temperature_c minus min_temperature_c. Summarises the diurnal range.",
    },
    {
        "feature": "degrees_above_33_c",
        "kind": "engineered",
        "unit": "°C",
        "definition": "How far max_temperature_c sits above 33°C, or 0 when the maximum is cooler. A simple heat-stress term.",
    },
    {
        "feature": "planting_delay_days",
        "kind": "engineered",
        "unit": "days",
        "definition": "How many days planting_day falls after day 40 (10 December), or 0 when planting is earlier.",
    },
]


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with the three engineered columns appended."""
    out = df.copy()
    for column in RAW_FEATURES:
        if column not in out.columns:
            raise ValueError(f"Cannot engineer features without {column}.")
        out[column] = pd.to_numeric(out[column], errors="coerce")
    out["temperature_range_c"] = out["max_temperature_c"] - out["min_temperature_c"]
    out["degrees_above_33_c"] = (out["max_temperature_c"] - 33.0).clip(lower=0)
    out["planting_delay_days"] = (out["planting_day"] - 40.0).clip(lower=0)
    return out


def feature_dictionary() -> pd.DataFrame:
    """Table of source and engineered features for the research export."""
    return pd.DataFrame(FEATURE_NOTES)


def write_feature_dictionary(root: Path) -> Path:
    path = root / "reports" / "tables" / "feature_dictionary.xlsx"
    path.parent.mkdir(parents=True, exist_ok=True)
    feature_dictionary().to_excel(path, index=False, sheet_name="features")
    return path
