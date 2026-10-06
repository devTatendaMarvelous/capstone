"""Cleaning for the consolidated maize observation file.

The clean file drops exact duplicate rows and rows with no yield. Values
outside physical limits, and values outside the documented plausible bounds,
are set to missing. They are not replaced here. Median imputation happens
inside the training pipeline, fitted on the training seasons only, so the
clean file does not leak validation or test information.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data.schema import COLUMN_SPECS, OBSERVATION_COLUMNS, TARGET_COLUMN, coerce_observation_frame


def _as_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def remove_exact_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Keep the first copy of each fully identical row."""
    duplicates = int(df.duplicated().sum())
    cleaned = df.drop_duplicates().reset_index(drop=True)
    return cleaned, duplicates


def blank_physical_violations(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Set values outside physical bounds to missing. Those values cannot be measurements."""
    out = df.copy()
    counts: dict[str, int] = {}
    for column, spec in COLUMN_SPECS.items():
        if "physical_min" not in spec or column not in out.columns:
            continue
        values = _as_float(out[column])
        invalid = values.notna() & (
            (values < spec["physical_min"]) | (values > spec["physical_max"])
        )
        counts[column] = int(invalid.sum())
        if counts[column]:
            out.loc[invalid, column] = pd.NA
    return out, counts


def blank_temperature_inconsistencies(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Blank average temperature when the row breaks min <= avg <= max.

    The synthetic generator injects a few impossible average temperatures.
    The row is kept. Only the inconsistent average is removed.
    """
    out = df.copy()
    required = ["min_temperature_c", "avg_temperature_c", "max_temperature_c"]
    if any(column not in out.columns for column in required):
        return out, 0
    minimum = _as_float(out["min_temperature_c"])
    average = _as_float(out["avg_temperature_c"])
    maximum = _as_float(out["max_temperature_c"])
    present = minimum.notna() & average.notna() & maximum.notna()
    broken = present & ((minimum > average) | (average > maximum))
    out.loc[broken, "avg_temperature_c"] = pd.NA
    return out, int(broken.sum())


def blank_plausible_outliers(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Set values outside the project's plausible bounds to missing.

    Plausible bounds are study checks, not official agronomic limits.
    Blanking them removes the injected extremes from model fitting without
    deleting the rest of the farm-season row.
    """
    out = df.copy()
    counts: dict[str, int] = {}
    for column, spec in COLUMN_SPECS.items():
        if "plausible_min" not in spec or column not in out.columns:
            continue
        values = _as_float(out[column])
        flagged = values.notna() & (
            (values < spec["plausible_min"]) | (values > spec["plausible_max"])
        )
        counts[column] = int(flagged.sum())
        if counts[column]:
            out.loc[flagged, column] = pd.NA
    return out, counts


def drop_missing_target(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Drop rows whose yield is missing. They cannot be used for supervised learning."""
    missing = int(df[TARGET_COLUMN].isna().sum())
    kept = df.loc[df[TARGET_COLUMN].notna()].reset_index(drop=True)
    return kept, missing


def clean_observations(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Run the documented cleaning steps and return the clean frame plus a log."""
    original = coerce_observation_frame(df)
    before_rows = int(len(original))
    before_missing = int(original.isna().sum().sum())
    before_duplicates = int(original.duplicated().sum())

    step, duplicate_count = remove_exact_duplicates(original)
    step, physical_counts = blank_physical_violations(step)
    step, temperature_fixes = blank_temperature_inconsistencies(step)
    step, outlier_counts = blank_plausible_outliers(step)
    step, dropped_target = drop_missing_target(step)
    step = coerce_observation_frame(step)
    step = step.sort_values(["year", "season", "ward", "farm_id", "record_id"]).reset_index(drop=True)

    report = {
        "rows_before": before_rows,
        "rows_after": int(len(step)),
        "missing_cells_before": before_missing,
        "missing_cells_after": int(step.isna().sum().sum()),
        "exact_duplicates_before": before_duplicates,
        "exact_duplicates_removed": duplicate_count,
        "exact_duplicates_after": int(step.duplicated().sum()),
        "physical_violations_blanked": physical_counts,
        "temperature_order_repairs": temperature_fixes,
        "plausible_outliers_blanked": outlier_counts,
        "rows_dropped_for_missing_yield": dropped_target,
        "imputation": "none in the clean file; the model pipeline imputes training medians",
        "columns": OBSERVATION_COLUMNS,
    }
    return step, report


def quality_tables(before: pd.DataFrame, after: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Before/after tables for the cleaning notebook and the Excel export."""
    summary = pd.DataFrame(
        [
            {"stage": "before", "rows": len(before), "columns": before.shape[1], "missing_cells": int(before.isna().sum().sum()), "duplicate_rows": int(before.duplicated().sum())},
            {"stage": "after", "rows": len(after), "columns": after.shape[1], "missing_cells": int(after.isna().sum().sum()), "duplicate_rows": int(after.duplicated().sum())},
        ]
    )
    missing_rows = []
    for column in OBSERVATION_COLUMNS:
        if column not in before.columns:
            continue
        missing_rows.append(
            {
                "column": column,
                "missing_before": int(before[column].isna().sum()),
                "missing_after": int(after[column].isna().sum()) if column in after.columns else None,
            }
        )
    numeric = [
        column
        for column, spec in COLUMN_SPECS.items()
        if spec["dtype"] in {"float", "int"} and column in after.columns
    ]
    describe = after[numeric].describe().round(3).reset_index().rename(columns={"index": "statistic"})
    return {
        "before_after": summary,
        "missing_by_column": pd.DataFrame(missing_rows),
        "numeric_describe": describe,
    }


def write_clean_outputs(clean: pd.DataFrame, report: dict, tables: dict[str, pd.DataFrame], root: Path) -> dict[str, Path]:
    """Write the clean CSV, an Excel workbook, and an HTML summary."""
    processed = root / "data" / "processed"
    tables_dir = root / "reports" / "tables"
    processed.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    csv_path = processed / "clean_dataset.csv"
    xlsx_path = tables_dir / "02_cleaning_quality.xlsx"
    html_path = tables_dir / "02_cleaning_quality.html"
    clean.to_csv(csv_path, index=False)
    with pd.ExcelWriter(xlsx_path) as writer:
        for name, frame in tables.items():
            frame.to_excel(writer, sheet_name=name[:31], index=False)
        pd.DataFrame([{"key": key, "value": str(value)} for key, value in report.items()]).to_excel(
            writer, sheet_name="cleaning_log", index=False
        )
    html_path.write_text(tables["before_after"].to_html(index=False), encoding="utf-8")
    return {"clean_csv": csv_path, "excel": xlsx_path, "html": html_path}
