"""Quality counts for an uploaded table.

feature_completeness_percent is 100 * (1 - missing cells / all cells).
It measures completeness only. It is not a weighted quality score.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PHYSICAL_BOUNDS = {
    "area_ha": (0, 100),
    "rainfall_mm": (0, 3000),
    "avg_temperature_c": (-5, 50),
    "max_temperature_c": (-5, 55),
    "min_temperature_c": (-10, 40),
    "soil_ph": (3, 10),
    "soil_nitrogen": (0, 2),
    "soil_organic_carbon": (0, 20),
    "fertilizer_kg_ha": (0, 1500),
    "planting_day": (1, 150),
    "yield_t_ha": (0, 20),
}


def read_table(path) -> pd.DataFrame:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(file_path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(file_path)
    raise ValueError("Upload a CSV or Excel file.")


def quality_report(path) -> dict:
    file_path = Path(path)
    frame = read_table(file_path)
    rows, columns = frame.shape
    cells = rows * columns
    missing_cells = int(frame.isna().sum().sum())
    invalid = 0
    for column, (low, high) in PHYSICAL_BOUNDS.items():
        if column not in frame.columns:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        invalid += int((values.notna() & ((values < low) | (values > high))).sum())
    completeness = None if cells == 0 else round(100 * (1 - missing_cells / cells), 2)
    return {
        "observations": int(rows),
        "columns": int(columns),
        "missing_cells": missing_cells,
        "duplicate_rows": int(frame.duplicated().sum()),
        "invalid_values": invalid,
        "feature_completeness_percent": completeness,
        "completeness_definition": (
            "100 * (1 - missing cells / total cells). Completeness only, not a weighted quality score."
        ),
        "source_types": frame["data_source_type"].dropna().astype(str).value_counts().to_dict()
        if "data_source_type" in frame.columns
        else {},
    }
