"""SoilGrids 2.0 provider for topsoil pH, nitrogen, and organic carbon."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pandas as pd
from django.conf import settings

from apps.predictions.geospatial.providers.base import BaseProvider

logger = logging.getLogger(__name__)

SOILGRIDS_QUERY_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"


class SoilGridsProvider(BaseProvider):
    name = "soilgrids"
    default_timeout = 10
    selected_depth = "0-5cm"

    def _fallback_from_local_cache(self) -> dict[str, Any] | None:
        """Read topsoil properties from local processed soilgrids table if present."""
        candidates = [
            settings.BASE_DIR.parent / "data-science" / "data" / "processed" / "soilgrids_points.csv",
            settings.BASE_DIR / "data" / "soilgrids_points.csv",
        ]
        for path in candidates:
            if path.is_file():
                try:
                    df = pd.read_csv(path)
                    depth_df = df.loc[df["depth"] == self.selected_depth]
                    if depth_df.empty:
                        depth_df = df
                    res: dict[str, float] = {}
                    for _, row in depth_df.iterrows():
                        prop = str(row["property"]).lower()
                        val = row.get("value")
                        if pd.notna(val):
                            num = float(val)
                            if prop == "phh2o":
                                res["soil_ph"] = round(num, 2)
                            elif prop == "nitrogen":
                                # Stored as g/kg in target_units; convert to percent (% = g/kg / 10)
                                res["soil_nitrogen"] = round(num / 10.0, 4)
                            elif prop == "soc":
                                # Stored as g/kg; convert to percent (% = g/kg / 10)
                                res["soil_organic_carbon"] = round(num / 10.0, 3)
                    if "soil_ph" in res and "soil_nitrogen" in res and "soil_organic_carbon" in res:
                        return res
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Could not read local SoilGrids fallback from %s: %s", path, exc)
        return None

    def acquire(self, latitude: float, longitude: float, season_year: int = 2023) -> dict[str, Any]:
        retrieval_time = datetime.now(timezone.utc).isoformat()
        data: dict[str, float] = {}
        warnings: list[str] = []
        missing: list[str] = []
        retrieval_status = "live_api"

        query = urlencode([
            ("lon", f"{longitude:.4f}"),
            ("lat", f"{latitude:.4f}"),
            ("property", "phh2o"),
            ("property", "nitrogen"),
            ("property", "soc"),
            ("depth", self.selected_depth),
            ("value", "mean"),
        ])
        request_url = f"{SOILGRIDS_QUERY_URL}?{query}"

        try:
            _status, payload = self._http_get_json(request_url)
            layers = payload.get("properties", {}).get("layers", [])
            for layer in layers:
                prop_name = layer.get("name")
                factor = float(layer.get("unit_measure", {}).get("d_factor") or 1.0)
                for d in layer.get("depths", []):
                    if d.get("label") == self.selected_depth:
                        mean_val = d.get("values", {}).get("mean")
                        if mean_val is not None:
                            val = float(mean_val) / factor
                            if prop_name == "phh2o":
                                data["soil_ph"] = round(val, 2)
                            elif prop_name == "nitrogen":
                                # Convert g/kg to percent (% = g/kg / 10)
                                data["soil_nitrogen"] = round(val / 10.0, 4)
                            elif prop_name == "soc":
                                # Convert g/kg to percent (% = g/kg / 10)
                                data["soil_organic_carbon"] = round(val / 10.0, 3)

            required_soil = ["soil_ph", "soil_nitrogen", "soil_organic_carbon"]
            if not all(k in data for k in required_soil):
                raise ValueError("Incomplete properties returned by SoilGrids API")

        except Exception as exc:  # noqa: BLE001
            logger.warning("SoilGrids live retrieval failed (%s). Checking local dataset fallback...", exc)
            fallback = self._fallback_from_local_cache()
            if fallback:
                data.update(fallback)
                retrieval_status = "local_study_area_cache_fallback"
                warnings.append(
                    "SoilGrids live endpoint was unreachable. Used pre-retrieved study-area SoilGrids 2.0 250m predictions."
                )
            else:
                for k in ["soil_ph", "soil_nitrogen", "soil_organic_carbon"]:
                    if k not in data:
                        missing.append(k)
                warnings.append(f"Failed to acquire SoilGrids soil data: {exc}")

        provenance = {
            "provider": "ISRIC — World Soil Information",
            "dataset_name": "SoilGrids 2.0 (Global Gridded Soil Information)",
            "source_url": request_url,
            "retrieval_timestamp": retrieval_time,
            "coordinates": {"latitude": latitude, "longitude": longitude},
            "depth_interval": self.selected_depth,
            "spatial_resolution": "250 m",
            "measurement_units": {
                "soil_ph": "pH (1:5 H2O)",
                "soil_nitrogen": "% (mass fraction converted from cg/kg or g/kg)",
                "soil_organic_carbon": "% (mass fraction converted from dg/kg or g/kg)",
            },
            "retrieval_status": retrieval_status,
            "observation_type": "modelled_spatial_prediction",
            "notes": "SoilGrids predictions represent 250 m spatial estimates, not direct farm laboratory soil samples.",
        }

        return {
            "data": data,
            "provenance": provenance,
            "warnings": warnings,
            "missing": missing,
        }
