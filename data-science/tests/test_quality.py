"""Range flags and duplicate detection do not delete rows."""

import pandas as pd

from acquisition.faostat import _wide_to_long
from validation.quality import apply_quality_flags, duplicate_mask


def test_negative_rainfall_is_flagged_and_kept():
    frame = pd.DataFrame(
        [
            {
                "season_rainfall_mm": -5,
                "avg_temperature_c": 22,
                "max_temperature_c": 30,
                "min_temperature_c": 15,
                "soil_ph": 6,
                "yield_t_ha": 1.2,
                "heat_stress_days": 1,
                "rainfall_days": 10,
                "latitude": -18.1,
                "longitude": 31.8,
                "geographic_level": "grid_cell",
                "yield_geographic_level": "national",
                "quality_flag": pd.NA,
            }
        ]
    )
    flagged = apply_quality_flags(frame)
    assert len(flagged) == 1
    assert "OUT_OF_RANGE" in flagged.loc[0, "quality_flag"]
    assert "SUSPICIOUS" in flagged.loc[0, "quality_flag"]


def test_duplicate_key_uses_coordinates_when_no_farm_id():
    frame = pd.DataFrame(
        [
            {"latitude": -18.1, "longitude": 31.8, "year": 2020, "season": "2019/2020", "crop": "maize", "geographic_level": "grid_cell", "yield_geographic_level": "national"},
            {"latitude": -18.1, "longitude": 31.8, "year": 2020, "season": "2019/2020", "crop": "maize", "geographic_level": "grid_cell", "yield_geographic_level": "national"},
        ]
    )
    assert duplicate_mask(frame).tolist() == [True, True]


def test_faostat_kg_per_ha_column_is_preserved_as_original_value():
    wide = pd.DataFrame(
        [
            {
                "Area": "Zimbabwe",
                "Item": "Maize (corn)",
                "Element": "Yield",
                "Unit": "kg/ha",
                "Y2020": "1500",
                "Y2020F": "A",
            }
        ]
    )
    long = _wide_to_long(wide)
    assert long.loc[0, "original_value"] == 1500
    assert long.loc[0, "year"] == 2020
    assert long.loc[0, "faostat_flag"] == "A"
