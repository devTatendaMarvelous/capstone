"""Turn daily grids into one row per maize harvest year."""

from __future__ import annotations

import numpy as np
import pandas as pd

from utils.dates import harvest_year, months_in_window, season_label


def _prepare(daily: pd.DataFrame, config: dict) -> pd.DataFrame:
    frame = daily.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    season = config["season"]
    frame["harvest_year"] = harvest_year(frame["date"], int(season["start_month"]), int(season["end_month"]))
    frame = frame.dropna(subset=["harvest_year"])
    frame["harvest_year"] = frame["harvest_year"].astype(int)
    frame["month"] = frame["date"].dt.month
    return frame


def _critical_mask(frame: pd.DataFrame, config: dict) -> pd.Series:
    window = months_in_window(
        int(config["critical_growth_period"]["start_month"]),
        int(config["critical_growth_period"]["end_month"]),
    )
    return frame["month"].isin(window)


def aggregate_chirps(daily: pd.DataFrame, config: dict) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame()
    frame = _prepare(daily, config)
    threshold = float(config["thresholds"]["rainfall_day_mm"])
    rows = []
    for year, group in frame.groupby("harvest_year"):
        rain = pd.to_numeric(group["rainfall_mm"], errors="coerce")
        critical = pd.to_numeric(group.loc[_critical_mask(group, config), "rainfall_mm"], errors="coerce")
        mean = float(rain.mean()) if rain.notna().any() else np.nan
        deviation = float(rain.std(ddof=0)) if rain.notna().sum() > 1 else np.nan
        rows.append(
            {
                "year": int(year),
                "season": season_label(int(year)),
                "chirps_season_rainfall_mm": float(rain.sum(min_count=1)),
                "chirps_critical_period_rainfall_mm": float(critical.sum(min_count=1)) if critical.notna().any() else np.nan,
                "chirps_rainfall_days": int((rain > threshold).sum()),
                "chirps_rainfall_cv": deviation / mean if mean and np.isfinite(mean) and mean != 0 else np.nan,
                "chirps_days": int(rain.notna().sum()),
            }
        )
    return pd.DataFrame(rows)


def aggregate_nasa(daily: pd.DataFrame, config: dict) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame()
    frame = _prepare(daily, config)
    threshold = float(config["thresholds"]["rainfall_day_mm"])
    heat = float(config["thresholds"]["heat_stress_tmax_c"])
    rows = []
    for year, group in frame.groupby("harvest_year"):
        rain = pd.to_numeric(group["PRECTOTCORR"], errors="coerce")
        critical = pd.to_numeric(group.loc[_critical_mask(group, config), "PRECTOTCORR"], errors="coerce")
        tmax = pd.to_numeric(group["T2M_MAX"], errors="coerce")
        tmin = pd.to_numeric(group["T2M_MIN"], errors="coerce")
        tavg = pd.to_numeric(group["T2M"], errors="coerce")
        mean_rain = float(rain.mean()) if rain.notna().any() else np.nan
        deviation = float(rain.std(ddof=0)) if rain.notna().sum() > 1 else np.nan
        max_mean = float(tmax.mean()) if tmax.notna().any() else np.nan
        min_mean = float(tmin.mean()) if tmin.notna().any() else np.nan
        rows.append(
            {
                "year": int(year),
                "season": season_label(int(year)),
                "nasa_season_rainfall_mm": float(rain.sum(min_count=1)),
                "nasa_critical_period_rainfall_mm": float(critical.sum(min_count=1)) if critical.notna().any() else np.nan,
                "nasa_rainfall_days": int((rain > threshold).sum()),
                "nasa_rainfall_cv": deviation / mean_rain if mean_rain and np.isfinite(mean_rain) and mean_rain != 0 else np.nan,
                "avg_temperature_c": float(tavg.mean()) if tavg.notna().any() else np.nan,
                "max_temperature_c": max_mean,
                "min_temperature_c": min_mean,
                "temperature_range_c": max_mean - min_mean if np.isfinite(max_mean) and np.isfinite(min_mean) else np.nan,
                "heat_stress_days": int((tmax >= heat).sum()),
                "nasa_days": int(tavg.notna().sum()),
            }
        )
    return pd.DataFrame(rows)
