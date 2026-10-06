"""Tests for cleaning, engineered features, and a fitted pipeline."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from data.cleaning import clean_observations
from data.schema import coerce_observation_frame
from features.engineering import ENGINEERED_FEATURES, RAW_FEATURES, add_engineered_features
from models.training import FeatureBuilder, candidate_models


def _raw() -> pd.DataFrame:
    path = Path(__file__).resolve().parents[1] / "data" / "interim" / "consolidated_raw.csv"
    return coerce_observation_frame(pd.read_csv(path))


def test_cleaning_removes_exact_duplicates_and_keeps_maize_label():
    raw = _raw()
    clean, report = clean_observations(raw)
    assert report["exact_duplicates_after"] == 0
    assert clean["yield_t_ha"].isna().sum() == 0
    assert set(clean["data_source_type"]) == {"SYNTHETIC"}
    assert set(clean["crop"]) == {"maize"}
    assert len(clean) < len(raw)


def test_engineered_features_match_their_definitions():
    raw = _raw().dropna(subset=RAW_FEATURES).head(20)
    built = add_engineered_features(raw)
    assert set(ENGINEERED_FEATURES).issubset(built.columns)
    assert np.allclose(
        built["temperature_range_c"],
        built["max_temperature_c"] - built["min_temperature_c"],
    )
    assert (built["degrees_above_33_c"] >= 0).all()
    assert (built["planting_delay_days"] >= 0).all()


def test_pipeline_predicts_one_yield_and_rejects_a_missing_column():
    raw = _raw()
    clean, _ = clean_observations(raw)
    train = clean.loc[clean["year"] <= 2021]
    model = candidate_models(7)["Linear Regression"]
    model.fit(train.loc[:, RAW_FEATURES], train["yield_t_ha"])
    one = train.loc[:, RAW_FEATURES].head(1)
    predicted = model.predict(one)
    assert predicted.shape == (1,)
    assert np.isfinite(predicted[0])
    broken = one.drop(columns=["rainfall_mm"])
    with pytest.raises(ValueError):
        FeatureBuilder().transform(broken)
