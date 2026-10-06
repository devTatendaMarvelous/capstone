"""Synthetic farm-season maize observations for pipeline development.

The generator builds a reproducible panel of fictional farms in the Macheke
study area. Relationships between weather, soil, management, and yield are
simplified assumptions so later notebooks have something structured to clean
and model. They are not a calibrated crop model and they are not estimates
for any real farm.

Every observation is labelled ``data_source_type = SYNTHETIC``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from data.quality import format_quality_report
from data.schema import (
    COLUMN_SPECS,
    COUNTRY,
    CROP,
    LOCATION,
    OBSERVATION_COLUMNS,
    PROVINCE,
    PROTECTED_COLUMNS,
    SCHEMA_VERSION,
    SYNTHETIC_DISCLAIMER,
    nullable_feature_columns,
)
from data.sources import build_source_catalogue

DATA_SOURCE_NAME = "smartcrop_synthetic_generator_v1"
GENERATOR_VERSION = "1.0.0"

# Invented soil baselines so wards differ. These are not survey results.
WARD_SOIL_BASELINE = {
    "SYN-W01": {"soil_ph": 5.3, "soil_nitrogen": 0.08, "soil_organic_carbon": 0.70},
    "SYN-W02": {"soil_ph": 5.6, "soil_nitrogen": 0.10, "soil_organic_carbon": 0.90},
    "SYN-W03": {"soil_ph": 5.9, "soil_nitrogen": 0.12, "soil_organic_carbon": 1.10},
    "SYN-W04": {"soil_ph": 6.1, "soil_nitrogen": 0.13, "soil_organic_carbon": 1.25},
    "SYN-W05": {"soil_ph": 5.5, "soil_nitrogen": 0.09, "soil_organic_carbon": 0.80},
    "SYN-W06": {"soil_ph": 6.3, "soil_nitrogen": 0.14, "soil_organic_carbon": 1.40},
}

DEFAULTS = {
    "number_of_records": 960,
    "number_of_seasons": 8,
    "random_seed": 42,
    "missing_rate": 0.03,
    "outlier_rate": 0.02,
    "duplicate_rate": 0.015,
    "start_season_year": 2016,
}


def data_science_root() -> Path:
    """Return the ``data-science`` directory that contains this package."""
    return Path(__file__).resolve().parents[2]


def _validate_params(
    number_of_records: int,
    number_of_seasons: int,
    missing_rate: float,
    outlier_rate: float,
    duplicate_rate: float,
) -> None:
    if number_of_seasons < 1:
        raise ValueError("number_of_seasons must be at least 1.")
    if number_of_records < number_of_seasons:
        raise ValueError("number_of_records must be at least number_of_seasons.")
    if not 0 <= missing_rate < 0.5:
        raise ValueError("missing_rate must be in [0, 0.5).")
    if not 0 <= outlier_rate < 0.2:
        raise ValueError("outlier_rate must be in [0, 0.2).")
    if not 0 <= duplicate_rate < 0.2:
        raise ValueError("duplicate_rate must be in [0, 0.2).")


def _rainfall_suitability(rainfall_mm: np.ndarray) -> np.ndarray:
    """Map seasonal rainfall to a 0–1 score peaking between about 700 and 900 mm."""
    rainfall = np.asarray(rainfall_mm, dtype=float)
    rising = np.clip((rainfall - 300.0) / 400.0, 0.0, 1.0)
    falling = np.clip((1300.0 - rainfall) / 400.0, 0.0, 1.0)
    return np.minimum(rising, falling)


def _bounded_score(center: np.ndarray, optimum: float, scale: float) -> np.ndarray:
    z = (np.asarray(center, dtype=float) - optimum) / scale
    return np.exp(-0.5 * z**2)


def _yield_tonnes_per_ha(
    rainfall_mm: np.ndarray,
    avg_temperature_c: np.ndarray,
    max_temperature_c: np.ndarray,
    soil_ph: np.ndarray,
    soil_nitrogen: np.ndarray,
    soil_organic_carbon: np.ndarray,
    fertilizer_kg_ha: np.ndarray,
    planting_day: np.ndarray,
    season_shock: np.ndarray,
    noise: np.ndarray,
) -> np.ndarray:
    """Apply the documented synthetic yield assumptions. Not a crop model."""
    rain_score = _rainfall_suitability(rainfall_mm)
    temp_score = _bounded_score(avg_temperature_c, optimum=24.0, scale=3.2)
    ph_score = _bounded_score(soil_ph, optimum=6.1, scale=0.7)
    nitrogen_score = np.clip((soil_nitrogen - 0.04) / 0.12, 0.0, 1.0)
    carbon_score = np.clip(soil_organic_carbon / 1.6, 0.0, 1.0)
    fertilizer_score = 1.0 - np.exp(-np.asarray(fertilizer_kg_ha, dtype=float) / 120.0)
    planting_score = np.clip(
        1.0 - np.abs(np.asarray(planting_day, dtype=float) - 30.0) / 45.0,
        0.05,
        1.0,
    )
    heat = np.clip((np.asarray(max_temperature_c, dtype=float) - 33.0) / 6.0, 0.0, 1.0)
    drought = np.clip((480.0 - np.asarray(rainfall_mm, dtype=float)) / 200.0, 0.0, 1.0)

    # Weights are an invented response, not a crop-growth equation.
    # Rainfall and fertilizer move yield the most. Late planting and very
    # low rainfall reduce it. A rainfall total far above the peak is already
    # reduced by rain_score.
    yield_t_ha = (
        0.20
        + 1.10 * rain_score
        + 0.55 * fertilizer_score
        + 0.45 * planting_score
        + 0.10 * temp_score
        + 0.08 * ph_score
        + 0.08 * nitrogen_score
        + 0.05 * carbon_score
        - 0.15 * heat
        - 0.35 * drought
        + season_shock
        + noise
    )
    return np.clip(yield_t_ha, 0.05, 6.5)


def _season_table(number_of_seasons: int, start_season_year: int, rng: np.random.Generator) -> pd.DataFrame:
    """One row per synthetic season, with a shared weather level."""
    rows = []
    # Spread seasons from drier to wetter, then shuffle. The spread is a
    # generator choice so notebooks can see rainfall differences. It is not
    # the historical rainfall of these calendar years.
    quantiles = (np.arange(number_of_seasons) + 0.5) / number_of_seasons
    rain_span = 400 + (1000 - 400) * quantiles
    rain_means = rain_span[rng.permutation(number_of_seasons)]
    rain_means = np.clip(rain_means + rng.normal(0, 20, size=number_of_seasons), 320, 1100)
    temp_means = np.clip(rng.normal(23.5, 0.6, size=number_of_seasons), 21.5, 26.5)
    shocks = rng.normal(0.0, 0.10, size=number_of_seasons)
    for index in range(number_of_seasons):
        start = start_season_year + index
        rows.append(
            {
                "season": f"{start}/{start + 1}",
                "year": start + 1,
                "season_rainfall_mean_mm": float(rain_means[index]),
                "season_temperature_mean_c": float(temp_means[index]),
                "season_shock": float(shocks[index]),
            }
        )
    return pd.DataFrame(rows)


def _records_per_season(number_of_records: int, number_of_seasons: int) -> list[int]:
    base, extra = divmod(number_of_records, number_of_seasons)
    return [base + (1 if index < extra else 0) for index in range(number_of_seasons)]


def generate_dataset(
    number_of_records: int = DEFAULTS["number_of_records"],
    number_of_seasons: int = DEFAULTS["number_of_seasons"],
    random_seed: int = DEFAULTS["random_seed"],
    missing_rate: float = DEFAULTS["missing_rate"],
    outlier_rate: float = DEFAULTS["outlier_rate"],
    duplicate_rate: float = DEFAULTS["duplicate_rate"],
    start_season_year: int = DEFAULTS["start_season_year"],
) -> tuple[pd.DataFrame, dict]:
    """Generate labelled synthetic observations and a generation manifest.

    Parameters
    ----------
    number_of_records
        Farm-season rows before duplicate injection.
    number_of_seasons
        Number of consecutive synthetic seasons.
    random_seed
        Seed for ``numpy.random.Generator``. The same seed rebuilds the same file.
    missing_rate
        Independent probability that an eligible feature cell is blanked.
    outlier_rate
        Fraction of pre-duplicate rows that receive one extreme value.
    duplicate_rate
        Fraction of pre-duplicate rows appended again as exact copies.
    start_season_year
        First year of the first season label. Labels are not historical weather.

    Returns
    -------
    observations, manifest
        The observation frame includes injected missing values, outliers, and
        exact duplicate rows. The manifest is an audit log, not a data source
        for modelling.
    """
    _validate_params(
        number_of_records,
        number_of_seasons,
        missing_rate,
        outlier_rate,
        duplicate_rate,
    )
    rng = np.random.default_rng(random_seed)
    seasons = _season_table(number_of_seasons, start_season_year, rng)
    per_season = _records_per_season(number_of_records, number_of_seasons)
    farm_count = max(per_season)

    wards = np.array(list(WARD_SOIL_BASELINE))
    farm_ward = rng.choice(wards, size=farm_count)
    farm_area = np.clip(rng.lognormal(mean=np.log(1.2), sigma=0.45, size=farm_count), 0.3, 8.0)

    farm_soil = {}
    for ward in wards:
        baseline = WARD_SOIL_BASELINE[ward]
        members = np.flatnonzero(farm_ward == ward)
        farm_soil[ward] = {
            "soil_ph": baseline["soil_ph"] + rng.normal(0, 0.12, size=len(members)),
            "soil_nitrogen": baseline["soil_nitrogen"] + rng.normal(0, 0.01, size=len(members)),
            "soil_organic_carbon": baseline["soil_organic_carbon"] + rng.normal(0, 0.08, size=len(members)),
            "members": members,
        }

    soil_ph = np.empty(farm_count)
    soil_nitrogen = np.empty(farm_count)
    soil_organic_carbon = np.empty(farm_count)
    for ward, values in farm_soil.items():
        members = values["members"]
        soil_ph[members] = values["soil_ph"]
        soil_nitrogen[members] = values["soil_nitrogen"]
        soil_organic_carbon[members] = values["soil_organic_carbon"]
    soil_ph = np.clip(soil_ph, 4.6, 7.2)
    soil_nitrogen = np.clip(soil_nitrogen, 0.05, 0.22)
    soil_organic_carbon = np.clip(soil_organic_carbon, 0.4, 2.2)

    rows: list[dict] = []
    for season_index, season in seasons.iterrows():
        count = per_season[season_index]
        farm_index = np.arange(count)
        rainfall = np.clip(
            rng.normal(season["season_rainfall_mean_mm"], 55, size=count),
            180,
            1300,
        )
        avg_temp = np.clip(
            rng.normal(season["season_temperature_mean_c"], 0.7, size=count),
            18,
            30,
        )
        max_temp = avg_temp + rng.uniform(6.5, 10.5, size=count)
        hot = rng.random(count) < 0.08
        max_temp = max_temp + np.where(hot, rng.uniform(3.0, 6.0, size=count), 0.0)
        min_temp = avg_temp - rng.uniform(5.0, 8.5, size=count)

        uses_fertilizer = rng.random(count) < 0.78
        fertilizer = np.zeros(count)
        fertilizer[uses_fertilizer] = rng.lognormal(
            mean=np.log(90),
            sigma=0.55,
            size=int(uses_fertilizer.sum()),
        )
        fertilizer = np.clip(fertilizer, 0, 350)

        late = rng.random(count) < 0.18
        planting = np.empty(count)
        planting[~late] = rng.normal(28, 10, size=int((~late).sum()))
        planting[late] = rng.normal(68, 8, size=int(late.sum()))
        planting = np.clip(np.rint(planting), 1, 100)

        noise = rng.normal(0, 0.15, size=count)
        shock = np.full(count, season["season_shock"])
        yield_t_ha = _yield_tonnes_per_ha(
            rainfall,
            avg_temp,
            max_temp,
            soil_ph[farm_index],
            soil_nitrogen[farm_index],
            soil_organic_carbon[farm_index],
            fertilizer,
            planting,
            shock,
            noise,
        )

        for row_index in range(count):
            farm_id = f"F{farm_index[row_index] + 1:04d}"
            rows.append(
                {
                    "farm_id": farm_id,
                    "year": int(season["year"]),
                    "season": season["season"],
                    "country": COUNTRY,
                    "province": PROVINCE,
                    "location": LOCATION,
                    "ward": str(farm_ward[farm_index[row_index]]),
                    "crop": CROP,
                    "area_ha": round(float(farm_area[farm_index[row_index]]), 2),
                    "rainfall_mm": round(float(rainfall[row_index]), 1),
                    "avg_temperature_c": round(float(avg_temp[row_index]), 2),
                    "max_temperature_c": round(float(max_temp[row_index]), 2),
                    "min_temperature_c": round(float(min_temp[row_index]), 2),
                    "soil_ph": round(float(soil_ph[farm_index[row_index]]), 2),
                    "soil_nitrogen": round(float(soil_nitrogen[farm_index[row_index]]), 3),
                    "soil_organic_carbon": round(float(soil_organic_carbon[farm_index[row_index]]), 2),
                    "fertilizer_kg_ha": round(float(fertilizer[row_index]), 1),
                    "planting_day": int(planting[row_index]),
                    "yield_t_ha": round(float(yield_t_ha[row_index]), 3),
                    "data_source_type": "SYNTHETIC",
                    "data_source": DATA_SOURCE_NAME,
                    "schema_version": SCHEMA_VERSION,
                }
            )

    frame = pd.DataFrame(rows)
    if len(frame) != number_of_records:
        raise RuntimeError("Generated row count did not match number_of_records.")
    frame.insert(0, "record_id", [f"SC-SYN-{index + 1:06d}" for index in range(len(frame))])

    outlier_ids = _inject_outliers(frame, outlier_rate, rng)
    missing_cells = _inject_missing(frame, missing_rate, rng)
    frame, duplicate_ids = _inject_duplicates(frame, duplicate_rate, rng)
    frame = frame.sample(frac=1, random_state=random_seed).reset_index(drop=True)
    frame = frame.loc[:, OBSERVATION_COLUMNS]

    manifest = {
        "disclaimer": SYNTHETIC_DISCLAIMER,
        "generator_version": GENERATOR_VERSION,
        "schema_version": SCHEMA_VERSION,
        "data_source": DATA_SOURCE_NAME,
        "data_source_type": "SYNTHETIC",
        "study_area": {
            "location": LOCATION,
            "province": PROVINCE,
            "country": COUNTRY,
            "crop": CROP,
            "ward_codes_are_official": False,
            "season_labels_match_historical_weather": False,
        },
        "parameters": {
            "number_of_records": number_of_records,
            "number_of_seasons": number_of_seasons,
            "random_seed": random_seed,
            "missing_rate": missing_rate,
            "outlier_rate": outlier_rate,
            "duplicate_rate": duplicate_rate,
            "start_season_year": start_season_year,
        },
        "rows_before_duplicates": number_of_records,
        "rows_after_duplicates": int(len(frame)),
        "protected_columns": list(PROTECTED_COLUMNS),
        "columns_eligible_for_missing": nullable_feature_columns(),
        "outlier_record_ids": outlier_ids,
        "duplicate_record_ids": duplicate_ids,
        "missing_cell_count": len(missing_cells),
        "assumptions": [
            "Yield is an invented function of rainfall, temperature, soil, fertilizer, and planting day, plus noise.",
            "Season rainfall levels are spread from drier to wetter and then shuffled. They are not NASA POWER or CHIRPS values for those years.",
            "Ward soil baselines are invented so locations differ. They are not SoilGrids or laboratory results.",
            "Fertilizer is product kg/ha, not an elemental nutrient rate.",
            "planting_day 1 means 1 November. This is a project convention.",
            "Area does not enter the yield function. Yield is tonnes per hectare.",
        ],
    }
    return frame, manifest


def _inject_outliers(frame: pd.DataFrame, outlier_rate: float, rng: np.random.Generator) -> list[str]:
    """Replace one value on a sample of rows with an extreme but finite value."""
    count = int(round(outlier_rate * len(frame)))
    if count == 0:
        return []
    chosen = rng.choice(len(frame), size=count, replace=False)
    # A short menu of extremes. Some sit outside the plausible range and
    # remain inside a wide physical range so later range checks can see them.
    edits = [
        ("rainfall_mm", (1600.0, 1750.0)),
        ("rainfall_mm", (90.0, 140.0)),
        ("fertilizer_kg_ha", (650.0, 900.0)),
        ("yield_t_ha", (7.5, 9.0)),
        ("soil_ph", (8.2, 8.6)),
        ("avg_temperature_c", (35.0, 37.0)),
    ]
    record_ids: list[str] = []
    for position in chosen:
        column, (low, high) = edits[int(rng.integers(0, len(edits)))]
        value = float(rng.uniform(low, high))
        if column == "yield_t_ha":
            frame.iat[position, frame.columns.get_loc(column)] = round(value, 3)
        elif column == "soil_ph" or column == "avg_temperature_c":
            frame.iat[position, frame.columns.get_loc(column)] = round(value, 2)
        else:
            frame.iat[position, frame.columns.get_loc(column)] = round(value, 1)
        record_ids.append(str(frame.iat[position, frame.columns.get_loc("record_id")]))
    return record_ids


def _inject_missing(frame: pd.DataFrame, missing_rate: float, rng: np.random.Generator) -> list[dict]:
    """Blank eligible feature cells. Provenance and identity columns stay filled."""
    cells: list[dict] = []
    if missing_rate == 0:
        return cells
    eligible = nullable_feature_columns()
    for column in eligible:
        mask = rng.random(len(frame)) < missing_rate
        positions = np.flatnonzero(mask)
        if len(positions) == 0:
            continue
        frame.loc[frame.index[positions], column] = pd.NA
        for position in positions:
            cells.append(
                {
                    "record_id": str(frame.iat[position, frame.columns.get_loc("record_id")]),
                    "column": column,
                }
            )
    return cells


def _inject_duplicates(
    frame: pd.DataFrame,
    duplicate_rate: float,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, list[str]]:
    """Append exact copies, including the original record_id."""
    count = int(round(duplicate_rate * len(frame)))
    if count == 0:
        return frame, []
    chosen = rng.choice(len(frame), size=count, replace=False)
    copies = frame.iloc[chosen].copy()
    record_ids = copies["record_id"].astype(str).tolist()
    combined = pd.concat([frame, copies], ignore_index=True)
    return combined, record_ids


def _round_for_export(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply display rounding without filling missing values."""
    exported = frame.copy()
    for column, spec in COLUMN_SPECS.items():
        if spec["dtype"] != "float":
            continue
        decimals = 3 if column in {"soil_nitrogen", "yield_t_ha"} else 2
        if column in {"rainfall_mm", "fertilizer_kg_ha", "area_ha"}:
            decimals = 1 if column != "area_ha" else 2
        exported[column] = pd.to_numeric(exported[column], errors="coerce").round(decimals)
    if "planting_day" in exported.columns:
        exported["planting_day"] = pd.to_numeric(exported["planting_day"], errors="coerce").astype("Int64")
    if "year" in exported.columns:
        exported["year"] = pd.to_numeric(exported["year"], errors="coerce").astype("int64")
    return exported


