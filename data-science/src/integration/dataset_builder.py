"""Build the real SmartCrop table. Yield is copied from an agricultural source only."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

from integration.spatial_join import attach_soil
from integration.temporal_join import aggregate_chirps, aggregate_nasa
from utils.config import data_dir, load_config
from utils.logging import get_logger
from validation.provenance import provenance_frame
from validation.quality import apply_quality_flags, duplicate_mask
from validation.schema import REAL_COLUMNS

LOG = get_logger()


def _study_boundary(config: dict) -> None:
    box = config["study_area"]["bbox"]
    polygon = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Macheke study-area approximation",
                    "boundary_status": config["study_area"]["boundary_status"],
                    "note": config["study_area"]["boundary_note"],
                    "country": config["study_area"]["country"],
                    "province": config["study_area"]["province"],
                    "district": config["study_area"]["district"],
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [box["min_lon"], box["min_lat"]],
                        [box["max_lon"], box["min_lat"]],
                        [box["max_lon"], box["max_lat"]],
                        [box["min_lon"], box["max_lat"]],
                        [box["min_lon"], box["min_lat"]],
                    ]],
                },
            }
        ],
    }
    path = data_dir() / "external" / "macheke_boundary.geojson"
    path.write_text(json.dumps(polygon, indent=2), encoding="utf-8")


def _load_csv(path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def build_real_dataset(config: dict | None = None) -> pd.DataFrame:
    config = config or load_config()
    root = data_dir()
    _study_boundary(config)
    nasa_daily = _load_csv(root / "interim" / "nasa_power_daily.csv")
    chirps_daily = _load_csv(root / "interim" / "chirps_daily.csv")
    soil = _load_csv(root / "processed" / "soilgrids_points.csv")
    agriculture = _load_csv(root / "interim" / "agricultural_observations.csv")
    nasa_season = aggregate_nasa(nasa_daily, config)
    chirps_season = aggregate_chirps(chirps_daily, config)
    nasa_season.to_csv(root / "processed" / "nasa_power_seasonal.csv", index=False)
    chirps_season.to_csv(root / "processed" / "chirps_seasonal.csv", index=False)

    if nasa_season.empty and chirps_season.empty:
        seasons = pd.DataFrame(columns=["year", "season"])
    elif nasa_season.empty:
        seasons = chirps_season.copy()
    elif chirps_season.empty:
        seasons = nasa_season.copy()
    else:
        seasons = nasa_season.merge(chirps_season, on=["year", "season"], how="outer")

    seasons = attach_soil(seasons, soil, config["soilgrids"]["selected_depth"])
    area = config["study_area"]
    seasons["latitude"] = area["latitude"]
    seasons["longitude"] = area["longitude"]
    seasons["country"] = area["country"]
    seasons["province"] = area["province"]
    seasons["district"] = area["district"]
    seasons["location"] = area["location_label"]
    seasons["geographic_level"] = "grid_cell"
    seasons["crop"] = config["crop"]["name"]
    seasons["ward"] = pd.NA
    seasons["farm_id"] = pd.NA

    # Rainfall prefers CHIRPS. NASA precipitation is kept only when CHIRPS is absent.
    if "chirps_season_rainfall_mm" in seasons.columns:
        seasons["season_rainfall_mm"] = seasons["chirps_season_rainfall_mm"]
        seasons["critical_period_rainfall_mm"] = seasons["chirps_critical_period_rainfall_mm"]
        seasons["rainfall_days"] = seasons["chirps_rainfall_days"]
        seasons["rainfall_cv"] = seasons["chirps_rainfall_cv"]
        missing_chirps = seasons["season_rainfall_mm"].isna()
        if "nasa_season_rainfall_mm" in seasons.columns:
            seasons.loc[missing_chirps, "season_rainfall_mm"] = seasons.loc[missing_chirps, "nasa_season_rainfall_mm"]
            seasons.loc[missing_chirps, "critical_period_rainfall_mm"] = seasons.loc[missing_chirps, "nasa_critical_period_rainfall_mm"]
            seasons.loc[missing_chirps, "rainfall_days"] = seasons.loc[missing_chirps, "nasa_rainfall_days"]
            seasons.loc[missing_chirps, "rainfall_cv"] = seasons.loc[missing_chirps, "nasa_rainfall_cv"]
    elif "nasa_season_rainfall_mm" in seasons.columns:
        seasons["season_rainfall_mm"] = seasons["nasa_season_rainfall_mm"]
        seasons["critical_period_rainfall_mm"] = seasons["nasa_critical_period_rainfall_mm"]
        seasons["rainfall_days"] = seasons["nasa_rainfall_days"]
        seasons["rainfall_cv"] = seasons["nasa_rainfall_cv"]
    if "season_rainfall_mm" not in seasons.columns:
        seasons["season_rainfall_mm"] = pd.NA
    seasons["growing_season_rainfall_mm"] = seasons["season_rainfall_mm"]

    start, end = int(config["years"]["start"]), int(config["years"]["end"])
    seasons = seasons.loc[seasons["year"].between(start, end)].copy()

    if not agriculture.empty and "geographic_level" in agriculture.columns:
        keep_cols = [column for column in ["year", "yield_t_ha", "yield_original_value", "yield_original_unit", "yield_conversion_formula", "production_tonnes", "faostat_flag", "data_source", "source_url", "source_dataset", "retrieved_at"] if column in agriculture.columns]
        national = agriculture.loc[agriculture["geographic_level"] == "national", keep_cols].copy()
        national = national.drop_duplicates("year")
        national = national.rename(columns={"data_source": "yield_source", "retrieved_at": "yield_retrieved_at"})
        national["yield_geographic_level"] = "national"
        seasons = seasons.merge(national, on="year", how="left")
    else:
        seasons["yield_geographic_level"] = pd.NA

    seasons["data_source"] = "NASA POWER; CHIRPS; SoilGrids 2.0; FAOSTAT"
    seasons["data_source_type"] = "integrated"
    seasons["source_url"] = "https://power.larc.nasa.gov/; https://climateserv.servirglobal.net/; https://rest.isric.org/soilgrids/v2.0/properties/query; https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Africa.zip"
    seasons["source_dataset"] = "POWER Daily; CHIRPS via ClimateSERV; SoilGrids 2.0; FAOSTAT Production Crops Livestock Africa"
    seasons["source_version"] = "POWER daily point; ClimateSERV datatype 0; SoilGrids 2.0; FAOSTAT Africa bulk"
    seasons["source_date"] = seasons["yield_retrieved_at"] if "yield_retrieved_at" in seasons.columns else pd.NA
    seasons["retrieved_at"] = datetime.now(timezone.utc).date().isoformat()
    seasons["spatial_resolution"] = "weather/soil: study-area grid; yield: Zimbabwe national"
    seasons["temporal_resolution"] = "seasonal climate joined to annual national statistics"
    seasons["synthetic_record"] = False
    seasons["soil_depth_cm"] = config["soilgrids"]["selected_depth"]
    seasons["notes"] = (
        "Climate and soil describe the Macheke study-area grid. "
        "yield_t_ha, when present, is FAOSTAT national Maize (corn) for Zimbabwe, not a Macheke farm measurement. "
        "The study-area box is an approximation, not an official district boundary. "
        + config["season"]["assumption"]
    )
    if "faostat_flag" in seasons.columns:
        estimated = seasons["faostat_flag"].astype(str).str.upper().eq("E")
        seasons.loc[estimated, "notes"] = seasons.loc[estimated, "notes"] + " FAOSTAT flag E marks that national yield as an FAO estimate."

    seasons = seasons.sort_values("year")
    seasons.insert(0, "record_id", [f"REAL-{int(year)}" for year in seasons["year"]])
    duplicated = duplicate_mask(seasons)
    seasons["quality_flag"] = pd.NA
    seasons.loc[duplicated, "quality_flag"] = "DUPLICATE"
    seasons = apply_quality_flags(seasons)
    for column in REAL_COLUMNS:
        if column not in seasons.columns:
            seasons[column] = pd.NA
    seasons = seasons.loc[:, REAL_COLUMNS]

    processed = root / "processed"
    csv_path = processed / "capstone_dataset_real.csv"
    seasons.to_csv(csv_path, index=False)
    seasons.to_excel(processed / "capstone_dataset_real.xlsx", index=False)
    model_rows = seasons.loc[seasons["yield_t_ha"].notna()].copy()
    model_rows.to_csv(processed / "modelling_dataset.csv", index=False)
    duplicates = seasons.loc[seasons["quality_flag"].astype(str).str.contains("DUPLICATE")]
    duplicates.to_csv(root / "reports" / "duplicate_records.csv", index=False)

    stamp = datetime.now(timezone.utc).isoformat()
    provenance_frame(
        {
            "nasa_daily": len(nasa_daily),
            "chirps_daily": len(chirps_daily),
            "soilgrids": len(soil),
            "faostat": int((agriculture["geographic_level"] == "national").sum()) if not agriculture.empty and "geographic_level" in agriculture.columns else 0,
        },
        stamp,
    ).to_csv(root / "metadata" / "provenance.csv", index=False)
    manifest = {
        "dataset_name": "SmartCrop Macheke Maize Yield Dataset",
        "dataset_version": "2.0.0-real",
        "study_area": "Macheke, Mashonaland East, Zimbabwe",
        "crop": "maize",
        "synthetic_records": int(seasons["synthetic_record"].sum()),
        "real_records": int(len(seasons)),
        "yield_records": int(seasons["yield_t_ha"].notna().sum()),
        "farm_level_yield_records": int(((seasons["yield_geographic_level"] == "farm") & seasons["yield_t_ha"].notna()).sum()) if "yield_geographic_level" in seasons.columns else 0,
        "sources": ["NASA POWER", "CHIRPS", "SoilGrids 2.0", "FAOSTAT"],
        "created_at": stamp,
        "generated_by": "SmartCrop data acquisition pipeline",
        "boundary_status": config["study_area"]["boundary_status"],
    }
    (root / "metadata" / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    LOG.info("Real dataset rows: %s yield rows: %s", manifest["real_records"], manifest["yield_records"])
    return seasons
