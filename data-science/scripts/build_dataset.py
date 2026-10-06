"""Join downloaded sources into the real SmartCrop tables."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from integration.dataset_builder import build_real_dataset
from models.real_training import train_from_real_dataset
from utils.config import data_dir
from validation.reporting import write_acquisition_report, write_dictionary, write_source_catalogue

import pandas as pd


def main() -> int:
    frame = build_real_dataset()
    root = data_dir()
    statuses = {
        "nasa": {"records": _rows(root / "interim" / "nasa_power_daily.csv"), "notes": "Daily point data retained."},
        "chirps": {"records": _rows(root / "interim" / "chirps_daily.csv"), "notes": "ClimateSERV subset. Not a local CHIRPS v3 raster."},
        "soilgrids": {
            "records": _rows(root / "processed" / "soilgrids_points.csv"),
            "ingestion_status": "ingested" if _rows(root / "processed" / "soilgrids_points.csv") else "reviewed_not_ingested",
            "notes": "REST query timed out, so no soil values were invented." if not _rows(root / "processed" / "soilgrids_points.csv") else "Spatial predictions at the study coordinate.",
        },
        "faostat": {"records": int(frame["yield_t_ha"].notna().sum()), "notes": "National Maize (corn) only. Not assigned to farms."},
        "zimstat": {"ingestion_status": "reviewed_not_ingested", "records": 0, "notes": "No public machine-readable Macheke table ingested."},
        "agritex": {"ingestion_status": "reviewed_not_ingested", "records": 0, "notes": "No public Macheke farm table ingested."},
    }
    write_source_catalogue(statuses)
    write_dictionary(frame)
    write_acquisition_report(frame)
    model = pd.read_csv(root / "processed" / "modelling_dataset.csv")
    train_from_real_dataset(model)
    return 0


def _rows(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open(encoding="utf-8") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


if __name__ == "__main__":
    raise SystemExit(main())
