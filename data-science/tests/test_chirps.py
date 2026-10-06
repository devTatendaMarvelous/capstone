"""CHIRPS response parsing and seasonal totals."""

import pandas as pd

from acquisition.chirps import _rows
from integration.temporal_join import aggregate_chirps
from utils.config import load_config


def test_chirps_row_uses_raw_rainfall_millimetres():
    payload = {"data": [{"isodate": "01/02/2020", "raw_value": 12.5, "value": {"avg": 12.5}}]}
    rows = _rows(payload, 2020)
    assert rows[0]["rainfall_mm"] == 12.5


def test_november_rainfall_counts_toward_the_next_harvest_year():
    config = load_config()
    daily = pd.DataFrame(
        {
            "date": ["2020-11-30", "2021-01-15", "2021-06-01"],
            "rainfall_mm": [10.0, 5.0, 100.0],
        }
    )
    seasonal = aggregate_chirps(daily, config)
    season = seasonal.loc[seasonal["year"] == 2021].iloc[0]
    assert season["chirps_season_rainfall_mm"] == 15.0
    assert season["season"] == "2020/2021"
    assert season["chirps_rainfall_days"] == 2
