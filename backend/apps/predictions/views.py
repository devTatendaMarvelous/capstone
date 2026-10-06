from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from apps.core.audit import write_audit
from apps.core.permissions import IsAtLeast
from apps.core.schema import ErrorResponseSerializer
from apps.predictions.ml_service import MLModelService
from apps.predictions.models import Prediction
from apps.predictions.serializers import (
    PredictionRecordSerializer,
    PredictionRequestSerializer,
    PredictionResponseSerializer,
)

EXAMPLE = {
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


@extend_schema_view(
    list=extend_schema(summary="List prediction history", responses={200: PredictionRecordSerializer(many=True)}),
    retrieve=extend_schema(summary="Retrieve one stored prediction", responses={200: PredictionRecordSerializer}),
)
class PredictionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = PredictionRecordSerializer
    permission_classes = [IsAtLeast]
    allowed_roles = ("farmer", "analyst", "researcher", "admin")
    queryset = Prediction.objects.select_related("user")

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role == "farmer" and not user.is_superuser:
            queryset = queryset.filter(user=user)
        return queryset

    @extend_schema(
        summary="Predict maize yield per hectare",
        description=(
            "Scores the active saved model. The request does not train or update the model. "
            "predicted_production_tonnes = predicted_yield_t_ha × area_ha. "
            "soil_organic_carbon is required because the saved model uses it."
        ),
        request=PredictionRequestSerializer,
        responses={201: PredictionResponseSerializer, 400: ErrorResponseSerializer, 503: ErrorResponseSerializer},
        examples=[OpenApiExample("Macheke smallholder example", value=EXAMPLE, request_only=True)],
    )
    def create(self, request, *args, **kwargs):
        try:
            result = MLModelService.predict(request.data)
        except FileNotFoundError as exc:
            return Response(
                {"success": False, "message": str(exc), "errors": {}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        record = Prediction.objects.create(
            user=request.user,
            model_version=result["model_version"],
            prediction_inputs={key: request.data.get(key) for key in EXAMPLE},
            predicted_yield=result["predicted_yield_t_ha"],
            predicted_production=result["predicted_production_tonnes"],
            farm_area=float(request.data["area_ha"]),
        )
        write_audit(request.user, "prediction.create", "prediction", record.pk, {"model_version": result["model_version"]})
        return Response(result, status=status.HTTP_201_CREATED)
