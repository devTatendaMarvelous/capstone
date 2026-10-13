from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import write_audit
from apps.core.permissions import IsAtLeast
from apps.core.schema import ErrorResponseSerializer
from apps.predictions.geospatial import (
    GeospatialService,
    convert_planting_date_to_planting_day,
    validate_coordinates,
)
from apps.predictions.ml_service import MLModelService
from apps.predictions.models import FarmLocation, Prediction
from apps.predictions.serializers import (
    EnvironmentalPreviewRequestSerializer,
    LocationValidationRequestSerializer,
    PredictionRecordSerializer,
    PredictionRequestSerializer,
    PredictionResponseSerializer,
)

EXAMPLE = {
    "location": {
        "latitude": -18.136,
        "longitude": 31.849,
        "location_selection_method": "manual_map_selection",
        "confirmed": True,
        "description": "Macheke smallholder farm",
    },
    "area_ha": 2.5,
    "planting_date": "2023-11-15",
    "fertilizer_kg_ha": 150.0,
}


class LocationValidateView(APIView):
    """Validate latitude and longitude and verify study area inclusion."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Validate farm coordinates and check study area scope",
        request=LocationValidationRequestSerializer,
        responses={200: dict, 400: ErrorResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = LocationValidationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = validate_coordinates(
            latitude=data["latitude"],
            longitude=data["longitude"],
            selection_method=data.get("location_selection_method"),
            is_confirmed=data.get("is_confirmed", False),
            description=data.get("location_description", ""),
        )

        if not result["valid"]:
            return Response(
                {"success": False, "message": "Invalid coordinates.", "errors": result["errors"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result, status=status.HTTP_200_OK)


class EnvironmentalDataPreviewView(APIView):
    """Preview geospatial environmental data before making a prediction."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Preview geospatial environmental data for coordinates",
        request=EnvironmentalPreviewRequestSerializer,
        responses={200: dict, 400: ErrorResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = EnvironmentalPreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        loc_check = validate_coordinates(data["latitude"], data["longitude"])
        if not loc_check["valid"]:
            return Response(
                {"success": False, "message": "Invalid coordinates.", "errors": loc_check["errors"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        res = GeospatialService.get_environmental_data(
            latitude=data["latitude"],
            longitude=data["longitude"],
            season_year=data.get("season_year", 2023),
            force_refresh=data.get("force_refresh", False),
        )

        # Include planting day conversion if planting date was provided
        if data.get("planting_date"):
            p_day = convert_planting_date_to_planting_day(data["planting_date"])
            if p_day is not None:
                res["environmental_data"]["planting_day"] = p_day

        return Response(res, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List prediction history", responses={200: PredictionRecordSerializer(many=True)}),
    retrieve=extend_schema(summary="Retrieve one stored prediction", responses={200: PredictionRecordSerializer}),
)
class PredictionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = PredictionRecordSerializer
    permission_classes = [IsAtLeast]
    allowed_roles = ("farmer", "analyst", "researcher", "admin")
    queryset = Prediction.objects.select_related("user", "farm_location")

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role == "farmer" and not user.is_superuser:
            queryset = queryset.filter(user=user)
        return queryset

    @extend_schema(
        summary="Predict maize yield per hectare",
        description=(
            "Scores the active saved model using location-derived environmental data or manual overrides. "
            "predicted_production_tonnes = predicted_yield_t_ha × area_ha. "
            "Requires confirmed farm location or complete legacy feature inputs."
        ),
        request=PredictionRequestSerializer,
        responses={201: PredictionResponseSerializer, 400: ErrorResponseSerializer, 503: ErrorResponseSerializer},
        examples=[OpenApiExample("Macheke smallholder location example", value=EXAMPLE, request_only=True)],
    )
    def create(self, request, *args, **kwargs):
        payload = dict(request.data)
        location_data = payload.get("location")
        farm_location_obj = None
        data_sources = []
        data_quality = {"missing_features": [], "warnings": []}
        environmental_record = {}

        # Parse location if provided
        lat = payload.get("latitude")
        lon = payload.get("longitude")
        confirmed = payload.get("location_confirmed", False)
        sel_method = payload.get("location_selection_method", "manual_coordinates")
        desc = ""

        if isinstance(location_data, dict):
            lat = location_data.get("latitude", lat)
            lon = location_data.get("longitude", lon)
            confirmed = location_data.get("confirmed", confirmed)
            sel_method = location_data.get("location_selection_method", sel_method)
            desc = location_data.get("description", "")

        # Workflow 1: Location-based prediction
        if lat is not None and lon is not None:
            # Validate coordinates
            loc_val = validate_coordinates(
                latitude=lat,
                longitude=lon,
                selection_method=sel_method,
                is_confirmed=confirmed,
                description=desc,
            )
            if not loc_val["valid"]:
                return Response(
                    {"success": False, "message": "Invalid coordinates.", "errors": loc_val["errors"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Enforce confirmation requirement: unconfirmed location cannot be submitted
            if not confirmed:
                return Response(
                    {
                        "success": False,
                        "message": "Farm location must be confirmed before estimating yield.",
                        "errors": {"location": ["Location must be confirmed before estimating yield."]},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Acquire geospatial environmental data
            geo_result = GeospatialService.get_environmental_data(
                latitude=float(lat),
                longitude=float(lon),
                season_year=2023,
            )
            env_vars = geo_result["environmental_data"]
            data_sources = geo_result["data_sources"]
            data_quality = geo_result["data_quality"]
            environmental_record = dict(env_vars)

            # Populate model inputs from environmental data unless manually overridden
            for var_name, var_val in env_vars.items():
                if var_name not in payload or payload[var_name] in (None, ""):
                    payload[var_name] = var_val

            # Resolve planting day
            if ("planting_day" not in payload or payload["planting_day"] in (None, "")) and payload.get("planting_date"):
                p_day = convert_planting_date_to_planting_day(payload["planting_date"])
                if p_day is not None:
                    payload["planting_day"] = p_day
            elif "planting_day" not in payload or payload["planting_day"] in (None, ""):
                # Default to median planting day (day 45 = 15 December) if neither date nor day given
                payload["planting_day"] = 45.0
                data_quality["warnings"].append("Planting day not specified; default mid-season planting day (45) used.")

            # Record missing fertilizer warning if fertilizer is not supplied
            if payload.get("fertilizer_kg_ha") in (None, ""):
                data_quality["warnings"].append(
                    "Fertilizer application rate was not provided. Imputed using training dataset median (150 kg/ha). "
                    "Actual harvest yield may vary substantially based on real fertilizer application."
                )

            # Persist FarmLocation
            farm_location_obj = FarmLocation.objects.create(
                user=request.user,
                latitude=float(lat),
                longitude=float(lon),
                location_selection_method=sel_method,
                is_confirmed=True,
                location_description=desc or loc_val["provisional_description"],
                is_within_study_area=loc_val["is_within_study_area"],
            )

        # Check required area
        if "area_ha" not in payload or payload["area_ha"] in (None, ""):
            return Response(
                {"success": False, "message": "area_ha is required.", "errors": {"area_ha": ["This field is required."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = MLModelService.predict(payload, allow_imputed_fertilizer=True)
        except ValidationError as exc:
            return Response(
                {"success": False, "message": "Validation failed.", "errors": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except FileNotFoundError as exc:
            return Response(
                {"success": False, "message": str(exc), "errors": {}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Prepare stored inputs record
        stored_inputs = {
            "rainfall_mm": payload.get("rainfall_mm"),
            "avg_temperature_c": payload.get("avg_temperature_c"),
            "max_temperature_c": payload.get("max_temperature_c"),
            "min_temperature_c": payload.get("min_temperature_c"),
            "soil_ph": payload.get("soil_ph"),
            "soil_nitrogen": payload.get("soil_nitrogen"),
            "soil_organic_carbon": payload.get("soil_organic_carbon"),
            "fertilizer_kg_ha": payload.get("fertilizer_kg_ha"),
            "planting_day": payload.get("planting_day"),
            "area_ha": payload.get("area_ha"),
        }

        record = Prediction.objects.create(
            user=request.user,
            model_version=result["model_version"],
            prediction_inputs=stored_inputs,
            predicted_yield=result["predicted_yield_t_ha"],
            predicted_production=result["predicted_production_tonnes"],
            farm_area=float(payload["area_ha"]),
            farm_location=farm_location_obj,
            environmental_data=environmental_record or None,
            data_sources=data_sources,
            data_quality=data_quality,
        )

        write_audit(request.user, "prediction.create", "prediction", record.pk, {"model_version": result["model_version"]})

        # Augment result with location and provenance
        if farm_location_obj:
            result["location"] = {
                "latitude": farm_location_obj.latitude,
                "longitude": farm_location_obj.longitude,
                "location_selection_method": farm_location_obj.location_selection_method,
                "confirmed": farm_location_obj.is_confirmed,
                "description": farm_location_obj.location_description,
                "is_within_study_area": farm_location_obj.is_within_study_area,
            }
        else:
            result["location"] = None

        result["environmental_data"] = environmental_record
        result["data_sources"] = data_sources
        result["data_quality"] = data_quality

        return Response(result, status=status.HTTP_201_CREATED)
