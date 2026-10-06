from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.audit import write_audit
from apps.core.permissions import IsAtLeast
from apps.core.schema import ErrorResponseSerializer
from apps.models_registry.models import ModelVersion
from apps.models_registry.serializers import ModelVersionSerializer


@extend_schema_view(
    list=extend_schema(summary="List registered model versions", responses={200: ModelVersionSerializer(many=True)}),
    retrieve=extend_schema(summary="Retrieve a model version", responses={200: ModelVersionSerializer}),
)
class ModelViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ModelVersionSerializer
    permission_classes = [IsAtLeast]
    allowed_roles = ("researcher", "analyst", "farmer", "admin")
    queryset = ModelVersion.objects.all()

    @extend_schema(
        summary="Mark one model as the active production model",
        description="Administrators only. Any other active flag is cleared.",
        responses={200: ModelVersionSerializer, 403: ErrorResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        if request.user.role != "admin" and not request.user.is_superuser:
            return Response(
                {"success": False, "message": "Only an administrator can activate a model.", "errors": {}},
                status=status.HTTP_403_FORBIDDEN,
            )
        model = self.get_object()
        model.is_active = True
        model.save()
        write_audit(request.user, "model.activate", "model_version", model.pk, {"version": model.version})
        return Response(ModelVersionSerializer(model).data)
