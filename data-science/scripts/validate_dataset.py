"""Print the real-dataset validation banner."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.config import data_dir


def _count(path: Path) -> int:
    if not path.is_file():
        return 0
    frame = pd.read_csv(path)
    return int(len(frame))


def main() -> int:
    root = data_dir()
    path = root / "processed" / "capstone_dataset_real.csv"
    if not path.is_file():
        print("Real dataset has not been built. Run scripts/build_dataset.py after acquisition.")
        return 1
    frame = pd.read_csv(path)
    manifest = json.loads((root / "metadata" / "dataset_manifest.json").read_text(encoding="utf-8"))
    years = frame["year"].dropna()
    farm_yields = int(((frame["yield_geographic_level"] == "farm") & frame["yield_t_ha"].notna()).sum())
    status = "PASS" if farm_yields >= 30 else "INSUFFICIENT TARGET DATA"
    if farm_yields == 0 and frame["yield_t_ha"].notna().any():
        status = "INSUFFICIENT TARGET DATA"
    suspicious = int(frame["quality_flag"].astype(str).str.contains("SUSPICIOUS|OUT_OF_RANGE").sum())
    duplicates = int(frame["quality_flag"].astype(str).str.contains("DUPLICATE").sum())
    invalid_coordinates = int((~frame["latitude"].between(-22.9, -15.5) | ~frame["longitude"].between(25, 33.2)).sum())
    print("====================================================")
    print("SMARTCROP REAL DATASET VALIDATION")
    print("====================================================")
    print("Study area: Macheke, Mashonaland East, Zimbabwe")
    print("Crop: Maize")
    print()
    print(f"Real observations: {len(frame)}")
    print(f"Synthetic observations: {int(frame['synthetic_record'].fillna(False).astype(bool).sum())}")
    print()
    if years.empty:
        print("Years: none")
    else:
        print(f"Years: {int(years.min())} - {int(years.max())}")
    print()
    print(f"Yield observations: {int(frame['yield_t_ha'].notna().sum())}")
    print()
    print(f"NASA POWER records: {_count(root / 'interim' / 'nasa_power_daily.csv')}")
    print(f"CHIRPS records: {_count(root / 'interim' / 'chirps_daily.csv')}")
    print(f"SoilGrids records: {_count(root / 'processed' / 'soilgrids_points.csv')}")
    print(f"FAOSTAT records: {_count(root / 'processed' / 'faostat_zimbabwe_maize.csv')}")
    print("ZIMSTAT records: 0")
    print(f"Agricultural records: {_count(root / 'interim' / 'agricultural_observations.csv')}")
    print()
    print(f"Missing yield: {int(frame['yield_t_ha'].isna().sum())}")
    print(f"Duplicate records: {duplicates}")
    print(f"Invalid coordinates: {invalid_coordinates}")
    print(f"Suspicious observations: {suspicious}")
    print()
    print(f"FINAL STATUS:")
    print(status)
    print("====================================================")
    print(f"Manifest real_records: {manifest.get('real_records')}")
    if farm_yields == 0:
        print(
            "WARNING: verified Macheke farm-level maize yield observations were not found. "
            "National FAOSTAT yield must not be described as Macheke farm yield."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
