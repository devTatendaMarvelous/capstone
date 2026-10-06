"""Flag impossible values. Do not delete them and do not impute them."""

from __future__ import annotations

import pandas as pd

ZIMBABWE_LAT = (-22.9, -15.5)
ZIMBABWE_LON = (25.0, 33.2)

RANGES = {
    "season_rainfall_mm": (0, 2500),
    "avg_temperature_c": (5, 40),
    "max_temperature_c": (5, 50),
    "min_temperature_c": (0, 40),
    "soil_ph": (3, 10),
    "yield_t_ha": (0, 20),
    "heat_stress_days": (0, 366),
    "rainfall_days": (0, 366),
}


def apply_quality_flags(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    flags = []
    outlier = []
    missing = []
    for _, row in out.iterrows():
        row_flags = []
        if pd.isna(row.get("yield_t_ha")):
            row_flags.append("MISSING")
        for column, (low, high) in RANGES.items():
            value = row.get(column)
            if pd.isna(value):
                continue
            if float(value) < low or float(value) > high:
                row_flags.append("OUT_OF_RANGE")
                break
        lat, lon = row.get("latitude"), row.get("longitude")
        if pd.notna(lat) and not (ZIMBABWE_LAT[0] <= float(lat) <= ZIMBABWE_LAT[1]):
            row_flags.append("OUT_OF_RANGE")
        if pd.notna(lon) and not (ZIMBABWE_LON[0] <= float(lon) <= ZIMBABWE_LON[1]):
            row_flags.append("OUT_OF_RANGE")
        if str(row.get("yield_geographic_level")) == "national" and str(row.get("geographic_level")) == "grid_cell":
            row_flags.append("SUSPICIOUS")
        if not row_flags:
            row_flags.append("VALID")
        # Preserve an earlier DUPLICATE mark.
        if str(row.get("quality_flag")) == "DUPLICATE" and "DUPLICATE" not in row_flags:
            row_flags.append("DUPLICATE")
        unique = list(dict.fromkeys(row_flags))
        flags.append("|".join(unique))
        outlier.append("OUT_OF_RANGE" in unique or "SUSPICIOUS" in unique)
        missing.append(bool(pd.isna(row.get("yield_t_ha")) or pd.isna(row.get("season_rainfall_mm"))))
    out["quality_flag"] = flags
    out["outlier_flag"] = outlier
    out["missing_value_flag"] = missing
    return out


def duplicate_mask(frame: pd.DataFrame) -> pd.Series:
    if "farm_id" in frame.columns and frame["farm_id"].notna().any():
        keys = ["farm_id", "year", "season", "crop"]
    else:
        keys = ["latitude", "longitude", "year", "season", "crop", "geographic_level", "yield_geographic_level"]
    present = [key for key in keys if key in frame.columns]
    return frame.duplicated(present, keep=False)