def write_dataset_bundle(
    frame: pd.DataFrame,
    manifest: dict,
    root: Path | None = None,
) -> dict[str, Path]:
    """Write the synthetic master file, two raw batches, and the source catalogue.

    The two raw batches are a disjoint split of the same synthetic run so
    Notebook 01 can load CSV and Excel and consolidate them. They are not a
    second population.
    """
    root = data_science_root() if root is None else Path(root)
    synthetic_dir = root / "data" / "synthetic"
    raw_dir = root / "data" / "raw"
    external_dir = root / "data" / "external"
    for directory in (synthetic_dir, raw_dir, external_dir):
        directory.mkdir(parents=True, exist_ok=True)

    exported = _round_for_export(frame)
    master_csv = synthetic_dir / "macheke_maize_synthetic.csv"
    master_xlsx = synthetic_dir / "macheke_maize_synthetic.xlsx"
    manifest_path = synthetic_dir / "generation_manifest.json"
    batch_csv = raw_dir / "batch_a_farm_observations.csv"
    batch_xlsx = raw_dir / "batch_b_farm_observations.xlsx"
    catalogue_path = external_dir / "source_catalogue.csv"

    exported.to_csv(master_csv, index=False)
    exported.to_excel(master_xlsx, index=False, sheet_name="observations")
    midpoint = len(exported) // 2
    exported.iloc[:midpoint].to_csv(batch_csv, index=False)
    exported.iloc[midpoint:].to_excel(batch_xlsx, index=False, sheet_name="observations")
    build_source_catalogue().to_csv(catalogue_path, index=False)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return {
        "master_csv": master_csv,
        "master_xlsx": master_xlsx,
        "manifest": manifest_path,
        "batch_csv": batch_csv,
        "batch_xlsx": batch_xlsx,
        "source_catalogue": catalogue_path,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Prints a quality summary and writes the dataset bundle."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate a clearly labelled SYNTHETIC maize dataset for SmartCrop. "
            "The output is not Macheke agricultural measurement data."
        )
    )
    parser.add_argument("--number-of-records", type=int, default=DEFAULTS["number_of_records"])
    parser.add_argument("--number-of-seasons", type=int, default=DEFAULTS["number_of_seasons"])
    parser.add_argument("--random-seed", type=int, default=DEFAULTS["random_seed"])
    parser.add_argument("--missing-rate", type=float, default=DEFAULTS["missing_rate"])
    parser.add_argument("--outlier-rate", type=float, default=DEFAULTS["outlier_rate"])
    parser.add_argument("--duplicate-rate", type=float, default=DEFAULTS["duplicate_rate"])
    parser.add_argument("--start-season-year", type=int, default=DEFAULTS["start_season_year"])
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Directory that contains data/. Defaults to the data-science root.",
    )
    args = parser.parse_args(argv)

    frame, manifest = generate_dataset(
        number_of_records=args.number_of_records,
        number_of_seasons=args.number_of_seasons,
        random_seed=args.random_seed,
        missing_rate=args.missing_rate,
        outlier_rate=args.outlier_rate,
        duplicate_rate=args.duplicate_rate,
        start_season_year=args.start_season_year,
    )
    paths = write_dataset_bundle(frame, manifest, root=args.output_root)
    print(SYNTHETIC_DISCLAIMER)
    print()
    print(format_quality_report(frame))
    print()
    print("Files")
    print("-----")
    for label, path in paths.items():
        print(f"  {label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
