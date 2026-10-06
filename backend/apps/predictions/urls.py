from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.predictions.views import PredictionViewSet

router = DefaultRouter()
router.register("predictions", PredictionViewSet, basename="prediction")

urlpatterns = [path("", include(router.urls))]
