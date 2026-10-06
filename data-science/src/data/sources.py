"""Catalogue of external sources that may be ingested later.

This catalogue contains no weather, soil, or yield measurements.
``ingestion_status`` is ``not_ingested`` until a real extract is added
under ``data/external`` and labelled ``EXTERNAL``.
"""

from __future__ import annotations

import pandas as pd

CATALOGUE_COLUMNS = [
    "source_name",
    "provider",
    "variables_of_interest",
    "unit_notes",
    "geographic_coverage_note",
    "intended_use",
    "ingestion_status",
    "data_source_type",
    "contains_measurements",
]


def build_source_catalogue() -> pd.DataFrame:
    """Return the external-source catalogue. No measured values are included."""
    rows = [
        {
            "source_name": "NASA POWER",
            "provider": "NASA Langley Research Center",
            "variables_of_interest": "rainfall; temperature",
            "unit_notes": "Millimetres and degrees Celsius if ingested later.",
            "geographic_coverage_note": "Point or grid query for the Macheke area. Not queried in this phase.",
            "intended_use": "Seasonal weather covariates for maize.",
            "ingestion_status": "not_ingested",
            "data_source_type": "EXTERNAL",
            "contains_measurements": False,
        },
        {
            "source_name": "CHIRPS",
            "provider": "Climate Hazards Center, UC Santa Barbara",
            "variables_of_interest": "rainfall",
            "unit_notes": "Millimetres if a raster extract is added later.",
            "geographic_coverage_note": "Gridded rainfall. No CHIRPS file is stored in this repository.",
            "intended_use": "Independent rainfall cross-check.",
            "ingestion_status": "not_ingested",
            "data_source_type": "EXTERNAL",
            "contains_measurements": False,
        },
        {
            "source_name": "SoilGrids",
            "provider": "ISRIC",
            "variables_of_interest": "soil_ph; soil_organic_carbon",
            "unit_notes": "SoilGrids organic carbon is often g/kg. Percent = g/kg / 10.",
            "geographic_coverage_note": "Global soil grids. No SoilGrids extract is stored here.",
            "intended_use": "Soil covariates after unit conversion.",
            "ingestion_status": "not_ingested",
            "data_source_type": "EXTERNAL",
            "contains_measurements": False,
        },
        {
            "source_name": "Agritex / Ministry of Agriculture",
            "provider": "Government of Zimbabwe",
            "variables_of_interest": "area; yield; farming practice",
            "unit_notes": "Confirm units on any official extract before cleaning.",
            "geographic_coverage_note": "Possible Macheke or district agricultural records. None are included.",
            "intended_use": "Farm and yield observations labelled REAL.",
            "ingestion_status": "not_ingested",
            "data_source_type": "EXTERNAL",
            "contains_measurements": False,
        },
        {
            "source_name": "ZIMSTAT",
            "provider": "Zimbabwe National Statistics Agency",
            "variables_of_interest": "production; area",
            "unit_notes": "Official tables often report production and area, not yield per hectare.",
            "geographic_coverage_note": "National or district statistics. No ZIMSTAT table is included.",
            "intended_use": "Context for yield = production / area after unit checks.",
            "ingestion_status": "not_ingested",
            "data_source_type": "EXTERNAL",
            "contains_measurements": False,
        },
    ]
    frame = pd.DataFrame(rows, columns=CATALOGUE_COLUMNS)
    if frame["contains_measurements"].any():
        raise ValueError("The source catalogue must not contain measurements.")
    if not (frame["ingestion_status"] == "not_ingested").all():
        raise ValueError("Catalogue rows must stay not_ingested until a real file is added.")
    return frame
