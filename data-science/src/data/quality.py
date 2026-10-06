"""Dataset structure and quality summaries used by the CLI and notebooks."""

from __future__ import annotations

import pandas as pd

from data.schema import (
    ALLOWED_SOURCE_TYPES,
    COLUMN_SPECS,
    CROP,
    OBSERVATION_COLUMNS,
    TARGET_COLUMN,
)


def structure_summary(df: pd.DataFrame) -> dict:
    """Row, column, and key-cardinality counts."""
    summary = {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "duplicate_rows": int(df.duplicated().sum()),
    }
    for column in ("record_id", "farm_id", "season", "ward", "crop", "data_source_type"):
        if column in df.columns:
            summary[f"unique_{column}"] = int(df[column].nunique(dropna=True))
    return summary


def missing_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Missing count and percent for every column."""
    row_count = len(df)
    rows = []
    for column in df.columns:
        missing = int(df[column].isna().sum())
        rows.append(
            {
                "column": column,
                "dtype": str(df[column].dtype),
                "missing_count": missing,
                "missing_percent": round(100 * missing / row_count, 2) if row_count else 0.0,
                "non_missing_count": row_count - missing,
            }
        )
    return pd.DataFrame(rows)


def duplicate_summary(df: pd.DataFrame) -> dict:
    """Exact duplicate rows, and repeated record identifiers."""
    exact = int(df.duplicated().sum())
    repeated_ids = 0
    if "record_id" in df.columns:
        repeated_ids = int(df["record_id"].duplicated().sum())
    return {
        "exact_duplicate_rows": exact,
        "rows_with_a_repeated_record_id": repeated_ids,
    }


def range_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Count values outside the schema's plausible and physical bounds."""
    rows = []
    for column, spec in COLUMN_SPECS.items():
        if column not in df.columns or "plausible_min" not in spec:
            continue
        series = pd.to_numeric(df[column], errors="coerce")
        present = series.notna()
        plausible = present & (
            (series < spec["plausible_min"]) | (series > spec["plausible_max"])
        )
        physical = present & (
            (series < spec["physical_min"]) | (series > spec["physical_max"])
        )
        rows.append(
            {
                "column": column,
                "unit": spec["unit"],
                "non_missing": int(present.sum()),
                "outside_plausible_range": int(plausible.sum()),
                "outside_physical_range": int(physical.sum()),
                "plausible_min": spec["plausible_min"],
                "plausible_max": spec["plausible_max"],
            }
        )
    return pd.DataFrame(rows)


def consistency_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Logical checks that do not delete or impute any values."""
    checks: list[dict] = []

    temperature_cols = ["min_temperature_c", "avg_temperature_c", "max_temperature_c"]
    if all(column in df.columns for column in temperature_cols):
        subset = df.dropna(subset=temperature_cols)
        ordered = (
            (subset["min_temperature_c"] <= subset["avg_temperature_c"])
            & (subset["avg_temperature_c"] <= subset["max_temperature_c"])
        )
        checks.append(
            {
                "check": "min_temperature <= avg_temperature <= max_temperature",
                "rows_evaluated": int(len(subset)),
                "failures": int((~ordered).sum()),
            }
        )

    if "crop" in df.columns:
        present = df["crop"].dropna()
        failures = int((present.str.lower() != CROP).sum()) if len(present) else 0
        checks.append(
            {
                "check": "crop is maize",
                "rows_evaluated": int(len(present)),
                "failures": failures,
            }
        )

    if "data_source_type" in df.columns:
        present = df["data_source_type"].dropna()
        failures = int((~present.isin(ALLOWED_SOURCE_TYPES)).sum())
        checks.append(
            {
                "check": "data_source_type is REAL, SYNTHETIC, or EXTERNAL",
                "rows_evaluated": int(len(present)),
                "failures": failures,
            }
        )

    if "yield_t_ha" in df.columns:
        present = pd.to_numeric(df["yield_t_ha"], errors="coerce").notna().sum()
        checks.append(
            {
                "check": "target yield_t_ha is present",
                "rows_evaluated": int(len(df)),
                "failures": int(len(df) - present),
            }
        )

    return pd.DataFrame(checks)


def source_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Row counts by provenance columns."""
    if "data_source_type" not in df.columns:
        return pd.DataFrame(columns=["data_source_type", "data_source", "rows"])
    counts = (
        df.groupby(["data_source_type", "data_source"], dropna=False)
        .size()
        .reset_index(name="rows")
    )
    return counts.sort_values(["data_source_type", "data_source"]).reset_index(drop=True)


def format_quality_report(df: pd.DataFrame) -> str:
    """Plain-text structure and quality report for the CLI and notebook output."""
    structure = structure_summary(df)
    missing = missing_summary(df)
    duplicates = duplicate_summary(df)
    ranges = range_summary(df)
    consistency = consistency_summary(df)
    sources = source_summary(df)

    lines = [
        "SMARTCROP DATASET STRUCTURE AND QUALITY SUMMARY",
        "=" * 52,
        "Study area label: Macheke, Mashonaland East, Zimbabwe",
        f"Crop: {CROP}",
        f"Target: {TARGET_COLUMN} (tonnes per hectare)",
        "",
        f"Rows: {structure['rows']}",
        f"Columns: {structure['columns']}",
        "",
        "Schema columns present: "
        + (
            "yes"
            if all(column in df.columns for column in OBSERVATION_COLUMNS)
            else "no"
        ),
        "",
        "Missing values",
        "--------------",
    ]
    for row in missing.itertuples(index=False):
        if row.missing_count:
            lines.append(
                f"  {row.column}: {row.missing_count} ({row.missing_percent}%)"
            )
    if int(missing["missing_count"].sum()) == 0:
        lines.append("  none")

    lines.extend(
        [
            "",
            "Duplicates",
            "----------",
            f"  exact duplicate rows: {duplicates['exact_duplicate_rows']}",
            f"  rows with a repeated record_id: {duplicates['rows_with_a_repeated_record_id']}",
            "",
            "Source types",
            "------------",
        ]
    )
    if sources.empty:
        lines.append("  none")
    else:
        for row in sources.itertuples(index=False):
            lines.append(
                f"  {row.data_source_type} | {row.data_source}: {row.rows}"
            )

    lines.extend(["", "Values outside plausible range", "-----------------------------"])
    flagged = ranges.loc[ranges["outside_plausible_range"] > 0]
    if flagged.empty:
        lines.append("  none")
    else:
        for row in flagged.itertuples(index=False):
            lines.append(
                f"  {row.column} ({row.unit}): {row.outside_plausible_range} "
                f"of {row.non_missing} non-missing"
            )

    lines.extend(["", "Consistency checks", "------------------"])
    for row in consistency.itertuples(index=False):
        lines.append(
            f"  {row.check}: {row.failures} failures in {row.rows_evaluated} rows"
        )

    if "season" in df.columns:
        lines.extend(["", "Rows by season", "--------------"])
        for season, count in df["season"].value_counts(dropna=False).sort_index().items():
            lines.append(f"  {season}: {count}")

    if "ward" in df.columns:
        lines.extend(["", "Rows by ward", "------------"])
        for ward, count in df["ward"].value_counts(dropna=False).sort_index().items():
            lines.append(f"  {ward}: {count}")

    lines.extend(
        [
            "",
            "These checks describe the file. They do not impute, delete, or clip values.",
        ]
    )
    return "\n".join(lines)
