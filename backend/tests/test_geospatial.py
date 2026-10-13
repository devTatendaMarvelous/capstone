"""Tests for geospatial validation, environmental providers, caching, and location-based prediction."""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.predictions.geospatial.constants import STUDY_AREA, ZIMBABWE_BOUNDS
from apps.predictions.geospatial.location_validator import validate_coordinates
from apps.predictions.geospatial.providers.chirps import ChirpsProvider
from apps.predictions.geospatial.providers.nasa_power import NasaPowerProvider
from apps.predictions.geospatial.providers.soilgrids import SoilGridsProvider
from apps.predictions.geospatial.service import (
    GeospatialService,
    convert_planting_date_to_planting_day,
)
from apps.predictions.models import EnvironmentalCache, FarmLocation, Prediction

User = get_user_model()


@pytest.fixture
def auth_farmer(db):
    user = User.objects.create_user(
        username="test_farmer",
        email="farmer@smartcrop.local",
        password="password123",
        role="farmer",
    )
    client = APIClient()
    resp = client.post("/api/v1/auth/token/", {"username": "test_farmer", "password": "password123"}, format="json")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client, user


# --- Location Validation Tests ---

def test_validate_coordinates_valid_macheke_study_area():
    res = validate_coordinates(
        latitude=-18.136,
        longitude=31.849,
        selection_method="manual_map_selection",
        is_confirmed=True,
    )
    assert res["valid"] is True
    assert res["is_within_study_area"] is True
    assert res["is_within_zimbabwe"] is True
    assert "Macheke" in res["provisional_description"]
    assert len(res["warnings"]) == 0


def test_validate_coordinates_outside_study_area_inside_zimbabwe():
    # Harare coordinate (-17.82, 31.05) is inside Zimbabwe but outside Macheke study area bbox
    res = validate_coordinates(
        latitude=-17.82,
        longitude=31.05,
        selection_method="browser_geolocation",
    )
    assert res["valid"] is True
    assert res["is_within_study_area"] is False
    assert res["is_within_zimbabwe"] is True
    assert any("outside the project's validated geographic scope" in w for w in res["warnings"])


def test_validate_coordinates_invalid_bounds():
    res = validate_coordinates(latitude=95.0, longitude=31.849)
    assert res["valid"] is False
    assert "latitude" in res["errors"]

    res2 = validate_coordinates(latitude=-18.136, longitude=-200.0)
    assert res2["valid"] is False
    assert "longitude" in res2["errors"]


def test_convert_planting_date_to_planting_day():
    # 1 November is day 1
    assert convert_planting_date_to_planting_day("2023-11-01") == 1.0
    # 10 December is day 40 (30 days in Nov + 10)
    assert convert_planting_date_to_planting_day("2023-12-10") == 40.0
    # 31 December is day 61
    assert convert_planting_date_to_planting_day("2023-12-31") == 61.0
    # 15 January is day 76
    assert convert_planting_date_to_planting_day("2024-01-15") == 76.0


# --- Provider & Caching Tests ---

def test_chirps_provider_study_area_fallback():
    provider = ChirpsProvider()
    res = provider.acquire(latitude=-18.136, longitude=31.849, season_year=2023)
    assert "rainfall_mm" in res["data"]
    assert res["data"]["rainfall_mm"] > 0
    assert res["provenance"]["provider"].startswith("Climate Hazards Center")
    assert res["provenance"]["measurement_units"]["rainfall_mm"] == "mm"


def test_nasa_power_provider_study_area_fallback():
    provider = NasaPowerProvider()
    res = provider.acquire(latitude=-18.136, longitude=31.849, season_year=2023)
    assert "avg_temperature_c" in res["data"]
    assert "max_temperature_c" in res["data"]
    assert "min_temperature_c" in res["data"]
    assert res["data"]["min_temperature_c"] <= res["data"]["avg_temperature_c"] <= res["data"]["max_temperature_c"]
    assert res["provenance"]["measurement_units"]["avg_temperature_c"] == "°C"


