"""SoilGrids 2.0 point query. Values are spatial predictions, not farm samples."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlencode

import pandas as pd

from utils.config import data_dir, load_config
from utils.downloads import fetch_json
from utils.logging import get_logger

LOG = get_logger()
QUERY = "https://rest.isric.org/soilgrids/v2.0/properties/query"

# Names used after dividing the mapped value by the API d_factor.
PROPERTY_COLUMNS = {
    "phh2o": "soil_ph",
    "nitrogen": "soil_nitrogen_g_kg",
    "soc": "soil_organic_carbon_g_kg",
    "clay": "soil_clay_pct",
    "sand": "soil_sand_pct",
    "silt": "soil_silt_pct",
    "cec": "soil_cec_cmol_kg",
    "bdod": "soil_bulk_density_g_cm3",
}


def _url(config: dict, prop: str, depth: str) -> str:
    area = config["study_area"]
    query = urlencode(
        {
            "lon": area["longitude"],
            "lat": area["latitude"],
            "property": prop,
            "depth": depth,
            "value": "mean",
        }
    )
    return f"{QUERY}?{query}"


def _points(payload: dict, prop: str) -> list[dict]:
    geometry = payload.get("geometry", {}).get("coordinates", [None, None])
    rows = []
    for layer in payload.get("properties", {}).get("layers", []):
        factor = float(layer.get("unit_measure", {}).get("d_factor") or 1)
        units = layer.get("unit_measure", {})
        for depth in layer.get("depths", []):
            values = depth.get("values") or {}
            mean = values.get("mean")
            converted = None if mean is None else float(mean) / factor
            if layer["name"] in {"clay", "sand", "silt"} and converted is not None and converted > 100:
                # SoilGrids mass fractions are g/kg. Percent is g/kg / 10.
                converted = converted / 10.0
            rows.append(
                {
                    "latitude": geometry[1],
                    "longitude": geometry[0],
                    "soilgrids_cell": f"{geometry[1]:.5f},{geometry[0]:.5f}",
                    "property": layer["name"],
                    "column": PROPERTY_COLUMNS.get(layer["name"], layer["name"]),
                    "depth": depth.get("label"),
                    "quantile": "mean",
                    "value_mapped": mean,
                    "d_factor": factor,
                    "mapped_units": units.get("mapped_units"),
                    "target_units": units.get("target_units"),
                    "value": converted,
                }
            )
    if not rows and prop:
        LOG.warning("SoilGrids returned no depths for %s", prop)
    return rows


def acquire_soilgrids(config: dict | None = None) -> pd.DataFrame:
    config = config or load_config()
    raw_dir = data_dir() / "raw" / "soilgrids"
    raw_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    LOG.info("SoilGrids acquisition started")
    for prop in config["soilgrids"]["properties"]:
        for depth in config["soilgrids"]["depths"]:
            dest = raw_dir / f"{prop}_{depth.replace('-', '_')}.json"
            url = _url(config, prop, depth)
            (raw_dir / f"{prop}_{depth.replace('-', '_')}.request.txt").write_text(url + "\n", encoding="utf-8")
            try:
                _status, payload = fetch_json(url, dest)
            except Exception as exc:  # noqa: BLE001
                LOG.warning("SoilGrids %s %s failed: %s", prop, depth, exc)
                continue
            frame = pd.DataFrame(_points(payload, prop))
            frames.append(frame)
            LOG.info("SoilGrids %s %s rows: %s", prop, depth, len(frame))
    points = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    out = data_dir() / "processed" / "soilgrids_points.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    points.to_csv(out, index=False)
    points.to_csv(data_dir() / "interim" / "soilgrids_points.csv", index=False)
    (raw_dir / "retrieved_at.txt").write_text(datetime.now(timezone.utc).isoformat() + "\n", encoding="utf-8")
    (raw_dir / "conversion_note.txt").write_text(
        "Mapped SoilGrids means are divided by unit_measure.d_factor. "
        "Clay, sand, and silt are then divided by 10 when the result is still above 100, "
        "because those properties are stored as g/kg and the project column is percent. "
        "These are 250 m predictions, not farm laboratory results.\n",
        encoding="utf-8",
    )
    LOG.info("SoilGrids point rows: %s", len(points))
    return points
