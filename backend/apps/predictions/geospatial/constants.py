"""Geospatial constants and boundaries for Macheke, Mashonaland East, Zimbabwe."""

# Macheke Study Area (derived from data-science/config/smartcrop_config.yaml)
STUDY_AREA = {
    "country": "Zimbabwe",
    "province": "Mashonaland East",
    "district": "Macheke",
    "location_label": "Macheke study-area grid",
    "center_lat": -18.136,
    "center_lon": 31.849,
    "bbox": {
        "min_lat": -18.25,
        "max_lat": -18.02,
        "min_lon": 31.75,
        "max_lon": 31.95,
    },
    "boundary_status": "study_area_approximation",
    "boundary_note": (
        "No authoritative Macheke district polygon was available to download. "
        "The box is an approximation around the town of Macheke and is not an official "
        "ward or district boundary. Synthetic ward codes are not used."
    ),
}

# Country boundary bounds for Zimbabwe (geographic sanity bounds)
ZIMBABWE_BOUNDS = {
    "min_lat": -22.5,
    "max_lat": -15.5,
    "min_lon": 25.0,
    "max_lon": 33.5,
}

# Maize growing season definition
SEASON_CONFIG = {
    "crop": "maize",
    "start_month": 11,  # November
    "end_month": 3,    # March
    "critical_growth_months": (1, 2),  # January - February
    "default_harvest_year": 2023,
    "reference_planting_start": "11-01",  # 1 November = day 1
    "heat_stress_threshold_c": 33.0,
}

# Supported location selection methods
LOCATION_METHODS = {
    "browser_geolocation": "Browser Geolocation",
    "manual_map_selection": "Manual Map Selection",
    "manual_coordinates": "Manual Coordinates",
}
