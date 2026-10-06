"""Joins do not create a yield from weather."""

import pandas as pd

import integration.dataset_builder as builder
from integration.dataset_builder import build_real_dataset


def test_missing_yield_stays_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(builder, "data_dir", lambda: tmp_path)
    interim = tmp_path / "interim"
    processed = tmp_path / "processed"
    for path in (interim, processed, tmp_path / "external", tmp_path / "metadata", tmp_path / "reports"):
        path.mkdir(parents=True)
    nasa = pd.DataFrame(
        {
            "date": pd.date_range("2019-11-01", "2020-03-31", freq="D"),
        }
    )
    nasa["T2M"] = 22.0
    nasa["T2M_MAX"] = 28.0
    nasa["T2M_MIN"] = 16.0
    nasa["PRECTOTCORR"] = 2.0
    nasa.to_csv(interim / "nasa_power_daily.csv", index=False)
    pd.DataFrame(columns=["date", "rainfall_mm"]).to_csv(interim / "chirps_daily.csv", index=False)
    pd.DataFrame(columns=["depth", "column", "value", "latitude", "longitude"]).to_csv(processed / "soilgrids_points.csv", index=False)
    pd.DataFrame(columns=["year", "geographic_level", "yield_t_ha"]).to_csv(interim / "agricultural_observations.csv", index=False)
    frame = build_real_dataset()
    assert frame["synthetic_record"].eq(False).all()
    assert frame["yield_t_ha"].isna().all()
    assert "SYN-W" not in frame.astype(str).to_string()
    assert (tmp_path / "external" / "macheke_boundary.geojson").is_file()
