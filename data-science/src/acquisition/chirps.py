"""CHIRPS rainfall for the study-area box via the SERVIR ClimateSERV subset API."""

from __future__ import annotations

import json
import time
import urllib.parse
from datetime import datetime, timezone

import pandas as pd

from utils.config import data_dir, load_config
from utils.downloads import fetch_bytes, fetch_json
from utils.logging import get_logger

LOG = get_logger()
SUBMIT = "https://climateserv.servirglobal.net/api/submitDataRequest/"
PROGRESS = "https://climateserv.servirglobal.net/api/getDataRequestProgress/"
RESULT = "https://climateserv.servirglobal.net/api/getDataFromRequest/"


def _geometry(config: dict) -> str:
    box = config["study_area"]["bbox"]
    ring = [
        [box["min_lon"], box["min_lat"]],
        [box["max_lon"], box["min_lat"]],
        [box["max_lon"], box["max_lat"]],
        [box["min_lon"], box["max_lat"]],
        [box["min_lon"], box["min_lat"]],
    ]
    return json.dumps({"type": "Polygon", "coordinates": [ring]})


def _submit(config: dict, year: int) -> str:
    payload = urllib.parse.urlencode(
        {
            "datatype": str(config["chirps"]["climateserv_datatype"]),
            "begintime": f"01/01/{year}",
            "endtime": f"12/31/{year}",
            "intervaltype": "0",
            "operationtype": "5",
            "geometry": _geometry(config),
        }
    ).encode()
    _status, body = fetch_bytes(SUBMIT, data=payload, force=True)
    parsed = json.loads(body.decode("utf-8"))
    if isinstance(parsed, list):
        return str(parsed[0])
    if isinstance(parsed, dict) and "id" in parsed:
        return str(parsed["id"])
    raise RuntimeError(f"ClimateSERV did not return a request id: {parsed!r}"[:300])


def _wait(request_id: str) -> None:
    for _ in range(40):
        _status, progress = fetch_json(f"{PROGRESS}?id={request_id}", force=True)
        if isinstance(progress, list) and progress and float(progress[0]) >= 100:
            return
        time.sleep(3)
    raise RuntimeError(f"ClimateSERV request {request_id} did not finish.")


def _rows(payload: dict, year: int) -> list[dict]:
    rows = []
    for item in payload.get("data", []):
        value = item.get("raw_value")
        if value is None and isinstance(item.get("value"), dict):
            value = item["value"].get("avg")
        rows.append(
            {
                "date": item.get("isodate") or item.get("date"),
                "rainfall_mm": None if value is None else float(value),
                "year_file": year,
            }
        )
    return rows


def acquire_chirps(config: dict | None = None) -> pd.DataFrame:
    config = config or load_config()
    raw_dir = data_dir() / "raw" / "chirps"
    raw_dir.mkdir(parents=True, exist_ok=True)
    start = int(config["years"]["start"]) - 1
    end = int(config["years"]["end"])
    frames = []
    LOG.info("CHIRPS acquisition started for %s-%s", start, end)
    for year in range(start, end + 1):
        dest = raw_dir / f"chirps_daily_{year}.json"
        if dest.is_file() and dest.stat().st_size > 50:
            payload = json.loads(dest.read_text(encoding="utf-8"))
            LOG.info("CHIRPS cache hit %s", year)
        else:
            request_id = _submit(config, year)
            (raw_dir / f"chirps_daily_{year}.request_id.txt").write_text(request_id + "\n", encoding="utf-8")
            _wait(request_id)
            _status, payload = fetch_json(f"{RESULT}?id={request_id}", dest, force=True)
            time.sleep(float(config["chirps"]["sleep_seconds"]))
        frame = pd.DataFrame(_rows(payload, year))
        frames.append(frame)
        LOG.info("CHIRPS records downloaded for %s: %s", year, len(frame))
    daily = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not daily.empty:
        daily["date"] = pd.to_datetime(daily["date"], format="mixed").dt.date.astype(str)
    interim = data_dir() / "interim" / "chirps_daily.csv"
    daily.to_csv(interim, index=False)
    (raw_dir / "retrieved_at.txt").write_text(datetime.now(timezone.utc).isoformat() + "\n", encoding="utf-8")
    LOG.info("CHIRPS daily rows: %s", len(daily))
    return daily
