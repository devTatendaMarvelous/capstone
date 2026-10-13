from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

from apps.core.admin_site import admin_site

docs = {"authentication_classes": [], "permission_classes": [AllowAny]}

urlpatterns = [
    path("admin/", admin_site.urls),
    path("api/schema/", SpectacularAPIView.as_view(**docs), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema", **docs), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema", **docs), name="redoc"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.datasets.urls")),
    path("api/v1/", include("apps.predictions.urls")),
    path("api/", include("apps.predictions.urls")),
    path("api/v1/", include("apps.models_registry.urls")),
    path("api/v1/analytics/", include("apps.analytics.urls")),
    path("api/v1/reports/", include("apps.reports.urls")),
    path("api/v1/health/", include("apps.core.urls")),
]

admin.site.site_header = "SmartCrop"
