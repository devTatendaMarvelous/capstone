"""Validate farm geographic coordinates and check study area boundaries."""

from __future__ import annotations

from typing import Any

from apps.predictions.geospatial.constants import (
    LOCATION_METHODS,
    STUDY_AREA,
    ZIMBABWE_BOUNDS,
)


def validate_coordinates(
    latitude: float | int | None,
    longitude: float | int | None,
    selection_method: str | None = None,
    is_confirmed: bool = False,
    description: str = "",
) -> dict[str, Any]:
    """Validate latitude and longitude and verify study area inclusion.

    Returns a dictionary with validation status, study area flag, warnings, and metadata.
    """
    errors: dict[str, list[str]] = {}

    if latitude is None:
        errors["latitude"] = ["Latitude is required."]
    else:
        try:
            latitude = float(latitude)
            if not (-90.0 <= latitude <= 90.0):
                errors["latitude"] = ["Latitude must be between -90 and 90 degrees."]
        except (TypeError, ValueError):
            errors["latitude"] = ["Latitude must be a valid number."]

    if longitude is None:
        errors["longitude"] = ["Longitude is required."]
    else:
        try:
            longitude = float(longitude)
            if not (-180.0 <= longitude <= 180.0):
                errors["longitude"] = ["Longitude must be between -180 and 180 degrees."]
        except (TypeError, ValueError):
            errors["longitude"] = ["Longitude must be a valid number."]

    if errors:
        return {
            "valid": False,
            "errors": errors,
            "latitude": latitude,
            "longitude": longitude,
            "is_within_study_area": False,
            "is_within_zimbabwe": False,
            "warnings": [],
        }

    warnings: list[str] = []

    # Check Zimbabwe broad boundary
    is_within_zimbabwe = (
        ZIMBABWE_BOUNDS["min_lat"] <= latitude <= ZIMBABWE_BOUNDS["max_lat"]
        and ZIMBABWE_BOUNDS["min_lon"] <= longitude <= ZIMBABWE_BOUNDS["max_lon"]
    )
    if not is_within_zimbabwe:
        warnings.append(
            f"The selected coordinates ({latitude:.4f}, {longitude:.4f}) are outside Zimbabwe "
            f"({ZIMBABWE_BOUNDS['min_lat']}° to {ZIMBABWE_BOUNDS['max_lat']}° S, "
            f"{ZIMBABWE_BOUNDS['min_lon']}° to {ZIMBABWE_BOUNDS['max_lon']}° E)."
        )

    # Check Macheke study area bbox
    bbox = STUDY_AREA["bbox"]
    is_within_study_area = (
        bbox["min_lat"] <= latitude <= bbox["max_lat"]
        and bbox["min_lon"] <= longitude <= bbox["max_lon"]
    )

    if not is_within_study_area:
        warnings.append(
            f"The selected location ({latitude:.4f}, {longitude:.4f}) is outside the project's "
            f"validated geographic scope (Macheke study area: latitudes {bbox['min_lat']} to {bbox['max_lat']}, "
            f"longitudes {bbox['min_lon']} to {bbox['max_lon']}). "
            "Predictions for locations outside this area are experimental and not validated on Macheke conditions."
        )

    # Valid selection method
    method = selection_method or "manual_coordinates"
    if method not in LOCATION_METHODS:
        method = "manual_coordinates"

    # Provisional description (not official administrative classification)
    if is_within_study_area:
        provisional_desc = f"{STUDY_AREA['district']}, {STUDY_AREA['province']}, {STUDY_AREA['country']} (provisional study area grid)"
    elif is_within_zimbabwe:
        provisional_desc = f"{description or 'Farm location'}, Zimbabwe (outside validated study area)"
    else:
        provisional_desc = f"{description or 'Farm location'} (outside Zimbabwe)"

    return {
        "valid": True,
        "latitude": latitude,
        "longitude": longitude,
        "selection_method": method,
        "is_confirmed": bool(is_confirmed),
        "is_within_study_area": is_within_study_area,
        "is_within_zimbabwe": is_within_zimbabwe,
        "provisional_description": provisional_desc,
        "study_area": STUDY_AREA,
        "warnings": warnings,
    }
