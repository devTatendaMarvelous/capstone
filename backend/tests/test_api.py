import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.models_registry.models import ModelVersion
from apps.predictions.ml_service import MLModelService

User = get_user_model()

PREDICTION = {
    "rainfall_mm": 650,
    "avg_temperature_c": 24.5,
    "max_temperature_c": 31.2,
    "min_temperature_c": 17.8,
    "soil_ph": 5.8,
    "soil_nitrogen": 0.12,
    "soil_organic_carbon": 1.0,
    "fertilizer_kg_ha": 150,
    "planting_day": 45,
    "area_ha": 2.5,
}


@pytest.fixture
def users(db):
    created = {}
    for username, role, superuser in (
        ("admin", "admin", True),
        ("researcher", "researcher", False),
        ("farmer", "farmer", False),
    ):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@smartcrop.local",
            password="test-password-9",
            role=role,
        )
        user.is_superuser = superuser
        user.is_staff = superuser
        user.save()
        created[username] = user
    return created


@pytest.fixture
def client():
    return APIClient()


def auth(client, username):
    response = client.post("/api/v1/auth/token/", {"username": username, "password": "test-password-9"}, format="json")
    assert response.status_code == 200, response.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return response


@pytest.mark.django_db
def test_login_returns_role(client, users):
    response = auth(client, "farmer")
    assert response.data["user"]["role"] == "farmer"


@pytest.mark.django_db
def test_prediction_requires_authentication(client):
    response = client.post("/api/v1/predictions/", PREDICTION, format="json")
    assert response.status_code == 401
    assert response.data["success"] is False


@pytest.mark.django_db
def test_prediction_rejects_negative_rainfall(client, users):
    auth(client, "farmer")
    payload = {**PREDICTION, "rainfall_mm": -5}
    response = client.post("/api/v1/predictions/", payload, format="json")
    assert response.status_code == 400
    assert response.data["success"] is False
    assert "rainfall_mm" in response.data["errors"]


@pytest.mark.django_db
def test_prediction_returns_yield_and_production(client, users):
    auth(client, "farmer")
    response = client.post("/api/v1/predictions/", PREDICTION, format="json")
    assert response.status_code == 201, response.content
    body = response.data
    assert body["model_version"] == "1.0.0"
    assert body["predicted_production_tonnes"] == round(body["predicted_yield_t_ha"] * 2.5, 2)
    second = client.post("/api/v1/predictions/", PREDICTION, format="json")
    assert second.data["predicted_yield_t_ha"] == body["predicted_yield_t_ha"]
    history = client.get("/api/v1/predictions/")
    assert history.data["count"] == 2


@pytest.mark.django_db
def test_model_metadata_loads():
    metadata = MLModelService.get_model_metadata()
    assert metadata["target"] == "yield_t_ha"
    assert "rainfall_mm" in metadata["raw_features"]
    model = MLModelService.load_model()
    assert hasattr(model, "predict")


@pytest.mark.django_db
def test_farmer_cannot_upload_dataset(client, users):
    auth(client, "farmer")
    upload = SimpleUploadedFile("farms.csv", b"yield_t_ha\n1.2\n", content_type="text/csv")
    response = client.post(
        "/api/v1/datasets/upload/",
        {"name": "Trial", "source": "test", "source_type": "SYNTHETIC", "version": "0.0.1", "file": upload},
        format="multipart",
    )
    assert response.status_code == 403
    assert response.data["success"] is False


@pytest.mark.django_db
def test_researcher_can_upload_dataset(client, users):
    auth(client, "researcher")
    upload = SimpleUploadedFile("farms.csv", b"yield_t_ha,data_source_type\n1.2,SYNTHETIC\n", content_type="text/csv")
    response = client.post(
        "/api/v1/datasets/upload/",
        {
            "name": "Trial",
            "description": "Synthetic test upload",
            "source": "unit-test",
            "source_type": "SYNTHETIC",
            "version": "0.0.1",
            "file": upload,
        },
        format="multipart",
    )
    assert response.status_code == 201, response.content
    assert response.data["record_count"] == 1
    assert response.data["source_type"] == "SYNTHETIC"


@pytest.mark.django_db
def test_model_report_pdf(client, users):
    ModelVersion.objects.create(
        name="smartcrop_maize_yield",
        version="1.0.0",
        algorithm="Random Forest Regressor",
        metrics={"mae": 0.26, "rmse": 0.34, "r2": 0.47},
        is_active=True,
        artifact_path="ml_models/smartcrop_model.joblib",
    )
    auth(client, "admin")
    response = client.get("/api/v1/reports/model-performance/?format=pdf")
    assert response.status_code == 200, response.content
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


@pytest.mark.django_db
def test_schema_is_public(client):
    response = client.get("/api/schema/")
    assert response.status_code == 200
    assert b"SmartCrop" in response.content
