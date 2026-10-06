from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.models_registry.views import ModelViewSet

router = DefaultRouter()
router.register("models", ModelViewSet, basename="model")

urlpatterns = [path("", include(router.urls))]