def test_soilgrids_provider_unit_conversions():
    provider = SoilGridsProvider()
    res = provider.acquire(latitude=-18.136, longitude=31.849, season_year=2023)
    assert "soil_ph" in res["data"]
    assert "soil_nitrogen" in res["data"]
    assert "soil_organic_carbon" in res["data"]
    # Check reasonable unit scales: pH between 3.5 and 9, N between 0 and 1%, SOC between 0 and 10%
    assert 3.5 <= res["data"]["soil_ph"] <= 9.0
    assert 0.0 <= res["data"]["soil_nitrogen"] <= 1.0
    assert 0.0 <= res["data"]["soil_organic_carbon"] <= 10.0


@pytest.mark.django_db
def test_geospatial_service_caching():
    # First call acquires and populates cache
    res1 = GeospatialService.get_environmental_data(-18.136, 31.849, season_year=2023, force_refresh=True)
    assert "rainfall_mm" in res1["environmental_data"]
    assert "avg_temperature_c" in res1["environmental_data"]
    assert "soil_ph" in res1["environmental_data"]

    # Verify cache entries were created
    assert EnvironmentalCache.objects.count() >= 3

    # Second call hits cache
    res2 = GeospatialService.get_environmental_data(-18.136, 31.849, season_year=2023, force_refresh=False)
    cache_hits = [src.get("cache_hit") for src in res2["data_sources"] if src.get("cache_hit")]
    assert len(cache_hits) >= 1


# --- API Endpoint Tests ---

@pytest.mark.django_db
def test_location_validate_api(auth_farmer):
    client, _ = auth_farmer
    resp = client.post(
        "/api/v1/location/validate/",
        {
            "latitude": -18.136,
            "longitude": 31.849,
            "location_selection_method": "manual_map_selection",
            "is_confirmed": True,
        },
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["valid"] is True
    assert resp.data["is_within_study_area"] is True


@pytest.mark.django_db
def test_environmental_preview_api(auth_farmer):
    client, _ = auth_farmer
    resp = client.post(
        "/api/v1/environmental-data/preview/",
        {
            "latitude": -18.136,
            "longitude": 31.849,
            "planting_date": "2023-11-15",
        },
        format="json",
    )
    assert resp.status_code == 200
    env = resp.data["environmental_data"]
    assert "rainfall_mm" in env
    assert "avg_temperature_c" in env
    assert "soil_ph" in env
    assert env.get("planting_day") == 15.0
    assert len(resp.data["data_sources"]) >= 3


@pytest.mark.django_db
def test_prediction_with_confirmed_location(auth_farmer):
    client, _ = auth_farmer
    payload = {
        "location": {
            "latitude": -18.136,
            "longitude": 31.849,
            "location_selection_method": "browser_geolocation",
            "confirmed": True,
            "description": "My test farm",
        },
        "area_ha": 3.0,
        "planting_date": "2023-11-15",
        "fertilizer_kg_ha": 120.0,
    }
    resp = client.post("/api/v1/predictions/", payload, format="json")
    assert resp.status_code == 201, resp.content
    body = resp.data
    assert body["predicted_yield_t_ha"] > 0
    assert body["estimated_production_tonnes"] == round(body["predicted_yield_t_ha"] * 3.0, 2)
    assert body["location"]["confirmed"] is True
    assert body["location"]["latitude"] == -18.136
    assert len(body["data_sources"]) >= 3
    assert "disclaimer" in body


@pytest.mark.django_db
def test_prediction_rejects_unconfirmed_location(auth_farmer):
    client, _ = auth_farmer
    payload = {
        "location": {
            "latitude": -18.136,
            "longitude": 31.849,
            "confirmed": False,  # Not confirmed!
        },
        "area_ha": 2.0,
    }
    resp = client.post("/api/v1/predictions/", payload, format="json")
    assert resp.status_code == 400
    assert "location" in resp.data["errors"]


@pytest.mark.django_db
def test_prediction_imputes_unknown_fertilizer(auth_farmer):
    client, _ = auth_farmer
    payload = {
        "location": {
            "latitude": -18.136,
            "longitude": 31.849,
            "confirmed": True,
        },
        "area_ha": 2.0,
        "planting_date": "2023-11-15",
        # fertilizer_kg_ha is omitted
    }
    resp = client.post("/api/v1/predictions/", payload, format="json")
    assert resp.status_code == 201
    body = resp.data
    assert body["predicted_yield_t_ha"] > 0
    # Check warning about fertilizer imputation
    warnings = body["data_quality"]["warnings"]
    assert any("Fertilizer application rate was not provided" in w for w in warnings)
