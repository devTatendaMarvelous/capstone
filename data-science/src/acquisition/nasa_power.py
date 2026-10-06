"""NASA POWER daily point data for the documented Macheke study coordinate."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlencode

import pandas as pd

from utils.config import data_dir, load_config
from utils.downloads import fetch_json
from utils.logging import get_logger

LOG = get_logger()
SOURCE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
FILL = -999.0


def _year_url(config: dict, year: int) -> str:
    area = config["study_area"]
    power = config["nasa_power"]
    query = urlencode(
        {
            "parameters": ",".join(power["parameters"]),
            "community": power["community"],
            "longitude": area["longitude"],
            "latitude": area["latitude"],
            "start": f"{year}0101",
            "end": f"{year}1231",
            "format": "JSON",
            "header": "true",
        }
    )
    return f"{SOURCE_URL}?{query}"


def _records_from_payload(payload: dict, year: int) -> list[dict]:
    parameters = payload.get("properties", {}).get("parameter", {})
    dates = set()
    for series in parameters.values():
        dates.update(series)
    rows = []
    for stamp in sorted(dates):
        row = {"date": datetime.strptime(stamp, "%Y%m%d").date().isoformat(), "year_file": year}
        for name, series in parameters.items():
            value = series.get(stamp)
            row[name] = None if value is None or float(value) <= FILL else float(value)
        rows.append(row)
    return rows


def acquire_nasa_power(config: dict | None = None) -> pd.DataFrame:
    config = config or load_config()
    raw_dir = data_dir() / "raw" / "nasa_power"
    raw_dir.mkdir(parents=True, exist_ok=True)
    start = int(config["years"]["start"]) - 1
    end = int(config["years"]["end"])
    frames = []
    metadata = []
    LOG.info("NASA POWER acquisition started for %s-%s", start, end)
    for year in range(start, end + 1):
        dest = raw_dir / f"power_daily_{year}.json"
        url = _year_url(config, year)
        _status, payload = fetch_json(url, dest)
        (raw_dir / f"power_daily_{year}.request.txt").write_text(url + "\n", encoding="utf-8")
        metadata.append(
            {
                "year": year,
                "url": url,
                "parameters": payload.get("parameters", {}),
                "header": payload.get("header", {}),
            }
        )
        frame = pd.DataFrame(_records_from_payload(payload, year))
        frames.append(frame)
        LOG.info("NASA POWER records downloaded for %s: %s", year, len(frame))
    daily = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    interim = data_dir() / "interim" / "nasa_power_daily.csv"
    daily.to_csv(interim, index=False)
    (raw_dir / "power_metadata.json").write_text(json.dumps(metadata, default=str)[:500000], encoding="utf-8")
    retrieved = datetime.now(timezone.utc).isoformat()
    (raw_dir / "retrieved_at.txt").write_text(retrieved + "\n", encoding="utf-8")
    LOG.info("NASA POWER daily rows: %s", len(daily))
    return daily
