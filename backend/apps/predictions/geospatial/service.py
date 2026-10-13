"""Orchestrator service for geospatial environmental data acquisition and caching."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from apps.predictions.geospatial.cache_service import GeospatialCacheService, make_grid_cell
from apps.predictions.geospatial.constants import SEASON_CONFIG
from apps.predictions.geospatial.location_validator import validate_coordinates
from apps.predictions.geospatial.providers.chirps import ChirpsProvider
from apps.predictions.geospatial.providers.nasa_power import NasaPowerProvider
from apps.predictions.geospatial.providers.soilgrids import SoilGridsProvider

logger = logging.getLogger(__name__)


def convert_planting_date_to_planting_day(planting_date_val: str | date | None) -> float | None:
    """Convert calendar planting date into the SmartCrop planting day index (1 = 1 November).

    Maize summer season starts 1 November (day 1).
    - 1 November -> 1
    - 10 December -> 40
    - 31 December -> 61
    - 1 January -> 62
    - 31 January -> 92
    - 1 February -> 93
    """
    if planting_date_val is None:
        return None
    if isinstance(planting_date_val, str):
        try:
            p_date = datetime.strptime(planting_date_val.strip(), "%Y-%m-%d").date()
        except ValueError:
            try:
                # Format MM-DD
                parts = planting_date_val.strip().split("-")
                month = int(parts[0]) if len(parts) == 2 else int(parts[1])
                day = int(parts[1]) if len(parts) == 2 else int(parts[2])
                p_date = date(2023, month, day)
            except Exception:
                return None
    elif isinstance(planting_date_val, date):
        p_date = planting_date_val
    else:
        return None

    # Calculate offset from November 1 of the prior calendar year if month is Jan-Apr
    if p_date.month in (11, 12):
        ref_date = date(p_date.year, 11, 1)
    else:
        ref_date = date(p_date.year - 1, 11, 1)

    delta_days = (p_date - ref_date).days
    planting_day = float(delta_days + 1)
    return max(1.0, min(150.0, planting_day))


class GeospatialService:
    """Unified service for retrieving environmental data at given coordinates."""

    chirps_provider = ChirpsProvider()
    nasa_power_provider = NasaPowerProvider()
    soilgrids_provider = SoilGridsProvider()

    @classmethod
    def get_environmental_data(
        cls,
        latitude: float,
        longitude: float,
        season_year: int = 2023,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Acquire environmental variables for given coordinates and harvest season year."""
        loc_val = validate_coordinates(latitude, longitude)
        grid_cell = make_grid_cell(latitude, longitude)
        date_range = f"{season_year - 1}-11-01_to_{season_year}-03-31"

        environmental_data: dict[str, float] = {}
        data_sources: list[dict[str, Any]] = []
        warnings: list[str] = list(loc_val.get("warnings", []))
        missing_features: list[str] = []

        # 1. CHIRPS Rainfall
        chirps_params = ["rainfall_mm"]
        cached_chirps = None if force_refresh else GeospatialCacheService.get("chirps", grid_cell, date_range, chirps_params)
        if cached_chirps:
            environmental_data.update(cached_chirps["data"])
            cached_prov = dict(cached_chirps["provenance"])
            cached_prov["cache_hit"] = True
            data_sources.append(cached_prov)
        else:
            chirps_res = cls.chirps_provider.acquire(latitude, longitude, season_year)
            if "rainfall_mm" in chirps_res["data"]:
                environmental_data["rainfall_mm"] = chirps_res["data"]["rainfall_mm"]
                GeospatialCacheService.set("chirps", grid_cell, date_range, chirps_params, chirps_res["data"], chirps_res["provenance"], ttl_days=30)
            else:
                missing_features.extend(chirps_res["missing"])
            warnings.extend(chirps_res["warnings"])
            data_sources.append(chirps_res["provenance"])

        # 2. NASA POWER Temperature
        nasa_params = ["avg_temperature_c", "max_temperature_c", "min_temperature_c"]
        cached_nasa = None if force_refresh else GeospatialCacheService.get("nasa_power", grid_cell, date_range, nasa_params)
        if cached_nasa:
            environmental_data.update(cached_nasa["data"])
            cached_prov = dict(cached_nasa["provenance"])
            cached_prov["cache_hit"] = True
            data_sources.append(cached_prov)
        else:
            nasa_res = cls.nasa_power_provider.acquire(latitude, longitude, season_year)
            if all(k in nasa_res["data"] for k in nasa_params):
                environmental_data.update(nasa_res["data"])
                GeospatialCacheService.set("nasa_power", grid_cell, date_range, nasa_params, nasa_res["data"], nasa_res["provenance"], ttl_days=14)
            else:
                missing_features.extend(nasa_res["missing"])
            warnings.extend(nasa_res["warnings"])
            data_sources.append(nasa_res["provenance"])

        # 3. SoilGrids Soil Properties
        soil_params = ["soil_ph", "soil_nitrogen", "soil_organic_carbon"]
        soil_date_range = "static_250m"
        cached_soil = None if force_refresh else GeospatialCacheService.get("soilgrids", grid_cell, soil_date_range, soil_params)
        if cached_soil:
            environmental_data.update(cached_soil["data"])
            cached_prov = dict(cached_soil["provenance"])
            cached_prov["cache_hit"] = True
            data_sources.append(cached_prov)
        else:
            soil_res = cls.soilgrids_provider.acquire(latitude, longitude, season_year)
            if all(k in soil_res["data"] for k in soil_params):
                environmental_data.update(soil_res["data"])
                GeospatialCacheService.set("soilgrids", grid_cell, soil_date_range, soil_params, soil_res["data"], soil_res["provenance"], ttl_days=90)
            else:
                missing_features.extend(soil_res["missing"])
            warnings.extend(soil_res["warnings"])
            data_sources.append(soil_res["provenance"])

        return {
            "environmental_data": environmental_data,
            "data_sources": data_sources,
            "data_quality": {
                "is_within_study_area": loc_val["is_within_study_area"],
                "is_within_zimbabwe": loc_val["is_within_zimbabwe"],
                "provisional_description": loc_val["provisional_description"],
                "grid_cell": grid_cell,
                "missing_features": sorted(list(set(missing_features))),
                "warnings": warnings,
            },
        }
