from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.predictions.views import (
    EnvironmentalDataPreviewView,
    LocationValidateView,
    PredictionViewSet,
)

router = DefaultRouter()
router.register("predictions", PredictionViewSet, basename="prediction")

urlpatterns = [
    path("location/validate/", LocationValidateView.as_view(), name="location-validate"),
    path("environmental-data/preview/", EnvironmentalDataPreviewView.as_view(), name="environmental-preview"),
    path("", include(router.urls)),
]
