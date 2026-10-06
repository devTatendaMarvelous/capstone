"""Collect yield tables that already exist. Never estimate yield from weather."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from acquisition.faostat import acquire_faostat
from utils.config import data_dir
from utils.logging import get_logger

LOG = get_logger()


def read_farm_survey(path: Path | None = None) -> pd.DataFrame:
    """Convert a real survey file when one is supplied. Do not create one."""
    path = path or (data_dir() / "raw" / "farm_survey.csv")
    if not path.is_file():
        LOG.info("No farm survey file at %s", path)
        return pd.DataFrame()
    frame = pd.read_csv(path)
    required = {"yield_kg", "farm_area_ha"}
    if not required.issubset(frame.columns):
        raise ValueError("farm_survey.csv must include yield_kg and farm_area_ha from the survey itself.")
    out = frame.copy()
    out["yield_original_value"] = pd.to_numeric(out["yield_kg"], errors="coerce")
    out["yield_original_unit"] = "kg on the reported area"
    area = pd.to_numeric(out["farm_area_ha"], errors="coerce")
    out["yield_t_ha"] = out["yield_original_value"] / area / 1000.0
    out["yield_conversion_formula"] = "yield_kg / farm_area_ha / 1000"
    out["geographic_level"] = "farm"
    out["data_source"] = "farm_survey"
    out["data_source_type"] = "agricultural_survey"
    out.loc[area.isna() | (area <= 0) | out["yield_original_value"].isna(), "yield_t_ha"] = pd.NA
    return out


def acquire_yield_tables(config: dict | None = None) -> pd.DataFrame:
    faostat = acquire_faostat(config)
    survey = read_farm_survey()
    frames = [frame for frame in (faostat, survey) if not frame.empty]
    combined = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    combined.to_csv(data_dir() / "interim" / "agricultural_observations.csv", index=False)
    LOG.info("Agricultural yield rows: %s", len(combined))
    return combined
