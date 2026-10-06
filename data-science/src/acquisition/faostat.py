"""FAOSTAT Zimbabwe maize statistics. National figures are not Macheke farm yields."""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone

import pandas as pd

from utils.config import data_dir, load_config
from utils.downloads import fetch_bytes
from utils.logging import get_logger

LOG = get_logger()
AFRICA_ZIP = "https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Africa.zip"
ELEMENT_YIELD = "Yield"
ELEMENT_PRODUCTION = "Production"
ELEMENT_AREA = "Area harvested"


def _wide_to_long(frame: pd.DataFrame) -> pd.DataFrame:
    year_columns = [column for column in frame.columns if column.startswith("Y") and column[1:5].isdigit() and len(column) == 5]
    flag_columns = {column: f"{column}F" for column in year_columns if f"{column}F" in frame.columns}
    id_columns = [column for column in ("Area Code", "Area", "Item Code", "Item", "Element Code", "Element", "Unit") if column in frame.columns]
    pieces = []
    for column in year_columns:
        part = frame.loc[:, id_columns + [column]].copy()
        part = part.rename(columns={column: "original_value"})
        part["year"] = int(column[1:])
        if column in flag_columns:
            part["faostat_flag"] = frame[flag_columns[column]].values
        else:
            part["faostat_flag"] = pd.NA
        pieces.append(part)
    long = pd.concat(pieces, ignore_index=True)
    long["original_value"] = pd.to_numeric(long["original_value"], errors="coerce")
    return long.dropna(subset=["original_value"])


def acquire_faostat(config: dict | None = None) -> pd.DataFrame:
    """Download the FAOSTAT Africa crop file and keep Zimbabwe maize (corn) only."""
    config = config or load_config()
    raw_dir = data_dir() / "raw" / "faostat"
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / "Production_Crops_Livestock_E_Africa.zip"
    LOG.info("FAOSTAT acquisition started")
    fetch_bytes(AFRICA_ZIP, dest)
    with zipfile.ZipFile(dest) as archive:
        member = "Production_Crops_Livestock_E_Africa.csv"
        text = archive.read(member).decode("utf-8", errors="replace")
    wide = pd.read_csv(io.StringIO(text), dtype=str)
    item_code = str(config["crop"]["faostat_item_code"])
    maize = wide.loc[
        (wide["Area"] == "Zimbabwe")
        & (wide["Item Code"].astype(str).str.replace(".0", "", regex=False) == item_code)
        & (wide["Element"].isin([ELEMENT_YIELD, ELEMENT_PRODUCTION, ELEMENT_AREA]))
    ].copy()
    long = _wide_to_long(maize)
    yield_rows = long.loc[long["Element"] == ELEMENT_YIELD].copy()
    production = long.loc[long["Element"] == ELEMENT_PRODUCTION, ["year", "original_value"]].rename(
        columns={"original_value": "production_tonnes"}
    )
    area = long.loc[long["Element"] == ELEMENT_AREA, ["year", "original_value"]].rename(
        columns={"original_value": "harvested_area_ha"}
    )
    table = yield_rows.merge(production, on="year", how="left").merge(area, on="year", how="left")
    unit = str(table["Unit"].iloc[0]) if not table.empty else ""
    if unit.lower() in {"kg/ha", "kg / ha"}:
        formula = "kg/ha / 1000"
        table["yield_t_ha"] = table["original_value"] / 1000.0
    elif unit.lower() in {"hg/ha", "hg / ha", "100 g/ha"}:
        formula = "hg/ha / 10000"
        table["yield_t_ha"] = table["original_value"] / 10000.0
    else:
        formula = f"unconverted unit: {unit}"
        table["yield_t_ha"] = pd.NA
        LOG.warning("FAOSTAT yield unit %r was not converted", unit)
    table["yield_original_value"] = table["original_value"]
    table["yield_original_unit"] = table["Unit"]
    table["yield_conversion_formula"] = formula
    table["geographic_level"] = "national"
    table["country"] = "Zimbabwe"
    table["crop"] = "maize"
    table["data_source"] = "FAOSTAT"
    table["source_dataset"] = member
    table["source_url"] = AFRICA_ZIP
    table["retrieved_at"] = datetime.now(timezone.utc).date().isoformat()
    keep = [
        "year",
        "country",
        "crop",
        "geographic_level",
        "yield_original_value",
        "yield_original_unit",
        "yield_conversion_formula",
        "yield_t_ha",
        "production_tonnes",
        "harvested_area_ha",
        "faostat_flag",
        "data_source",
        "source_dataset",
        "source_url",
        "retrieved_at",
    ]
    table = table.loc[:, keep].sort_values("year")
    out = data_dir() / "processed" / "faostat_zimbabwe_maize.csv"
    table.to_csv(out, index=False)
    LOG.info("FAOSTAT Zimbabwe maize (corn) years: %s", len(table))
    return table
