"""Provenance rows for each source that was actually used."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd


def provenance_frame(counts: dict[str, int], retrieved_at: str | None = None) -> pd.DataFrame:
    stamp = retrieved_at or datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "data_source": "NASA POWER",
            "data_source_type": "meteorological",
            "source_dataset": "POWER Daily API",
            "source_url": "https://power.larc.nasa.gov/api/temporal/daily/point",
            "spatial_resolution": "NASA POWER point/grid analysis (about 0.5 degree)",
            "temporal_resolution": "daily, aggregated to the configured maize season",
            "records": counts.get("nasa_daily", 0),
        },
        {
            "data_source": "CHIRPS",
            "data_source_type": "rainfall",
            "source_dataset": "CHIRPS via ClimateSERV datatype 0",
            "source_url": "https://climateserv.servirglobal.net/api/submitDataRequest/",
            "spatial_resolution": "0.05 degree grid, averaged over the study-area approximation box",
            "temporal_resolution": "daily, aggregated to the configured maize season",
            "records": counts.get("chirps_daily", 0),
        },
        {
            "data_source": "ISRIC SoilGrids",
            "data_source_type": "soil",
            "source_dataset": "SoilGrids 2.0",
            "source_url": "https://rest.isric.org/soilgrids/v2.0/properties/query",
            "spatial_resolution": "250 m prediction",
            "temporal_resolution": "static soil prediction",
            "records": counts.get("soilgrids", 0),
        },
        {
            "data_source": "FAOSTAT",
            "data_source_type": "agricultural_statistics",
            "source_dataset": "Production_Crops_Livestock_E_Africa",
            "source_url": "https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Africa.zip",
            "spatial_resolution": "national",
            "temporal_resolution": "annual",
            "records": counts.get("faostat", 0),
        },
    ]
    frame = pd.DataFrame(rows)
    frame["retrieved_at"] = stamp
    frame["geographic_level_note"] = frame["data_source"].map(
        {
            "NASA POWER": "grid_cell",
            "CHIRPS": "grid_cell",
            "ISRIC SoilGrids": "grid_cell",
            "FAOSTAT": "national",
        }
    )
    return frame
