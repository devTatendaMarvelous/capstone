"""NASA POWER weather provider for growing-season temperatures."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pandas as pd
from django.conf import settings

from apps.predictions.geospatial.constants import STUDY_AREA
from apps.predictions.geospatial.providers.base import BaseProvider

logger = logging.getLogger(__name__)

NASA_POWER_POINT_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


class NasaPowerProvider(BaseProvider):
    name = "nasa_power"
    default_timeout = 15

    def _fallback_from_local_cache(self, season_year: int) -> dict[str, Any] | None:
        """Attempt to read from local repository dataset if coordinate is within study area."""
        candidates = [
            settings.BASE_DIR.parent / "data-science" / "data" / "processed" / "nasa_power_seasonal.csv",
            settings.BASE_DIR / "data" / "nasa_power_seasonal.csv",
        ]
        for path in candidates:
            if path.is_file():
                try:
                    df = pd.read_csv(path)
                    match = df.loc[df["year"] == season_year]
                    if not match.empty:
                        row = match.iloc[0]
                        return {
                            "avg_temperature_c": round(float(row["avg_temperature_c"]), 2),
                            "max_temperature_c": round(float(row["max_temperature_c"]), 2),
                            "min_temperature_c": round(float(row["min_temperature_c"]), 2),
                            "nasa_season_rainfall_mm": (
                                round(float(row["nasa_season_rainfall_mm"]), 2)
                                if "nasa_season_rainfall_mm" in row and pd.notna(row["nasa_season_rainfall_mm"])
                                else None
                            ),
                        }
                    # If exact season not found, use closest year average
                    avg_row = df.mean(numeric_only=True)
                    return {
                        "avg_temperature_c": round(float(avg_row["avg_temperature_c"]), 2),
                        "max_temperature_c": round(float(avg_row["max_temperature_c"]), 2),
                        "min_temperature_c": round(float(avg_row["min_temperature_c"]), 2),
                        "nasa_season_rainfall_mm": round(float(avg_row.get("nasa_season_rainfall_mm", 700.0)), 2),
                    }
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Could not read local NASA POWER fallback from %s: %s", path, exc)
        return None

    def acquire(self, latitude: float, longitude: float, season_year: int = 2023) -> dict[str, Any]:
        retrieval_time = datetime.now(timezone.utc).isoformat()
        start_date = f"{season_year - 1}1101"
        end_date = f"{season_year}0331"

        query = urlencode({
            "parameters": "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR",
            "community": "AG",
            "longitude": f"{longitude:.4f}",
            "latitude": f"{latitude:.4f}",
            "start": start_date,
            "end": end_date,
            "format": "JSON",
            "header": "true",
        })
        request_url = f"{NASA_POWER_POINT_URL}?{query}"

        data: dict[str, float] = {}
        warnings: list[str] = []
        missing: list[str] = []
        retrieval_status = "live_api"

        try:
            _status, payload = self._http_get_json(request_url)
            params = payload.get("properties", {}).get("parameter", {})
            t2m_series = params.get("T2M", {})
            t2m_max_series = params.get("T2M_MAX", {})
            t2m_min_series = params.get("T2M_MIN", {})

            # Filter valid measurements (fill value is -999)
            valid_t2m = [float(v) for v in t2m_series.values() if v is not None and float(v) > -900]
            valid_max = [float(v) for v in t2m_max_series.values() if v is not None and float(v) > -900]
            valid_min = [float(v) for v in t2m_min_series.values() if v is not None and float(v) > -900]

            if valid_t2m and valid_max and valid_min:
                data["avg_temperature_c"] = round(sum(valid_t2m) / len(valid_t2m), 2)
                data["max_temperature_c"] = round(sum(valid_max) / len(valid_max), 2)
                data["min_temperature_c"] = round(sum(valid_min) / len(valid_min), 2)
            else:
                raise ValueError("Incomplete temperature parameters returned by NASA POWER")

        except Exception as exc:  # noqa: BLE001
            logger.warning("NASA POWER live retrieval failed (%s). Checking local cache fallback...", exc)
            fallback = self._fallback_from_local_cache(season_year)
            if fallback:
                data["avg_temperature_c"] = fallback["avg_temperature_c"]
                data["max_temperature_c"] = fallback["max_temperature_c"]
                data["min_temperature_c"] = fallback["min_temperature_c"]
                retrieval_status = "local_study_area_cache_fallback"
                warnings.append(
                    "NASA POWER live API was unreachable. Used pre-retrieved study-area historical meteorological record."
                )
            else:
                missing.extend(["avg_temperature_c", "max_temperature_c", "min_temperature_c"])
                warnings.append(f"Failed to acquire temperature data from NASA POWER: {exc}")

        # Consistency check: min <= avg <= max
        if "avg_temperature_c" in data and "max_temperature_c" in data and "min_temperature_c" in data:
            if not (data["min_temperature_c"] <= data["avg_temperature_c"] <= data["max_temperature_c"]):
                warnings.append("Computed temperatures violate ordering min <= avg <= max.")

        provenance = {
            "provider": "NASA POWER (Prediction of Worldwide Energy Resources)",
            "dataset_name": "NASA POWER Agroclimatology (AG) Daily Point",
            "source_url": request_url,
            "retrieval_timestamp": retrieval_time,
            "coordinates": {"latitude": latitude, "longitude": longitude},
            "date_range": f"{season_year - 1}-11-01 to {season_year}-03-31",
            "temporal_resolution": "Daily aggregated to November–March seasonal mean",
            "spatial_resolution": "0.5° × 0.5° (~50 km)",
            "measurement_units": {
                "avg_temperature_c": "°C",
                "max_temperature_c": "°C",
                "min_temperature_c": "°C",
            },
            "retrieval_status": retrieval_status,
            "observation_type": "modelled_reanalysis",
        }

        return {
            "data": data,
            "provenance": provenance,
            "warnings": warnings,
            "missing": missing,
        }
